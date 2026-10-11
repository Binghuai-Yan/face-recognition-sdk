"""Bounded OSS outage/recreation checks on an explicitly isolated Docker project."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import quote
import uuid

import boto3
from botocore.config import Config
import requests

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--env-file',required=True)
    parser.add_argument('--project',required=True)
    parser.add_argument('--docker',default='docker')
    parser.add_argument('--compose',default='docker-compose')
    args=parser.parse_args()
    if not args.project.startswith('facesdk-fulltest-'):
        raise ValueError('Use an isolated facesdk-fulltest project')
    env=json.loads(Path(args.config).read_text())['env']
    url=env['FACESDK_API_URL'].rstrip('/')
    key=env['FACESDK_RECOGNITION_API_KEY']
    bucket=env['FACESDK_OSS_BUCKET']
    s3=boto3.client('s3',endpoint_url=env['FACESDK_OSS_ENDPOINT'],region_name=env.get('FACESDK_OSS_REGION','us-east-1'),
        aws_access_key_id=env['FACESDK_OSS_ACCESS_KEY_ID'],aws_secret_access_key=env['FACESDK_OSS_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4',connect_timeout=5,read_timeout=10,
                      retries={'total_max_attempts':1},s3={'addressing_style':'path'},
                      request_checksum_calculation='when_required',response_checksum_validation='when_required'))
    prefix=env.get('FACESDK_OSS_PREFIX','faces')+'/'+hashlib.sha256(key.encode()).hexdigest()+'/'
    subject='OSS fault '+uuid.uuid4().hex
    data=Path(env['FACESDK_TEST_IMAGE']).read_bytes()
    results={}
    def passed(name):
        results[name]='passed'
        print(name+': PASSED',flush=True)
    def command(argv,cwd=ROOT):
        result=subprocess.run(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError('Test container operation failed (details retained privately)')
        return result.stdout.decode('utf-8',errors='replace').strip()
    def control(operation,service):
        command([args.docker,operation,args.project+'-'+service+'-1'])
    def recreate(services):
        command([args.compose,'-p',args.project,'--env-file',str(Path(args.env_file).resolve()),
                 'up','-d','--no-build','--no-deps','--force-recreate',*services],ROOT/'docker-compose')
    def journal_script(script):
        command([args.docker,'run','--rm','--network','none','--volume',args.project+'_oss-journal:/data',
                 'facesdk/oss-gateway:1.0.0','python','-c',script])
    def request(method,path,**kwargs):
        return requests.request(method,url+path,headers={'x-api-key':key},timeout=120,**kwargs)
    def objects():
        return {obj['Key'] for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket,Prefix=prefix)
                for obj in page.get('Contents',[])}
    def wait(predicate,message,seconds=180):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            try:
                if predicate():
                    return
            except requests.RequestException:
                pass
            time.sleep(2)
        raise TimeoutError(message)
    def ready():
        response=request('GET','/api/v1/consistence/status')
        return response.status_code==200 and response.json().get('objectStorage')=='OK'
    def add():
        response=request('POST','/api/v1/recognition/faces',params={'subject':subject},
                         files={'file':('face.jpg',data,'image/jpeg')})
        assert response.status_code==201
        return str(uuid.UUID(response.json()['image_id']))
    wait(ready,'Initial OSS health did not become ready')
    baseline=objects()
    try:
        image_id=add()
        sql="SELECT count(*)=1 AND coalesce(max(octet_length(i.content)),0)=0 FROM embedding e LEFT JOIN img i ON e.img_id=i.id WHERE e.id='"+image_id+"';"
        answer=command([args.docker,'exec',args.project+'-postgres-1','psql','-U','compreface','-d','compreface','-At','-c',sql])
        assert answer=='t','A new original was stored in PostgreSQL or embedding was absent'
        passed('new-original-not-stored-in-postgresql')
        control('stop','oss-gateway')
        journal_script("import sqlite3\ns=sqlite3.connect('/data/storage.sqlite3')\nb=sqlite3.connect('/data/test-backup.sqlite3')\ns.backup(b)\nb.close()\ns.execute('DELETE FROM images')\ns.commit()\ns.close()")
        control('start','oss-gateway')
        wait(ready,'Gateway did not restart for journal restore test')
        assert request('GET','/api/v1/recognition/faces/'+image_id+'/img').status_code==404
        control('stop','oss-gateway')
        journal_script("import sqlite3\nfrom pathlib import Path\nb=sqlite3.connect('/data/test-backup.sqlite3')\ns=sqlite3.connect('/data/storage.sqlite3')\nb.backup(s)\ns.close()\nb.close()\nPath('/data/test-backup.sqlite3').unlink()")
        control('start','oss-gateway')
        wait(ready,'Gateway did not recover its restored journal')
        response=request('GET','/api/v1/recognition/faces/'+image_id+'/img')
        assert response.status_code==200 and response.content==data
        passed('sqlite-backup-restores-original-image-association')
        recreate(['rustfs','oss-gateway'])
        wait(ready,'Recreated RustFS/gateway did not recover')
        response=request('GET','/api/v1/recognition/faces/'+image_id+'/img')
        assert response.status_code==200 and response.content==data and len(objects()-baseline)==1
        passed('rustfs-and-journal-survive-container-recreation')
        control('stop','rustfs')
        response=request('GET','/api/v1/consistence/status')
        assert response.status_code==503
        assert request('GET','/health/live').status_code==200
        passed('storage-outage-revokes-readiness-with-live-process')
        response=request('POST','/api/v1/recognition/faces',params={'subject':subject},files={'file':('face.jpg',data,'image/jpeg')})
        assert response.status_code==503
        listing=request('GET','/api/v1/recognition/faces',params={'subject':subject,'size':10,'page':0})
        assert listing.status_code==200 and [f['image_id'] for f in listing.json()['faces']]==[image_id]
        passed('storage-outage-upload-does-not-register-a-face')
        response=request('DELETE','/api/v1/recognition/faces/'+image_id)
        assert response.status_code==200 and response.headers['x-facesdk-object-delete']=='pending'
        assert request('GET','/api/v1/recognition/faces/'+image_id+'/img').status_code==404
        passed('storage-outage-delete-revokes-access-and-queues-object')
        recreate(['oss-gateway'])
        wait(lambda:request('GET','/health/live').status_code==200,'Gateway did not restart during OSS outage')
        control('start','rustfs')
        wait(ready,'OSS did not recover after restart')
        wait(lambda:objects()==baseline,'Durable delete outbox did not drain')
        passed('delete-outbox-survives-gateway-recreation-and-drains')
    finally:
        control('start','oss-gateway')
        control('start','rustfs')
        wait(ready,'OSS failed to recover during cleanup')
        response=request('DELETE','/api/v1/recognition/subjects/'+quote(subject,safe=''))
        assert response.status_code in (200,404)
        wait(lambda:objects()==baseline,'Test object cleanup did not complete')
        (ROOT/'test-results/oss-faults-summary.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    main()
