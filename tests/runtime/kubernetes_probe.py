"""Exercise DB failure/recovery only in the dedicated FaceSDK kind cluster."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kubectl', default='kubectl')
    parser.add_argument('--kubeconfig', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--marker', required=True)
    args = parser.parse_args()
    base = [args.kubectl, '--kubeconfig', args.kubeconfig]
    def run(*command):
        return subprocess.run(base+list(command), check=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, encoding='utf-8').stdout
    context = run('config', 'current-context').strip()
    if context != 'kind-facesdk-fulltest':
        raise ValueError('This fault test requires the dedicated kind-facesdk-fulltest context')
    def pod():
        items = json.loads(run('-n','facesdk','get','pods','-l','app=compreface-api','-o','json'))['items']
        assert len(items) == 1, 'Fault test expects one API Pod'
        value = items[0]
        return {'uid':value['metadata']['uid'],
                'ready':any(c['type']=='Ready' and c['status']=='True' for c in value['status'].get('conditions',[])),
                'restarts':sum(c['restartCount'] for c in value['status'].get('containerStatuses',[]))}
    def wait_ready(expected, timeout):
        deadline = time.monotonic()+timeout
        while pod()['ready'] != expected:
            if time.monotonic() >= deadline:
                raise TimeoutError('API readiness did not reach the expected state')
            time.sleep(5)
    before = pod()
    assert before['ready']
    start = time.monotonic()
    unavailable = False
    try:
        run('-n','facesdk','scale','deployment/postgres','--replicas=0')
        print('Database scaled to zero; waiting for API readiness=False', flush=True)
        wait_ready(False, 150)
        unavailable = True
        print('API readiness=False observed', flush=True)
        # Exceed the liveness failure window while checking the same Pod survives.
        while time.monotonic()-start < 120:
            current = pod()
            assert current['uid']==before['uid'] and current['restarts']==before['restarts']
            time.sleep(5)
    finally:
        run('-n','facesdk','scale','deployment/postgres','--replicas=1')
        print('Database restored to one replica', flush=True)
    outage = round(time.monotonic()-start, 2)
    assert unavailable
    run('-n','facesdk','rollout','status','deployment/postgres','--timeout=240s')
    wait_ready(True, 300)
    after = pod()
    assert after['uid']==before['uid'] and after['restarts']==before['restarts']
    root = Path(__file__).resolve().parents[2]
    process = subprocess.run([sys.executable,str(root/'tests/runtime/persistence.py'),
                              '--config',args.config,'--marker',args.marker,'verify'],
                             stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if process.returncode:
        raise AssertionError('Persistent face verification failed; inspect the isolated service privately')
    result = {'readiness_false_during_database_outage':'passed',
              'readiness_true_after_recovery':'passed',
              'same_api_pod_without_liveness_restart':'passed',
              'persistent_subject_face_and_recognition':'passed',
              'database_outage_seconds':outage,
              'api_restart_count_before':before['restarts'],
              'api_restart_count_after':after['restarts']}
    (root/'test-results/kubernetes-recovery.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Kubernetes readiness, liveness isolation and PVC data recovery passed', flush=True)


if __name__ == '__main__':
    main()
