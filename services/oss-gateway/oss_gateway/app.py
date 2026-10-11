"""CompreFace-compatible gateway: durable originals in configurable object storage."""
import asyncio
import base64
from contextlib import asynccontextmanager
import hashlib
import io
import json
import re
import uuid
from urllib.parse import quote, unquote

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
import httpx
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from .config import Settings
from .journal import Journal
from .store import S3Store

FACES = '/api/v1/recognition/faces'
SUBJECTS = '/api/v1/recognition/subjects'
HOP_HEADERS = {'connection','keep-alive','proxy-authenticate','proxy-authorization',
               'te','trailer','transfer-encoding','upgrade','content-length','content-encoding'}


class UpstreamRejected(Exception):
    def __init__(self, response):
        self.response = response


class GatewayError(Exception):
    def __init__(self, message, status=503):
        self.message, self.status = message, status


def proxy_response(response):
    result = Response(response.content, status_code=response.status_code)
    connection = set(response.headers.get('connection', '').lower().split(','))
    result.raw_headers = [(k.encode('latin-1'),v.encode('latin-1')) for k,v in response.headers.multi_items()
                          if k.lower() not in HOP_HEADERS | connection]
    result.headers['content-length'] = str(len(response.content))
    return result


def upstream_path(request):
    raw = request.scope.get('raw_path')
    return raw.decode('ascii') if raw is not None else quote(request.scope['path'], safe='/')


def image_identifier(value):
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise GatewayError('Invalid image identifier', 400) from None


class Gateway:
    def __init__(self, settings, store, journal, client):
        self.settings, self.store, self.journal, self.client = settings, store, journal, client
        self.locks = {}

    async def object_call(self, method, *args):
        try:
            return await run_in_threadpool(getattr(self.store, method), *args)
        except Exception:
            # Provider errors can contain credential IDs; do not return or log them.
            raise GatewayError('Object storage is unavailable') from None

    async def flush(self):
        try:
            await run_in_threadpool(self.journal.flush, self.store)
        except Exception:
            pass  # Durable outbox remains queued; the background worker retries.

    async def worker(self):
        while True:
            try:
                await self.object_call('initialize')
                await self.flush()
            except GatewayError:
                pass
            await asyncio.sleep(self.settings.poll_seconds)

    async def call(self, method, path, api_key='', params=None, body=None, headers=None):
        outgoing = dict(headers or {})
        for name in list(outgoing):
            if name.lower() in HOP_HEADERS | {'host'}:
                del outgoing[name]
        if api_key:
            outgoing['x-api-key'] = api_key
        try:
            return await self.client.request(method, self.settings.upstream+path,
                                             params=params, content=body, headers=outgoing)
        except httpx.HTTPError:
            raise GatewayError('CompreFace is unavailable', 502) from None

    async def face_ids(self, api_key, subject=None):
        ids, page = [], 0
        while True:
            params = {'page':page, 'size':1000}
            if subject is not None:
                params['subject'] = subject
            response = await self.call('GET', FACES, api_key, params)
            if not response.is_success:
                raise UpstreamRejected(response)
            data = response.json()
            ids.extend(face['image_id'] for face in data['faces'])
            page += 1
            if page >= data['total_pages']:
                return ids
            if page > 10000:
                raise GatewayError('Face collection pagination exceeded the gateway limit', 502)

    async def authorize(self, api_key):
        response = await self.call('GET', SUBJECTS, api_key)
        if not response.is_success:
            raise UpstreamRejected(response)

    async def recover(self, api_key, namespace):
        # A service key is supplied by the caller, never written into the journal.
        unresolved = False
        for upload in self.journal.uploads(namespace):
            if not upload['subject']:
                # Legacy migration never registers a backend face. Its DB source
                # remains available, so an interrupted copy can be safely retried.
                self.journal.discard_upload(upload['id'])
                continue
            current = await self.face_ids(api_key, upload['subject'])
            added = set(current)-set(json.loads(upload['previous_ids']))
            if len(added) == 1:
                self.journal.complete_upload(upload['id'], added.pop())
            elif not added:
                # A timed-out backend operation can still commit later. Absence
                # in one snapshot cannot establish that an upload failed.
                unresolved = True
            else:
                raise GatewayError('Upload recovery is ambiguous; reconcile the journal before writing')
        plans = self.journal.prepared_deletes(namespace)
        if plans:
            current = set(await self.face_ids(api_key))
            for plan in plans:
                planned = {image['image_id'] for image in json.loads(plan['images'])}
                if planned and not planned & current:
                    self.journal.finish_delete(plan['id'])
                else:
                    # Keep the intent until a late delete is confirmed, rather
                    # than losing its outbox association while it is in flight.
                    unresolved = True
        await self.flush()
        return unresolved

    async def upload_bytes(self, request, body):
        if request.headers.get('content-type', '').split(';',1)[0] == 'application/json':
            try:
                value = json.loads(body)['file']
                return base64.b64decode(value, validate=True)
            except (KeyError, ValueError, TypeError):
                raise GatewayError('Expected a valid base64 file', 400) from None
        try:
            form = await request.form(max_files=1, max_fields=20)
            try:
                upload = form.get('file')
                if len(form.getlist('file')) != 1 or not hasattr(upload, 'read'):
                    raise GatewayError('Expected a multipart file', 400)
                return await upload.read()
            finally:
                await form.close()
        except GatewayError:
            raise
        except Exception:
            raise GatewayError('Invalid multipart file', 400) from None

    @staticmethod
    def media_type(data):
        try:
            with Image.open(io.BytesIO(data)) as image:
                content_type = Image.MIME.get(image.format, 'application/octet-stream')
                image.verify()
                return content_type
        except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
            raise GatewayError('Invalid image', 400) from None

    async def add_face(self, request, body, api_key, namespace):
        subject = request.query_params.get('subject')
        if len(request.query_params.getlist('subject')) != 1 or not subject or len(subject) > 50:
            raise GatewayError('Subject must contain 1 to 50 characters', 400)
        data = await self.upload_bytes(request, body)
        media_type = self.media_type(data)
        previous = await self.face_ids(api_key, subject)
        object_key = f'{self.settings.prefix}/{namespace}/{uuid.uuid4().hex}'
        operation = self.journal.begin_upload(namespace, subject, previous, object_key)
        try:
            await self.object_call('put', object_key, data, media_type)
        except GatewayError:
            self.journal.discard_upload(operation)
            await self.flush()
            raise
        # Keep the original multipart/base64 bytes and query intact.
        response = await self.call('POST', FACES, api_key, list(request.query_params.multi_items()),
                                   body, request.headers)
        if response.is_success:
            image_id = str(uuid.UUID(response.json()['image_id']))
            self.journal.complete_upload(operation, image_id)
        elif response.status_code < 500:
            self.journal.discard_upload(operation)
            await self.flush()
        # 5xx/network errors may occur after a committed upload: recover on the next
        # authenticated request using the before/after IDs, keeping the original safe.
        return proxy_response(response)

    async def delete(self, request, body, api_key, namespace, image_ids):
        operation = self.journal.plan_delete(namespace, image_ids)
        response = await self.call(request.method, upstream_path(request), api_key,
                                   list(request.query_params.multi_items()), body, request.headers)
        if response.is_success:
            self.journal.finish_delete(operation)
            await self.flush()
        elif response.status_code < 500:
            self.journal.discard_delete(operation)
        result = proxy_response(response)
        if response.is_success:
            # SQL deletion is complete; object deletion may be queued during an outage.
            result.headers['x-facesdk-object-delete'] = 'pending' if self.journal.pending_deletes(namespace) else 'completed'
        return result

    async def image(self, api_key, namespace, image_id, migrate=True):
        # Verify current ownership/existence, including after an admin deletion or crash.
        ids = await self.face_ids(api_key)
        if image_id not in ids:
            raise GatewayError('Face image not found', 404)
        object_key = self.journal.image(namespace, image_id)
        if object_key:
            data, media_type = await self.object_call('get', object_key)
        else:
            # Existing DB images are migrated on first authorized read. New images
            # use SAVE_IMAGES_TO_DB=false, so originals live only in object storage.
            response = await self.call('GET', f'{FACES}/{image_id}/img', api_key)
            if not response.is_success:
                raise UpstreamRejected(response)
            if not response.content:
                raise GatewayError('Original image is unavailable; restore the storage journal', 404)
            data = response.content
            media_type = self.media_type(data)
            if migrate:
                object_key = f'{self.settings.prefix}/{namespace}/{uuid.uuid4().hex}'
                operation = self.journal.begin_upload(namespace, '', ids, object_key)
                await self.object_call('put', object_key, data, media_type)
                self.journal.complete_upload(operation, image_id)
        return Response(data, media_type=media_type,
                        headers={'cache-control':'private, no-store','x-content-type-options':'nosniff'})


def create_app(settings=None, store=None, transport=None):
    settings = settings or Settings.from_env()
    settings.validate()
    store = store or S3Store(settings)
    journal = Journal(settings.database)
    client = httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(120, connect=10), trust_env=False)
    gateway = Gateway(settings, store, journal, client)

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(gateway.worker())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await client.aclose()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.gateway = gateway

    @app.exception_handler(GatewayError)
    async def gateway_error(request, error):
        return JSONResponse({'message':error.message,'code':'OSS_GATEWAY_ERROR'}, status_code=error.status)

    @app.exception_handler(UpstreamRejected)
    async def upstream_error(request, error):
        return proxy_response(error.response)

    @app.exception_handler(Exception)
    async def internal_error(request, error):
        return JSONResponse({'message':'Storage gateway could not complete the operation',
                             'code':'OSS_GATEWAY_ERROR'}, status_code=503)

    @app.get('/health/live')
    async def live():
        return {'status':'OK'}

    @app.get('/api/v1/consistence/status')
    async def health():
        try:
            response = await gateway.call('GET', '/api/v1/consistence/status')
            if not response.is_success or response.json().get('status') != 'OK':
                raise GatewayError('CompreFace dependencies are unavailable')
            journal.check()
            await gateway.object_call('check')
            data = response.json()
            data['objectStorage'] = 'OK'
            return JSONResponse(data)
        except Exception:
            return JSONResponse({'status':'DOWN'}, status_code=503)

    @app.api_route('/{path:path}', methods=['GET','HEAD','POST','PUT','PATCH','DELETE','OPTIONS'])
    async def proxy(request: Request, path: str):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > settings.max_body_bytes:
                raise GatewayError('Request body is too large', 413)
        request._body = bytes(body)  # Starlette form parser reuses this bounded body.
        api_key = request.headers.get('x-api-key', '')
        # Decode exactly once; preserve literal %xx in Subjects and raw forwarding.
        uri = unquote(upstream_path(request)) or '/'
        static = re.fullmatch(r'/api/v1/static/([^/]+)/images/([^/]+)', uri)
        image = re.fullmatch(FACES+r'/([^/]+)/img', uri)
        face_delete = re.fullmatch(FACES+r'/([^/]+)', uri) if request.method == 'DELETE' else None
        subject_delete = uri.startswith(SUBJECTS+'/') and request.method == 'DELETE'
        mutation = (uri == FACES and request.method in ('POST','DELETE')) or face_delete or subject_delete or (uri == FACES+'/delete' and request.method == 'POST')
        if static or image or mutation or (uri.startswith('/api/v1/recognition/') and api_key):
            if static:
                api_key = static[1]
            namespace = hashlib.sha256(api_key.encode()).hexdigest()
            await gateway.authorize(api_key)
            async with gateway.locks.setdefault(namespace, asyncio.Lock()):
                unresolved = await gateway.recover(api_key, namespace)
                read_only = request.method in ('GET','HEAD') or (request.method == 'POST' and
                            (uri == '/api/v1/recognition/recognize' or re.fullmatch(FACES+r'/[^/]+/verify',uri)))
                if unresolved and not read_only:
                    raise GatewayError('An upstream operation is unconfirmed; retry reads or reconcile before writing')
                if request.method == 'GET' and (static or image):
                    image_id = image_identifier((static or image)[2 if static else 1])
                    return await gateway.image(api_key, namespace, image_id, migrate=not unresolved)
                if uri == FACES and request.method == 'POST':
                    return await gateway.add_face(request, bytes(body), api_key, namespace)
                if mutation:
                    if face_delete:
                        image_ids = [image_identifier(face_delete[1])]
                    elif uri == FACES+'/delete':
                        try:
                            values = json.loads(body)
                            if not isinstance(values, list):
                                raise ValueError('Expected an array')
                            image_ids = [image_identifier(value) for value in values]
                        except (ValueError, TypeError):
                            raise GatewayError('Expected an array of image identifiers', 400) from None
                    else:
                        subject = uri[len(SUBJECTS)+1:] if subject_delete else request.query_params.get('subject')
                        image_ids = await gateway.face_ids(api_key, subject)
                    return await gateway.delete(request, bytes(body), api_key, namespace, image_ids)
                # Subject create/rename and other recognition requests share the
                # service lock, so they cannot race an upload's recovery snapshot.
                return proxy_response(await gateway.call(request.method, upstream_path(request), api_key,
                                                         list(request.query_params.multi_items()), bytes(body), request.headers))
        return proxy_response(await gateway.call(request.method, upstream_path(request), api_key,
                                                 list(request.query_params.multi_items()), bytes(body), request.headers))

    return app
