"""Validate rendered resources against versioned Kubernetes JSON schemas."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
from urllib.request import Request, urlopen
from urllib.error import URLError

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kubectl', default='kubectl')
    parser.add_argument('--version', default='1.31.0')
    args = parser.parse_args()
    rendered = subprocess.run([args.kubectl, 'kustomize', 'kubernetes'], cwd=ROOT, check=True, stdout=subprocess.PIPE, text=True, encoding='utf-8')
    documents = [d for d in yaml.safe_load_all(rendered.stdout) if d]
    # Also check the optional Redis example and the Secret format example.
    for filename in ['redis-deployment.yaml', 'secret.yaml']:
        documents.extend(d for d in yaml.safe_load_all((ROOT/'kubernetes'/filename).read_text(encoding='utf-8')) if d)
    cache = ROOT/'test-results/kubernetes-schemas'/args.version
    cache.mkdir(parents=True, exist_ok=True)
    def filename(doc):
        kind = doc['kind'].lower()
        group, _, version = doc['apiVersion'].partition('/')
        return f'{kind}-{group.split(".")[0]}-{version}.json' if version else f'{kind}-{group}.json'
    def fetch(name):
        path = cache/name
        if not path.exists():
            suffix=f'v{args.version}-standalone-strict/{name}'
            url='https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/'+suffix
            try:
                with urlopen(url, timeout=20) as response:
                    schema=json.load(response)
            except (URLError, TimeoutError):
                request=Request('https://api.github.com/repos/yannh/kubernetes-json-schema/contents/'+suffix,
                                headers={'Accept':'application/vnd.github.raw+json','User-Agent':'FaceSDK-config-tests'})
                with urlopen(request, timeout=20) as response:
                    schema=json.load(response)
            path.write_text(json.dumps(schema), encoding='utf-8')
        return name, json.loads(path.read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=6) as pool:
        schemas=dict(pool.map(fetch, sorted({filename(d) for d in documents})))
    for document in documents:
        schema=schemas[filename(document)]
        if '$schema' not in schema or 'properties' not in schema:
            raise ValueError('Downloaded resource is not a Kubernetes schema')
        jsonschema.Draft4Validator(schema).validate(document)
        print(f"VALID {document['kind']} {document['metadata']['name']}")
    print(f'{len(documents)} resources valid against Kubernetes {args.version} strict schemas')


if __name__ == '__main__':
    main()
