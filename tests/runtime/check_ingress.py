"""Verify real API/UI hostname routing and TLS with curl's trusted CA checks."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--curl', default='curl')
    parser.add_argument('--config', required=True)
    parser.add_argument('--certificate', required=True)
    parser.add_argument('--https-port', type=int, default=18445)
    parser.add_argument('--http-port', type=int, default=18082)
    args = parser.parse_args()
    env = json.loads(Path(args.config).read_text(encoding='utf-8'))['env']
    def request(host, path, extra=None):
        command = [args.curl,'--silent','--show-error','--fail','--max-time','120',
                   '--resolve',f'{host}:{args.https_port}:127.0.0.1',
                   '--cacert',args.certificate]+(extra or [])+[f'https://{host}:{args.https_port}{path}']
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            raise AssertionError('TLS request failed for '+host+path)
        return result.stdout
    assert json.loads(request('api.facesdk.local','/api/v1/consistence/status'))['status']=='OK'
    assert b'<html' in request('ui.facesdk.local','/').lower()
    detected = json.loads(request('api.facesdk.local','/api/v1/detection/detect',
        ['--header','x-api-key: '+env['FACESDK_DETECTION_API_KEY'],
         '--form','file=@'+env['FACESDK_TEST_IMAGE']]))
    assert len(detected['result']) == 1
    result = subprocess.run([args.curl,'--silent','--show-error','--max-time','15','-D','-','-o',
                             'NUL' if __import__('os').name=='nt' else '/dev/null',
                             '--header','Host: api.facesdk.local',f'http://127.0.0.1:{args.http_port}/'],
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    headers = result.stdout.decode('utf-8',errors='replace')
    assert ' 308 ' in headers or ' 301 ' in headers
    assert 'https://api.facesdk.local' in headers
    output = {'trusted_tls_sni_api_hostname':'passed','trusted_tls_sni_ui_hostname':'passed',
              'real_detection_through_ingress':'passed','http_to_https_redirect':'passed'}
    Path('test-results/kubernetes-ingress.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print('Ingress API/UI SNI, trusted TLS, real detection and HTTP redirect passed')


if __name__ == '__main__':
    main()
