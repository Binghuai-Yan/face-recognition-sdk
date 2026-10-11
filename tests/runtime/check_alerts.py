"""Verify Prometheus -> Alertmanager delivery during an isolated DB outage."""
import argparse
import json
from pathlib import Path
import time

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('state', choices=['firing', 'resolved'])
    parser.add_argument('--prometheus', default='http://localhost:19090')
    parser.add_argument('--alertmanager', default='http://localhost:9093')
    args = parser.parse_args()
    expected = {'FaceSDKAPIDown', 'PostgreSQLDown'}
    deadline = time.monotonic()+240
    while True:
        response = requests.get(args.prometheus+'/api/v1/alerts', timeout=10)
        response.raise_for_status()
        prometheus = {a['labels']['alertname'] for a in response.json()['data']['alerts']
                      if a['state'] == 'firing'}
        response = requests.get(args.alertmanager+'/api/v2/alerts', timeout=10)
        response.raise_for_status()
        alertmanager = {a['labels']['alertname'] for a in response.json()
                        if a['status']['state'] == 'active'}
        if args.state == 'firing':
            passed = expected <= prometheus and expected <= alertmanager
        else:
            passed = not (expected & prometheus) and not (expected & alertmanager)
            for expression in ['pg_up{job="postgres"}', 'probe_success{job="facesdk-health"}']:
                response = requests.get(args.prometheus+'/api/v1/query', params={'query':expression}, timeout=10)
                response.raise_for_status()
                metrics = response.json()['data']['result']
                passed = passed and bool(metrics) and all(m['value'][1] == '1' for m in metrics)
        if passed:
            output = Path('test-results/fault-recovery.json')
            results = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
            results['prometheus-alertmanager-'+args.state] = 'passed'
            output.write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
            print('Both API/database alerts '+args.state+' in Prometheus and Alertmanager')
            return
        if time.monotonic() >= deadline:
            raise AssertionError('Expected alert delivery/state was not observed')
        time.sleep(5)


if __name__ == '__main__':
    main()
