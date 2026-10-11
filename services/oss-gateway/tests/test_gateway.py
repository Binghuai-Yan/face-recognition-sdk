import base64
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import uuid

import httpx
from PIL import Image
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oss_gateway.app import create_app
from oss_gateway.config import Settings

KEY = 'test-recognition-key-a'
OTHER = 'test-recognition-key-b'


class Store:
    def __init__(self):
        self.objects = {}
        self.fail_put = self.fail_delete = self.fail_check = False

    def initialize(self):
        self.check()

    def check(self):
        if self.fail_check:
            raise OSError('provider failed with secret details')

    def put(self, key, data, content_type):
        if self.fail_put:
            raise OSError('private provider error')
        self.objects[key] = (data,content_type)

    def get(self, key):
        return self.objects[key]

    def delete(self, key):
        if self.fail_delete:
            raise OSError('provider failed')
        self.objects.pop(key,None)


class Backend:
    def __init__(self):
        self.faces = {KEY:{}, OTHER:{}}
        self.originals = {}
        self.reject_upload = False
        self.timeout_after_commit = False
        self.timeout_before_commit = False
        self.pending_upload = None
        self.timeout_after_delete = False
        self.timeout_before_delete = False
        self.healthy = True
        self.uploads = 0
        self.last_upload_body = None

    def __call__(self, request):
        path, method = request.url.path, request.method
        key = request.headers.get('x-api-key','')
        if path.endswith('/consistence/status'):
            return httpx.Response(200,json={'status':'OK' if self.healthy else 'DOWN'})
        if key not in self.faces:
            return httpx.Response(404,json={'message':'Service not found'})
        faces = self.faces[key]
        if path.endswith('/subjects'):
            return httpx.Response(200,json={'subjects':list(set(faces.values()))})
        if path.endswith('/faces') and method=='GET':
            subject = request.url.params.get('subject')
            selected = [{'image_id':i,'subject':s} for i,s in faces.items() if subject is None or s==subject]
            page, size = int(request.url.params['page']), int(request.url.params['size'])
            return httpx.Response(200,json={'faces':selected[page*size:(page+1)*size],
                'total_pages':(len(selected)+size-1)//size,'total_elements':len(selected)})
        if path.endswith('/faces') and method=='POST':
            self.uploads += 1
            self.last_upload_body = request.content
            if self.reject_upload:
                return httpx.Response(400,json={'message':'No face found'})
            image_id = str(uuid.uuid4())
            if self.timeout_before_commit:
                self.timeout_before_commit=False
                self.pending_upload=(image_id,request.url.params['subject'])
                raise httpx.ReadTimeout('backend is still processing the upload')
            faces[image_id] = request.url.params['subject']
            if self.timeout_after_commit:
                self.timeout_after_commit = False
                raise httpx.ReadTimeout('response lost after server commit')
            return httpx.Response(201,json={'image_id':image_id,'subject':faces[image_id]})
        if path.endswith('/img'):
            image_id = path.split('/')[-2]
            return httpx.Response(200,content=self.originals.get(image_id,b''))
        if '/subjects/' in path and method=='DELETE':
            subject = path.split('/subjects/',1)[1]
            if self.timeout_before_delete:
                self.timeout_before_delete=False
                raise httpx.ReadTimeout('backend is still processing the subject delete')
            for image_id in list(faces):
                if faces[image_id]==subject:
                    del faces[image_id]
            return httpx.Response(200,json={'subject':subject})
        if path.endswith('/faces/delete') and method=='POST':
            image_ids = json.loads(request.content)
            for image_id in image_ids:
                faces.pop(image_id,None)
            return httpx.Response(200,json=[{'image_id':i} for i in image_ids])
        if method=='DELETE':
            image_id = path.rsplit('/',1)[1]
            if image_id not in faces:
                return httpx.Response(404,json={'message':'Not found'})
            if self.timeout_before_delete:
                self.timeout_before_delete=False
                raise httpx.ReadTimeout('backend is still processing the delete')
            subject = faces.pop(image_id)
            if self.timeout_after_delete:
                self.timeout_after_delete=False
                raise httpx.ReadTimeout('delete response lost after server commit')
            return httpx.Response(200,json={'image_id':image_id,'subject':subject})
        return httpx.Response(200,json={'result':[]})


@pytest.fixture
def setup(tmp_path):
    image = io.BytesIO()
    Image.new('RGB',(16,16),'red').save(image,format='PNG')
    settings = Settings(upstream='http://backend',endpoint='http://objects',access_key='storage-id',
                        secret_key='storage-secret',database=str(tmp_path/'storage.sqlite3'),poll_seconds=3600)
    store, backend = Store(), Backend()
    def client():
        return TestClient(create_app(settings,store,httpx.MockTransport(backend)),raise_server_exceptions=False)
    return settings, store, backend, image.getvalue(), client


def upload(client, image, subject='张三 &?'):
    return client.post('/api/v1/recognition/faces',headers={'x-api-key':KEY},
                       params={'subject':subject},files={'file':('face.png',image,'image/png')})


@pytest.mark.parametrize('base64_input',[False,True])
def test_original_bytes_are_stored_and_reads_require_ownership(setup, base64_input):
    settings, store, backend, image, factory = setup
    with factory() as client:
        if base64_input:
            response = client.post('/api/v1/recognition/faces',headers={'x-api-key':KEY},
                                   params={'subject':'alice'},json={'file':base64.b64encode(image).decode()})
        else:
            response = upload(client,image)
            assert image in backend.last_upload_body
        assert response.status_code==201
        image_id = response.json()['image_id']
        assert len(store.objects)==1 and next(iter(store.objects.values()))==(image,'image/png')
        assert KEY not in next(iter(store.objects))
        read = client.get(f'/api/v1/recognition/faces/{image_id}/img',headers={'x-api-key':KEY})
        assert read.content==image and read.headers['cache-control']=='private, no-store'
        assert client.get(f'/api/v1/static/{KEY}/images/{image_id}').content==image
        assert client.get(f'/api/v1/recognition/faces/{image_id}/img',headers={'x-api-key':OTHER}).status_code==404
        assert client.delete(f'/api/v1/recognition/faces/{image_id}',headers={'x-api-key':OTHER}).status_code==404
        assert len(store.objects)==1
        removed = client.delete(f'/api/v1/recognition/faces/{image_id}',headers={'x-api-key':KEY})
        assert removed.status_code==200 and removed.headers['x-facesdk-object-delete']=='completed'
        assert not store.objects


def test_store_failure_never_registers_a_face_and_never_leaks_provider_errors(setup):
    settings, store, backend, image, factory = setup
    store.fail_put=True
    with factory() as client:
        response = upload(client,image)
        assert response.status_code==503 and 'private provider error' not in response.text
        assert backend.uploads==0 and not store.objects


def test_rejected_face_cleans_the_uploaded_object(setup):
    settings, store, backend, image, factory = setup
    backend.reject_upload=True
    with factory() as client:
        assert upload(client,image).status_code==400
        assert not store.objects and not backend.faces[KEY]


def test_lost_response_recovers_after_gateway_restart_without_duplicate_registration(setup):
    settings, store, backend, image, factory = setup
    backend.timeout_after_commit=True
    with factory() as client:
        assert upload(client,image).status_code==502
        assert len(store.objects)==len(backend.faces[KEY])==1
    with factory() as client:
        listing = client.get('/api/v1/recognition/faces',headers={'x-api-key':KEY},params={'page':0,'size':10})
        image_id = listing.json()['faces'][0]['image_id']
        assert client.get(f'/api/v1/recognition/faces/{image_id}/img',headers={'x-api-key':KEY}).content==image
        assert backend.uploads==1
    with sqlite3.connect(settings.database) as db:
        dumped = '\n'.join(db.iterdump())
    assert KEY not in dumped and 'storage-secret' not in dumped


def test_failed_delete_is_durable_and_revokes_reads_until_retried_after_restart(setup):
    settings, store, backend, image, factory = setup
    with factory() as client:
        image_id = upload(client,image).json()['image_id']
        store.fail_delete=True
        response = client.delete(f'/api/v1/recognition/faces/{image_id}',headers={'x-api-key':KEY})
        assert response.status_code==200 and response.headers['x-facesdk-object-delete']=='pending'
        assert store.objects and not backend.faces[KEY]
        assert client.get(f'/api/v1/recognition/faces/{image_id}/img',headers={'x-api-key':KEY}).status_code==404
    store.fail_delete=False
    with factory() as client:
        assert client.get('/api/v1/consistence/status').status_code==200
        client.get('/api/v1/recognition/faces',headers={'x-api-key':KEY},params={'page':0,'size':10})
        assert not store.objects


@pytest.mark.parametrize('subject',['张三 &?','literal %2F /'])
def test_subject_delete_preserves_encoded_unicode_query_characters(setup,subject):
    settings, store, backend, image, factory = setup
    from urllib.parse import quote
    with factory() as client:
        assert upload(client,image,subject).status_code==201
        response=client.delete('/api/v1/recognition/subjects/'+quote(subject,safe=''),headers={'x-api-key':KEY})
        assert response.status_code==200 and response.json()['subject']==subject
        assert not store.objects and not backend.faces[KEY]


def test_delete_committed_without_a_response_is_reconciled_after_restart(setup):
    settings,store,backend,image,factory=setup
    with factory() as client:
        image_id=upload(client,image).json()['image_id']
        backend.timeout_after_delete=True
        assert client.delete(f'/api/v1/recognition/faces/{image_id}',headers={'x-api-key':KEY}).status_code==502
        assert store.objects and not backend.faces[KEY]
    with factory() as client:
        response=client.get('/api/v1/recognition/faces',headers={'x-api-key':KEY},params={'page':0,'size':10})
        assert response.status_code==200 and not store.objects


def test_upload_committing_after_timeout_and_restart_never_loses_its_original(setup):
    settings,store,backend,image,factory=setup
    backend.timeout_before_commit=True
    with factory() as client:
        assert upload(client,image).status_code==502
        assert store.objects and not backend.faces[KEY]
    with factory() as client:
        response=client.get('/api/v1/recognition/faces',headers={'x-api-key':KEY},params={'page':0,'size':10})
        assert response.status_code==200 and not response.json()['faces'] and store.objects
        assert upload(client,image).status_code==503 and backend.uploads==1
        image_id,subject=backend.pending_upload
        backend.faces[KEY][image_id]=subject  # Original request commits late.
        read=client.get(f'/api/v1/recognition/faces/{image_id}/img',headers={'x-api-key':KEY})
        assert read.status_code==200 and read.content==image
        assert backend.uploads==1


def test_delete_committing_after_timeout_does_not_lose_its_cleanup_intent(setup):
    settings,store,backend,image,factory=setup
    with factory() as client:
        image_id=upload(client,image).json()['image_id']
        backend.timeout_before_delete=True
        assert client.delete(f'/api/v1/recognition/faces/{image_id}',headers={'x-api-key':KEY}).status_code==502
    with factory() as client:
        assert client.get(f'/api/v1/recognition/faces/{image_id}/img',headers={'x-api-key':KEY}).content==image
        assert upload(client,image).status_code==503 and store.objects
        del backend.faces[KEY][image_id]  # Original delete commits late.
        assert client.get(f'/api/v1/recognition/faces/{image_id}/img',headers={'x-api-key':KEY}).status_code==404
        assert not store.objects


def test_unmigrated_legacy_face_delete_remains_tracked_without_creating_an_orphan(setup):
    settings,store,backend,image,factory=setup
    image_id=str(uuid.uuid4())
    backend.faces[KEY][image_id]='legacy'
    backend.originals[image_id]=image
    with factory() as client:
        backend.timeout_before_delete=True
        assert client.delete(f'/api/v1/recognition/faces/{image_id}',headers={'x-api-key':KEY}).status_code==502
        assert client.get(f'/api/v1/recognition/faces/{image_id}/img',headers={'x-api-key':KEY}).content==image
        assert not store.objects  # Reading during an unconfirmed delete doesn't migrate.
        assert upload(client,image).status_code==503
        del backend.faces[KEY][image_id]
        assert client.get(f'/api/v1/recognition/faces/{image_id}/img',headers={'x-api-key':KEY}).status_code==404
        assert upload(client,image).status_code==201


def test_empty_collection_delete_timeout_requires_reconciliation_before_writes(setup):
    settings,store,backend,image,factory=setup
    with factory() as client:
        backend.timeout_before_delete=True
        assert client.delete('/api/v1/recognition/subjects/empty',headers={'x-api-key':KEY}).status_code==502
        assert client.get('/api/v1/recognition/faces',headers={'x-api-key':KEY},params={'page':0,'size':10}).status_code==200
        assert upload(client,image).status_code==503 and not store.objects and not backend.faces[KEY]


def test_bulk_delete_requires_an_array_and_preserves_existing_objects(setup):
    settings,store,backend,image,factory=setup
    with factory() as client:
        image_id=upload(client,image).json()['image_id']
        response=client.post('/api/v1/recognition/faces/delete',headers={'x-api-key':KEY},json={image_id:'bad'})
        assert response.status_code==400 and len(store.objects)==1


def test_duplicate_file_or_subject_cannot_store_a_different_original_from_the_backend(setup):
    settings,store,backend,image,factory=setup
    with factory() as client:
        response=client.post('/api/v1/recognition/faces',headers={'x-api-key':KEY},params={'subject':'alice'},
                             files=[('file',('a.png',image)),('file',('b.png',image))])
        assert response.status_code==400
        response=client.post('/api/v1/recognition/faces',headers={'x-api-key':KEY},params=[('subject','alice'),('subject','bob')],
                             files={'file':('a.png',image)})
        assert response.status_code==400 and not store.objects and backend.uploads==0


def test_bulk_delete_cleans_only_selected_objects(setup):
    settings, store, backend, image, factory = setup
    with factory() as client:
        selected=upload(client,image).json()['image_id']
        other=upload(client,image).json()['image_id']
        response=client.post('/api/v1/recognition/faces/delete',headers={'x-api-key':KEY},json=[selected])
        assert response.status_code==200 and len(store.objects)==1
        assert other in backend.faces[KEY]


@pytest.mark.parametrize('interrupted_copy',[False,True])
def test_existing_database_image_migrates_on_authorized_read(setup,interrupted_copy):
    settings, store, backend, image, factory = setup
    image_id=str(uuid.uuid4())
    backend.faces[KEY][image_id]='legacy'
    backend.originals[image_id]=image
    with factory() as client:
        if interrupted_copy:
            store.fail_put=True
            assert client.get(f'/api/v1/recognition/faces/{image_id}/img',headers={'x-api-key':KEY}).status_code==503
            store.fail_put=False
        assert client.get(f'/api/v1/recognition/faces/{image_id}/img',headers={'x-api-key':KEY}).content==image
        del backend.originals[image_id]
        assert client.get(f'/api/v1/recognition/faces/{image_id}/img',headers={'x-api-key':KEY}).content==image
        assert len(store.objects)==1
        assert upload(client,image).status_code==201


def test_health_checks_store_and_upstream_but_liveness_is_independent(setup):
    settings, store, backend, image, factory = setup
    with factory() as client:
        assert client.get('/api/v1/consistence/status').json()['objectStorage']=='OK'
        store.fail_check=True
        assert client.get('/api/v1/consistence/status').status_code==503
        assert client.get('/health/live').status_code==200
        store.fail_check=False
        backend.healthy=False
        assert client.get('/api/v1/consistence/status').status_code==503


def test_body_limit_invalid_images_and_invalid_credentials_are_rejected(setup):
    settings, store, backend, image, factory = setup
    with factory() as client:
        assert upload(client,b'invalid').status_code==400
        assert client.get('/api/v1/recognition/faces/nope/img',headers={'x-api-key':KEY}).status_code==400
        assert client.post('/api/v1/recognition/faces',headers={'x-api-key':'invalid'},
                           params={'subject':'alice'},files={'file':('face.png',image)}).status_code==404
        assert not store.objects and backend.uploads==0
    with TestClient(create_app(replace(settings,max_body_bytes=20),store,httpx.MockTransport(backend))) as client:
        assert upload(client,image).status_code==413


def test_endpoint_credentials_are_not_accepted_and_secrets_are_not_in_settings_repr(setup):
    settings, *_=setup
    with pytest.raises(ValueError):
        replace(settings,endpoint='https://key:secret@objects').validate()
    assert 'storage-secret' not in repr(settings)
