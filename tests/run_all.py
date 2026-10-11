"""Run reproducible checks; do not report missing tools as successful checks."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Require and run the real CompreFace tests')
    parser.add_argument('--race', action='store_true', help='Require Go race tests (needs a C compiler)')
    parser.add_argument('--audit', action='store_true', help='Audit production npm dependencies against the official registry')
    parser.add_argument('--oss-live', action='store_true', help='Require real S3-compatible storage lifecycle tests')
    parser.add_argument('--live-config', help='Ignored JSON file containing an env mapping for real-service tests')
    args = parser.parse_args()
    if args.live_config:
        config = json.loads(Path(args.live_config).read_text(encoding='utf-8'))
        os.environ.update({key:str(value) for key,value in config['env'].items() if key.startswith('FACESDK_')})
    results = []
    output = ROOT/'test-results'
    output.mkdir(exist_ok=True)
    def run(name, command, cwd=ROOT, env=None, skip_reason=None):
        start = time.monotonic()
        print(f'Running {name}...', flush=True)
        try:
            process = subprocess.run(command, cwd=cwd, env=env or os.environ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
            status = process.returncode
            log = process.stdout
        except OSError as error:
            status, log = 127, str(error)
        for key, value in os.environ.items():
            if key.startswith(('FACESDK_','OSS_','RUSTFS_')) and any(word in key for word in ['API_KEY','PASSWORD','TOKEN','SECRET','ACCESS_KEY']) and value:
                log = log.replace(value, '[REDACTED]')
        (output/(name+'.log')).write_text(log, encoding='utf-8')
        state = 'skipped' if status == 0 and skip_reason else ('passed' if status == 0 else 'failed')
        results.append({'check':name,'exit_code':status,'status':state,'seconds':round(time.monotonic()-start,2)})
        if state == 'skipped':
            results[-1]['reason'] = skip_reason
        print(f'{name}: {state.upper()} ({results[-1]["seconds"]}s)', flush=True)
        if status:
            print(log[-4000:], flush=True)
        return status==0
    def tool(name, override):
        return os.environ.get(override) or shutil.which(name) or name
    npm = tool('npm.cmd' if os.name=='nt' else 'npm','FACESDK_NPM')
    mvn = tool('mvn.cmd' if os.name=='nt' else 'mvn','FACESDK_MAVEN')
    go = tool('go','FACESDK_GO')
    java_args = [mvn,'-B','-ntp']
    if os.getenv('FACESDK_MAVEN_SETTINGS'):
        java_args += ['-s',os.environ['FACESDK_MAVEN_SETTINGS']]
    run('python-install',[sys.executable,'-m','pip','install','./sdk/python'])
    run('oss-gateway-install',[sys.executable,'-m','pip','install','-r','services/oss-gateway/requirements.txt'])
    run('oss-gateway-tests',[sys.executable,'-m','pytest','services/oss-gateway/tests','-q','--junitxml=test-results/oss-gateway.xml'])
    run('python-tests',[sys.executable,'-m','pytest','sdk/python/tests','tests/config','-q','--junitxml=test-results/python.xml'])
    run('python-package',[sys.executable,'-m','build','--no-isolation'],ROOT/'sdk/python')
    wheels=list((ROOT/'sdk/python/dist').glob('*.whl'))
    if wheels:
        with tempfile.TemporaryDirectory(prefix='facesdk-install-') as task_dir:
            venv=Path(task_dir)/'venv'
            if run('fresh-venv',[sys.executable,'-m','venv',str(venv)]):
                python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
                run('fresh-install',[str(python),'-m','pip','install',str(max(wheels,key=lambda p:p.stat().st_mtime))],Path(task_dir))
                run('fresh-import',[str(python),'-c','import facesdk, aiofiles; from facesdk import FaceSDKClient, AsyncFaceSDKClient; print(facesdk.__file__)'],Path(task_dir))
                run('fresh-dependencies',[str(python),'-m','pip','check'],Path(task_dir))
    run('java-verify-install',java_args+['clean','install'],ROOT/'sdk/java')
    run('ruoyi-tests',java_args+['clean','verify'],ROOT/'tests/ruoyi')
    run('go-tests',[go,'test','-count=1','-v','./...'],ROOT/'sdk/go')
    run('go-vet',[go,'vet','./...'],ROOT/'sdk/go')
    if args.race:
        run('go-race',[go,'test','-race','./...'],ROOT/'sdk/go')
    run('node-install',[npm,'ci'],ROOT/'sdk/nodejs')
    run('node-tests',[npm,'test','--','--runInBand'],ROOT/'sdk/nodejs')
    run('node-lint',[npm,'run','lint'],ROOT/'sdk/nodejs')
    run('node-types',[npm,'run','typecheck'],ROOT/'sdk/nodejs')
    run('node-package',[npm,'pack','--dry-run'],ROOT/'sdk/nodejs')
    if args.audit:
        run('node-production-audit',[npm,'audit','--omit=dev','--registry=https://registry.npmjs.org','--json'],ROOT/'sdk/nodejs')
    run('web-install',[npm,'ci'],ROOT/'facesdk-web')
    run('web-tests',[npm,'test'],ROOT/'facesdk-web')
    run('web-lint',[npm,'run','lint','--','--no-fix'],ROOT/'facesdk-web')
    run('web-build',[npm,'run','build'],ROOT/'facesdk-web')
    if args.audit:
        run('web-production-audit',[npm,'audit','--omit=dev','--registry=https://registry.npmjs.org','--json'],ROOT/'facesdk-web')
    compose=os.getenv('FACESDK_COMPOSE') or shutil.which('docker-compose')
    compose_cmd=[compose] if compose else [tool('docker','FACESDK_DOCKER'),'compose']
    run('compose-config',compose_cmd+['--env-file','.env.example','--profile','*','config','--quiet'],ROOT/'docker-compose')
    run('compose-test-config',compose_cmd+['-f','docker-compose.test.yml','config','--quiet'],ROOT/'docker-compose')
    run('compose-external-oss-config',compose_cmd+['--env-file','.env.example','-f','docker-compose.yml','-f','docker-compose.external-oss.yml','config','--quiet'],ROOT/'docker-compose')
    kubectl=tool('kubectl','FACESDK_KUBECTL')
    run('kustomize',[kubectl,'kustomize','kubernetes'])
    run('kubernetes-schema',[sys.executable,'tests/validate_kubernetes.py','--kubectl',kubectl])
    live_env=dict(os.environ)
    if args.live:
        live_env['FACESDK_LIVE']='1'
    live_requested = args.live or live_env.get('FACESDK_LIVE')=='1'
    run('live-tests',[sys.executable,'-m','pytest','tests/integration/test_python','tests/runtime/test_model.py','-q','-rs','--junitxml=test-results/live.xml'],env=live_env,
        skip_reason=None if live_requested else 'FACESDK_LIVE is not enabled; real service tests did not run')
    if live_requested:
        run('node-live',['node','tests/integration/live/node.cjs'],env=live_env)
        run('go-live',[go,'run','.'],ROOT/'tests/integration/live/go',env=live_env)
        java = str(Path(os.environ['JAVA_HOME'])/'bin'/('java.exe' if os.name=='nt' else 'java')) if os.getenv('JAVA_HOME') else tool('java','FACESDK_JAVA')
        run('java-live',[java,'--class-path',str(ROOT/'sdk/java/target/facesdk-java-1.0.0.jar'),str(ROOT/'tests/integration/live/LiveSmoke.java')],env=live_env)
    if args.oss_live:
        live_env['FACESDK_OSS_LIVE']='1'
        run('oss-live',[sys.executable,'-m','pytest','tests/runtime/test_object_storage.py','-q','--junitxml=test-results/oss-live.xml'],env=live_env)
    report={'checks':results,'live_requested':live_requested,'oss_live_requested':args.oss_live,'race_requested':args.race,'production_audit_requested':args.audit}
    (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f'Results: {output}',flush=True)
    return 1 if any(r['exit_code'] for r in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
