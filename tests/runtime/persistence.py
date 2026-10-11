"""Create and verify a real face record across isolated deployment changes."""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'sdk/python'))
from facesdk import FaceSDKClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--marker', required=True)
    parser.add_argument('action', choices=['create', 'verify', 'remove', 'wait', 'unavailable'])
    args = parser.parse_args()
    env = json.loads(Path(args.config).read_text(encoding='utf-8'))['env']
    url = env['FACESDK_API_URL'].rstrip('/')
    if args.action in ['wait', 'unavailable']:
        deadline = time.monotonic() + (600 if args.action == 'wait' else 120)
        while True:
            try:
                response = requests.get(url+'/api/v1/consistence/status', timeout=10)
                healthy = response.ok and response.json().get('status') == 'OK'
            except (requests.RequestException, ValueError):
                healthy = False
            if healthy == (args.action == 'wait'):
                print('Health state verified: '+('OK' if healthy else 'unavailable'))
                return
            if time.monotonic() >= deadline:
                raise TimeoutError('Expected health state was not observed')
            time.sleep(3)
    keys = {s:env['FACESDK_'+s.upper()+'_API_KEY'] for s in ['detection','recognition','verification']}
    image = Path(env['FACESDK_TEST_IMAGE']).read_bytes()
    marker_path = Path(args.marker)
    with FaceSDKClient(url, api_keys=keys, timeout=120, max_retries=0) as client:
        if args.action == 'create':
            if marker_path.exists():
                raise FileExistsError('Use a new marker path to avoid losing an existing test record')
            subject = 'facesdk-persist-'+uuid.uuid4().hex
            client.create_subject(subject)
            record = client.add_face(subject, image)
            marker_path.write_text(json.dumps({'subject':subject,'image_id':record.image_id}), encoding='utf-8')
        else:
            marker = json.loads(marker_path.read_text(encoding='utf-8'))
            if args.action == 'remove':
                client.delete_subject(marker['subject'])
            else:
                assert marker['subject'] in [s.subject_id for s in client.list_subjects()]
                result = client.search(image, limit=100, threshold=0.8)
                assert any(m.subject_id == marker['subject'] and m.match for m in result.results)
                response = requests.get(url+'/api/v1/recognition/faces',
                    headers={'x-api-key':keys['recognition']},
                    params={'subject':marker['subject'],'size':100}, timeout=30)
                response.raise_for_status()
                assert any(face['image_id'] == marker['image_id'] for face in response.json()['faces'])
        print('Real subject, stored face and recognition persistence: '+args.action+' passed')


if __name__ == '__main__':
    main()
