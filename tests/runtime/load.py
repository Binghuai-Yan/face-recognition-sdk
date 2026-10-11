"""Bounded concurrent real-model load test with response assertions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics
import time

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--requests', type=int, default=20)
    parser.add_argument('--concurrency', type=int, default=2)
    args = parser.parse_args()
    env = json.loads(Path(args.config).read_text())['env']
    image = Path(env['FACESDK_TEST_IMAGE']).read_bytes()
    def request(index):
        verification = index%2 == 1
        service = 'VERIFICATION' if verification else 'DETECTION'
        endpoint = '/api/v1/verification/verify' if verification else '/api/v1/detection/detect'
        fields = ['source_image','target_image'] if verification else ['file']
        started = time.perf_counter()
        response = requests.post(env['FACESDK_API_URL']+endpoint,
                                 headers={'x-api-key':env['FACESDK_'+service+'_API_KEY']},
                                 files={f:('face.jpg',image,'image/jpeg') for f in fields}, timeout=120)
        response.raise_for_status()
        faces = response.json()['result']
        assert len(faces)==1
        if verification:
            assert len(faces[0]['face_matches'])==1 and faces[0]['face_matches'][0]['similarity']>=0.8
        return time.perf_counter()-started
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        durations = list(pool.map(request, range(args.requests)))
    elapsed = time.perf_counter()-started
    report = {'requests':args.requests,'concurrency':args.concurrency,'failures':0,
              'seconds':round(elapsed,3),'requests_per_second':round(args.requests/elapsed,3),
              'latency_mean_ms':round(statistics.mean(durations)*1000,2),
              'latency_max_ms':round(max(durations)*1000,2)}
    Path('test-results/model-load.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
