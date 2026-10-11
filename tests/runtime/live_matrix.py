"""Run only the four-language real-model checks for a deployment variant."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not args.name.replace('-', '').isalnum():
        raise ValueError('Use an alphanumeric deployment name')
    env = dict(os.environ)
    env.update(json.loads(Path(args.config).read_text(encoding='utf-8'))['env'])
    env['FACESDK_LIVE'] = '1'
    go = env.get('FACESDK_GO') or shutil.which('go') or 'go'
    java = str(Path(env['JAVA_HOME'])/'bin'/('java.exe' if os.name == 'nt' else 'java')) if env.get('JAVA_HOME') else 'java'
    checks = [
        ('python', [sys.executable,'-m','pytest','tests/integration/test_python','tests/runtime/test_model.py','-q'], ROOT),
        ('node', ['node','tests/integration/live/node.cjs'], ROOT),
        ('go', [go,'run','.'], ROOT/'tests/integration/live/go'),
        ('java', [java,'--class-path',str(ROOT/'sdk/java/target/facesdk-java-1.0.0.jar'),str(ROOT/'tests/integration/live/LiveSmoke.java')], ROOT),
    ]
    output = ROOT/'test-results'
    output.mkdir(exist_ok=True)
    results = []
    for name, command, cwd in checks:
        start = time.monotonic()
        process = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        log = process.stdout
        for key, value in env.items():
            if key.startswith('FACESDK_') and any(word in key for word in ['API_KEY','PASSWORD','TOKEN']) and value:
                log = log.replace(value, '[REDACTED]')
        (output/(args.name+'-'+name+'.log')).write_text(log, encoding='utf-8')
        results.append({'check':name,'exit_code':process.returncode,
                        'status':'passed' if process.returncode == 0 else 'failed',
                        'seconds':round(time.monotonic()-start, 2)})
        print(args.name+' '+name+': '+results[-1]['status'], flush=True)
        if process.returncode:
            print(log[-3000:], flush=True)
    (output/(args.name+'-summary.json')).write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
    return int(any(r['exit_code'] for r in results))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main())
