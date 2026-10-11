"""Exercise both transports over HTTP using CompreFace 1.2 wire responses."""
import io
import json
import threading
from collections import deque
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, unquote

import pytest

from facesdk import FaceSDKClient, AsyncFaceSDKClient
from facesdk.exceptions import FaceSDKException, AuthenticationException, ValidationException

FIXTURES = json.loads((Path(__file__).resolve().parents[3] / 'tests/fixtures/compreface-1.2.json').read_text(encoding='utf-8'))
IMAGE = b'\xff\xd8face-image\x00\xff'
SUBJECT = '张三 /?&'


@pytest.fixture
def server():
    replies, requests = deque(), []
    class Handler(BaseHTTPRequestHandler):
        def handle_request(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            files = {}
            if 'multipart/form-data' in self.headers.get('Content-Type', ''):
                message = BytesParser(policy=default).parsebytes(('Content-Type: ' + self.headers['Content-Type'] + '\r\n\r\n').encode() + body)
                for part in message.iter_parts():
                    files[part.get_param('name', header='content-disposition')] = part.get_payload(decode=True)
            requests.append({'method': self.command, 'path': urlsplit(self.path).path,
                             'query': parse_qs(urlsplit(self.path).query), 'key': self.headers.get('x-api-key'), 'files': files, 'body': body})
            status, payload = replies.popleft() if replies else (500, {'message': 'unexpected request'})
            content = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        do_GET = do_POST = do_DELETE = handle_request
        def log_message(self, *args):
            pass
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{httpd.server_port}', replies, requests
    httpd.shutdown()
    httpd.server_close()
    thread.join()


@pytest.mark.parametrize('asynchronous', [False, True])
@pytest.mark.asyncio
async def test_full_protocol(server, asynchronous):
    url, replies, requests = server
    cls = AsyncFaceSDKClient if asynchronous else FaceSDKClient
    client = cls(url+'/', api_keys={'detection': 'D', 'verification': 'V', 'recognition': 'R'}, retry_delay=0)
    async def call(name, *args, **kwargs):
        value = getattr(client, name)(*args, **kwargs)
        return await value if asynchronous else value
    try:
        replies.append((200, FIXTURES['detection']))
        result = await call('detect', io.BytesIO(IMAGE), status=True, det_prob_threshold=0.7)
        assert result.face_count == 1 and result.faces[0].confidence == 0.99
        assert requests[-1]['files'] == {'file': IMAGE}
        assert requests[-1]['query'] == {'status': ['true'], 'det_prob_threshold': ['0.7']}
        assert requests[-1]['key'] == 'D'
        replies.append((200, FIXTURES['verification']))
        result = await call('compare', IMAGE, IMAGE)
        assert result.similarity == 0.8 and result.match and result.threshold == 0.8
        assert requests[-1]['path'] == '/api/v1/verification/verify'
        assert requests[-1]['files'] == {'source_image': IMAGE, 'target_image': IMAGE}
        assert requests[-1]['key'] == 'V'
        replies.append((200, FIXTURES['recognition']))
        result = await call('search', IMAGE, limit=3, threshold=0.8)
        assert [r.subject_id for r in result.results] == ['best', 'boundary']
        assert result.face_count == 1 and result.results[0].face.confidence == 0.99
        assert requests[-1]['query'] == {'prediction_count': ['3']} and requests[-1]['key'] == 'R'
        replies.append((200, FIXTURES['detection']))
        assert await call('extract_feature', IMAGE) == FIXTURES['embedding_base64']
        assert requests[-1]['query'] == {'face_plugins': ['calculator']}
        replies.append((200, FIXTURES['subjects']))
        assert [s.subject_id for s in await call('list_subjects')] == ['alice', SUBJECT]
        replies.append((201, FIXTURES['created']))
        assert (await call('create_subject', SUBJECT, 'ignored-name')).subject_id == SUBJECT
        assert json.loads(requests[-1]['body']) == {'subject': SUBJECT}
        replies.append((201, FIXTURES['added']))
        record = await call('add_face', SUBJECT, IMAGE)
        assert record.image_id == FIXTURES['added']['image_id']
        assert requests[-1]['query'] == {'subject': [SUBJECT]} and requests[-1]['files'] == {'file': IMAGE}
        replies.append((204, b''))
        await call('delete_face', record.image_id)
        replies.append((204, b''))
        await call('delete_subject', SUBJECT)
        assert unquote(requests[-1]['path'].split('/subjects/')[1]) == SUBJECT
        assert requests[-1]['query'] == {}
    finally:
        if asynchronous:
            await client.close()
        else:
            client.close()


@pytest.mark.parametrize('asynchronous', [False, True])
@pytest.mark.asyncio
async def test_retry_and_error_boundaries(server, asynchronous):
    url, replies, requests = server
    client = (AsyncFaceSDKClient if asynchronous else FaceSDKClient)(url, 'key', max_retries=1, retry_delay=0)
    async def call(name, *args, **kwargs):
        value = getattr(client, name)(*args, **kwargs)
        return await value if asynchronous else value
    try:
        replies.extend([(503, FIXTURES['error']), (200, FIXTURES['detection'])])
        await call('detect', io.BytesIO(IMAGE))
        assert len(requests) == 2 and all(r['files'] == {'file': IMAGE} for r in requests)
        for status in [401, 400]:
            replies.append((status, FIXTURES['error']))
            before = len(requests)
            with pytest.raises(FaceSDKException):
                await call('detect', IMAGE)
            assert len(requests) == before + 1
        for method, args in [('create_subject', ('new',)), ('add_face', ('new', IMAGE))]:
            replies.append((503, FIXTURES['error']))
            before = len(requests)
            with pytest.raises(FaceSDKException):
                await call(method, *args)
            assert len(requests) == before + 1
        for payload in [b'<html>not JSON</html>', b'[]', b'{}']:
            replies.append((200, payload))
            before = len(requests)
            with pytest.raises(FaceSDKException):
                await call('detect', IMAGE)
            assert len(requests) == before + 1
        before = len(requests)
        for kwargs in [{'limit': 0}, {'threshold': 1.1}, {'threshold': float('nan')}]:
            with pytest.raises(ValidationException):
                await call('search', IMAGE, **kwargs)
        with pytest.raises(ValidationException):
            await call('add_face', 'new', IMAGE, {'source': 'camera'})
        with pytest.raises(ValidationException):
            await call('delete_subject', '..')
        assert len(requests) == before
        multi = {'result': FIXTURES['detection']['result'] * 2}
        replies.append((200, multi))
        with pytest.raises(ValidationException):
            await call('extract_feature', IMAGE)
    finally:
        if asynchronous:
            await client.close()
        else:
            client.close()


def test_zero_retry_and_missing_key(server):
    url, replies, requests = server
    with FaceSDKClient(url, 'key', max_retries=0) as client:
        replies.append((503, FIXTURES['error']))
        with pytest.raises(FaceSDKException):
            client.detect(IMAGE)
    assert len(requests) == 1
    with FaceSDKClient(url) as client:
        with pytest.raises(AuthenticationException):
            client.detect(IMAGE)
    assert len(requests) == 1
