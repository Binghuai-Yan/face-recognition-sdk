"""Create an isolated test application using the real CompreFace admin API.

Writes credentials only to an ignored JSON file, never to stdout.
"""
import argparse
import json
import hashlib
from pathlib import Path
import secrets
import struct
import time
import uuid

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--web-url', default='http://localhost:18083/')
    args = parser.parse_args()
    url = args.url.rstrip('/')
    deadline = time.monotonic() + 600
    while True:
        try:
            response = requests.get(url+'/api/v1/consistence/status', timeout=15)
            if response.ok and response.json().get('status') == 'OK':
                break
        except (requests.RequestException, ValueError):
            pass
        if time.monotonic() >= deadline:
            raise TimeoutError('CompreFace dependencies did not become healthy')
        time.sleep(5)
    session = requests.Session()
    email = 'facesdk-'+uuid.uuid4().hex+'@example.test'
    password = 'FaceSDK!'+secrets.token_hex(20)
    response = session.post(url+'/admin/user/register', json={
        'email':email, 'password':password, 'firstName':'FaceSDK',
        'lastName':'RuntimeTests', 'isAllowStatistics':False,
    }, timeout=30)
    response.raise_for_status()
    response = session.post(url+'/admin/oauth/token',
        auth=('CommonClientId','password'),
        data={'username':email,'password':password,'grant_type':'password'}, timeout=30)
    response.raise_for_status()
    session.headers['Authorization'] = 'Bearer '+response.json()['access_token']
    response = session.post(url+'/admin/app', json={'name':'FaceSDK '+uuid.uuid4().hex[:12]}, timeout=30)
    response.raise_for_status()
    application = response.json()['id']
    env = {'FACESDK_LIVE':'1','FACESDK_API_URL':url,'FACESDK_WEB_URL':args.web_url,
           'FACESDK_TEST_IMAGE':str(Path(args.image).resolve())}
    for service, kind in [('detection','DETECTION'),('recognition','RECOGNITION'),('verification','VERIFY'),('other_recognition','RECOGNITION')]:
        response = session.post(url+'/admin/app/'+application+'/model',
                                json={'name':service,'type':kind}, timeout=30)
        response.raise_for_status()
        env['FACESDK_'+service.upper()+'_API_KEY'] = response.json()['apiKey']
    response = session.post(url+'/api/v1/detection/detect', params={'face_plugins':'calculator'},
                            headers={'x-api-key':env['FACESDK_DETECTION_API_KEY']},
                            files={'file':('test-face.jpg',Path(args.image).read_bytes(),'image/jpeg')}, timeout=120)
    response.raise_for_status()
    faces = response.json()['result']
    assert len(faces) == 1, 'Runtime fixture must contain exactly one detectable face'
    embedding = faces[0]['embedding']
    assert embedding, 'Real calculator plugin must return an embedding'
    feature = struct.pack('<'+str(len(embedding))+'f', *embedding)
    env['FACESDK_FEATURE_SHA256'] = hashlib.sha256(feature).hexdigest()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'env':env, 'admin':{'email':email,'password':password,'application':application}}), encoding='utf-8')
    print('Real Detection, Recognition and Verification services created; credentials saved privately')


if __name__ == '__main__':
    main()
