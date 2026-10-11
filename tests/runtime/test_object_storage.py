"""Real object storage tests. Use a dedicated test service and a private bucket."""
import base64
import hashlib
import io
import os
from pathlib import Path
from urllib.parse import quote
import uuid

import boto3
from botocore.config import Config
from PIL import Image
import pytest
import requests

pytestmark=pytest.mark.skipif(os.getenv('FACESDK_OSS_LIVE')!='1',reason='Requires explicitly enabled real object storage')
FACES='/api/v1/recognition/faces'
INVALID_KEY='00000000-0000-4000-8000-000000000000'


@pytest.fixture
def storage():
    url=os.environ['FACESDK_API_URL'].rstrip('/')
    key=os.environ['FACESDK_RECOGNITION_API_KEY']
    other=os.environ['FACESDK_OTHER_RECOGNITION_API_KEY']
    bucket=os.environ['FACESDK_OSS_BUCKET']
    endpoint=os.environ['FACESDK_OSS_ENDPOINT']
    s3=boto3.client('s3',endpoint_url=endpoint,region_name=os.getenv('FACESDK_OSS_REGION','us-east-1'),
        aws_access_key_id=os.environ['FACESDK_OSS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['FACESDK_OSS_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4',s3={'addressing_style':'path'},
            request_checksum_calculation='when_required',response_checksum_validation='when_required'))
    prefix=os.getenv('FACESDK_OSS_PREFIX','faces')+'/'+hashlib.sha256(key.encode()).hexdigest()+'/'
    data=Path(os.environ['FACESDK_TEST_IMAGE']).read_bytes()
    subject='OSS 张三 &? '+uuid.uuid4().hex[:16]
    def request(method,path,**kwargs):
        kwargs.setdefault('headers',{'x-api-key':key})
        return requests.request(method,url+path,timeout=120,**kwargs)
    def objects():
        return {item['Key'] for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket,Prefix=prefix)
                for item in page.get('Contents',[])}
    baseline=objects()
    yield request,s3,bucket,endpoint,other,data,subject,objects,baseline
    # Tests create their own subject only. Do not delete unrelated bucket contents.
    response=request('DELETE','/api/v1/recognition/subjects/'+quote(subject,safe=''))
    assert response.status_code in (200,404)
    assert objects()==baseline,'Test objects were not cleaned up'


@pytest.mark.parametrize('base64_input',[False,True])
def test_original_is_private_in_oss_and_only_its_service_can_read(storage,base64_input):
    request,s3,bucket,endpoint,other,data,subject,objects,baseline=storage
    kwargs={'json':{'file':base64.b64encode(data).decode()}} if base64_input else {'files':{'file':('face.jpg',data,'image/jpeg')}}
    response=request('POST',FACES,params={'subject':subject},**kwargs)
    assert response.status_code==201
    image_id=response.json()['image_id']
    added=objects()-baseline
    assert len(added)==1
    object_key=added.pop()
    original=s3.get_object(Bucket=bucket,Key=object_key)
    try:
        assert hashlib.sha256(original['Body'].read()).digest()==hashlib.sha256(data).digest()
    finally:
        original['Body'].close()
    assert original['ContentType']=='image/jpeg'
    assert requests.get(endpoint+'/'+bucket+'/'+object_key,timeout=30).status_code==403
    read=request('GET',FACES+'/'+image_id+'/img')
    assert read.status_code==200 and read.content==data
    assert read.headers['Cache-Control']=='private, no-store'
    legacy=request('GET','/api/v1/static/'+os.environ['FACESDK_RECOGNITION_API_KEY']+'/images/'+image_id)
    assert legacy.status_code==200 and legacy.content==data
    assert request('GET',FACES+'/'+image_id+'/img',headers={'x-api-key':other}).status_code==404
    assert request('DELETE',FACES+'/'+image_id,headers={'x-api-key':other}).status_code==404
    assert request('GET',FACES+'/'+image_id+'/img',headers={'x-api-key':INVALID_KEY}).status_code==404
    response=request('DELETE',FACES+'/'+image_id)
    assert response.status_code==200 and response.headers['x-facesdk-object-delete']=='completed'
    assert objects()==baseline
    assert request('GET',FACES+'/'+image_id+'/img').status_code==404


def test_bulk_and_subject_deletion_remove_only_their_objects(storage):
    request,s3,bucket,endpoint,other,data,subject,objects,baseline=storage
    ids=[]
    for _ in range(2):
        response=request('POST',FACES,params={'subject':subject},files={'file':('face.jpg',data,'image/jpeg')})
        assert response.status_code==201
        ids.append(response.json()['image_id'])
    assert len(objects()-baseline)==2
    response=request('POST',FACES+'/delete',json=[ids[0]])
    assert response.status_code==200 and len(objects()-baseline)==1
    assert request('GET',FACES+'/'+ids[1]+'/img').content==data
    response=request('DELETE','/api/v1/recognition/subjects/'+quote(subject,safe=''))
    assert response.status_code==200 and response.json()['subject']==subject
    assert objects()==baseline


def test_rejected_face_and_invalid_credentials_leave_no_original(storage):
    request,s3,bucket,endpoint,other,data,subject,objects,baseline=storage
    blank=io.BytesIO()
    Image.new('RGB',(64,64),'white').save(blank,format='PNG')
    response=request('POST',FACES,params={'subject':subject},files={'file':('blank.png',blank.getvalue(),'image/png')})
    assert response.status_code==400 and objects()==baseline
    response=request('POST',FACES,params={'subject':subject},headers={'x-api-key':INVALID_KEY},files={'file':('face.jpg',data,'image/jpeg')})
    assert response.status_code==404 and objects()==baseline


def test_duplicate_file_and_subject_are_rejected_before_writing(storage):
    request,s3,bucket,endpoint,other,data,subject,objects,baseline=storage
    response=request('POST',FACES,params={'subject':subject},
                     files=[('file',('a.jpg',data,'image/jpeg')),('file',('b.jpg',data,'image/jpeg'))])
    assert response.status_code==400 and objects()==baseline
    response=request('POST',FACES,params=[('subject',subject),('subject','ambiguous')],
                     files={'file':('a.jpg',data,'image/jpeg')})
    assert response.status_code==400 and objects()==baseline
    response=request('GET',FACES,params={'subject':subject,'size':10,'page':0})
    assert response.status_code==200 and response.json()['faces']==[]
