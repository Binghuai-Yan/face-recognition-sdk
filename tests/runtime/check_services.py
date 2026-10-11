"""Assert real gateway, monitoring and cache behavior on an isolated test stack."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import time

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--docker', default='docker')
    parser.add_argument('--project', required=True)
    args = parser.parse_args()
    if not args.project.startswith('facesdk-fulltest-'):
        raise ValueError('Use an isolated test project')
    env = json.loads(Path(args.config).read_text())['env']
    values = dict(line.split('=',1) for line in Path(args.env_file).read_text().splitlines() if '=' in line)
    results = {}
    def passed(name):
        results[name] = 'passed'
        print(name+': PASSED', flush=True)
    health = requests.get(env['FACESDK_API_URL']+'/api/v1/consistence/status', timeout=30)
    health.raise_for_status(); assert health.json()['status']=='OK'
    passed('real-api-core-database-health')
    response = requests.get('https://localhost:18443/api/v1/consistence/status',
                            verify=str(Path('docker-compose/nginx/ssl/fullchain.pem').resolve()), timeout=30)
    response.raise_for_status(); assert response.json()['status']=='OK'
    passed('gateway-tls-verified-certificate')
    response = requests.get('http://localhost:18080/', allow_redirects=False, timeout=10)
    assert response.status_code==301 and response.headers['Location'].startswith('https://')
    passed('gateway-http-redirect')
    def request(_):
        return requests.get('https://localhost:18443/api/v1/consistence/status',
                            headers={'x-api-key':env['FACESDK_DETECTION_API_KEY']},
                            verify=str(Path('docker-compose/nginx/ssl/fullchain.pem').resolve()), timeout=30).status_code
    with ThreadPoolExecutor(max_workers=20) as pool:
        statuses = list(pool.map(request,range(60)))
    assert 429 in statuses and 200 in statuses and set(statuses)<={200,429}
    passed('gateway-real-rate-limit')
    for expression in ['pg_up', 'probe_success{job="facesdk-health"}']:
        deadline = time.monotonic()+60
        while True:
            response = requests.get('http://localhost:19090/api/v1/query', params={'query':expression}, timeout=10)
            response.raise_for_status(); metrics = response.json()['data']['result']
            if metrics and all(r['value'][1]=='1' for r in metrics):break
            if time.monotonic()>=deadline:raise AssertionError('Missing healthy metric: '+expression)
            time.sleep(3)
    passed('prometheus-real-database-and-api-probes')
    response = requests.get('http://localhost:13000/api/datasources', auth=('admin',values['GRAFANA_ADMIN_PASSWORD']), timeout=10)
    response.raise_for_status(); assert any(d['type']=='prometheus' for d in response.json())
    response = requests.get('http://localhost:13000/api/search', auth=('admin',values['GRAFANA_ADMIN_PASSWORD']), timeout=10)
    response.raise_for_status(); assert response.json()
    passed('grafana-datasource-and-dashboard')
    response = requests.get('http://localhost:9093/-/ready',timeout=10)
    response.raise_for_status()
    passed('alertmanager-real-readiness')
    container=args.project+'-redis-1'
    response = subprocess.run([args.docker,'exec',container,'redis-cli','ping'], check=True, stdout=subprocess.PIPE,text=True)
    assert 'NOAUTH' in response.stdout
    response = subprocess.run([args.docker,'exec',container,'sh','-c','REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli ping'], check=True,stdout=subprocess.PIPE,text=True)
    assert response.stdout.strip()=='PONG'
    passed('redis-rejects-anonymous-and-accepts-authenticated')
    output=Path('test-results/runtime-checks.json')
    previous=json.loads(output.read_text()) if output.exists() else {}
    previous.update(results); output.write_text(json.dumps(previous,indent=2)+'\n')


if __name__ == '__main__':
    main()
