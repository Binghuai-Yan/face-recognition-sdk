"""Verify backup/restore on the isolated test PostgreSQL container."""
import argparse
from pathlib import Path
import subprocess
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker', default='docker')
    parser.add_argument('--project')
    parser.add_argument('--kubectl', default='kubectl')
    parser.add_argument('--kubeconfig')
    args = parser.parse_args()
    if args.kubeconfig:
        kube = [args.kubectl,'--kubeconfig',args.kubeconfig]
        context = subprocess.run(kube+['config','current-context'],check=True,
                                 stdout=subprocess.PIPE,text=True).stdout.strip()
        if context != 'kind-facesdk-fulltest':
            raise ValueError('Only the dedicated FaceSDK kind cluster may be mutated')
        result = subprocess.run(kube+['-n','facesdk','get','pods','-l','app=postgres','-o',
                                      'jsonpath={.items[0].metadata.name}'],check=True,
                                stdout=subprocess.PIPE,text=True)
        prefix = kube+['-n','facesdk','exec','-i',result.stdout,'--']
        deployment = 'kubernetes'
    else:
        if not args.project or not args.project.startswith('facesdk-fulltest-'):
            raise ValueError('Only isolated FaceSDK full-test projects may be mutated')
        prefix = [args.docker,'exec','-i',args.project+'-postgres-1']
        deployment = 'compose'
    def run(command, data=None):
        return subprocess.run(prefix+command, input=data,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    def sql(database, query):
        return run(['psql','-v','ON_ERROR_STOP=1','-U','compreface','-d',database,'-At','-c',query]).decode().strip()
    marker = uuid.uuid4().hex
    sql('compreface', "CREATE TABLE IF NOT EXISTS facesdk_runtime_canary (value text PRIMARY KEY); INSERT INTO facesdk_runtime_canary VALUES ('"+marker+"');")
    assert 'uuid-ossp' in sql('compreface', 'SELECT extname FROM pg_extension;')
    tables = sql('compreface', "SELECT quote_ident(table_schema)||'.'||quote_ident(table_name) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name;").splitlines()
    counts = {table:sql('compreface','SELECT count(*) FROM '+table+';') for table in tables}
    backup = run(['pg_dump','-U','compreface','-d','compreface','-Fc'])
    output = Path('test-results/'+deployment+'-database-backup.dump')
    output.write_bytes(backup)
    restored = 'facesdk_restore_'+uuid.uuid4().hex[:12]
    sql('postgres','CREATE DATABASE '+restored+';')
    try:
        run(['pg_restore','--exit-on-error','--no-owner','-U','compreface','-d',restored],backup)
        assert sql(restored,"SELECT count(*) FROM facesdk_runtime_canary WHERE value='"+marker+"';") == '1'
        assert 'uuid-ossp' in sql(restored,'SELECT extname FROM pg_extension;')
        assert all(sql(restored,'SELECT count(*) FROM '+table+';') == count for table,count in counts.items())
        print('PostgreSQL real pg_dump/pg_restore, all table row counts, canary and uuid-ossp passed')
    finally:
        sql('postgres','DROP DATABASE '+restored+';')


if __name__ == '__main__':
    main()
