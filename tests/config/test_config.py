"""Validate deployment wiring and published API examples without a running engine."""
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

import jsonschema
import yaml
from openapi_spec_validator import validate
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT4

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return yaml.safe_load((ROOT / path).read_text(encoding='utf-8'))


def test_openapi_and_official_fixtures():
    spec = load('sdk/openapi/compreface-api.yaml')
    validate(spec)
    fixtures = json.loads((ROOT / 'tests/fixtures/compreface-1.2.json').read_text(encoding='utf-8'))
    # Resolve only local references. The published schemas must accept wire fixtures.
    uri = 'urn:facesdk:openapi'
    registry = Registry().with_resource(uri, Resource.from_contents(spec, default_specification=DRAFT4))
    for fixture, schema in {'detection':'Detection','verification':'Verification','recognition':'Recognition','subjects':'Subjects','created':'Subject','added':'FaceRecord','empty':'Detection'}.items():
        jsonschema.Draft4Validator({'$ref':uri+'#/components/schemas/'+schema}, registry=registry).validate(fixtures[fixture])
    assert set(spec['paths']) == {'/api/v1/detection/detect','/api/v1/verification/verify','/api/v1/recognition/recognize','/api/v1/recognition/subjects','/api/v1/recognition/subjects/{subject}','/api/v1/recognition/faces','/api/v1/recognition/faces/{image_id}','/api/v1/consistence/status'}
    for path, fixture in {'/api/v1/recognition/subjects/{subject}':'created',
                          '/api/v1/recognition/faces/{image_id}':'added'}.items():
        schema = spec['paths'][path]['delete']['responses']['200']['content']['application/json']['schema']
        jsonschema.Draft4Validator({'$ref':uri+schema['$ref']}, registry=registry).validate(fixtures[fixture])
        required = spec['components']['schemas'][schema['$ref'].rsplit('/', 1)[1]]['required']
        assert set(required) == set(fixtures[fixture])
    verify_params = spec['paths']['/api/v1/verification/verify']['post']['parameters']
    recognize_params = spec['paths']['/api/v1/recognition/recognize']['post']['parameters']
    assert 'prediction_count' not in {parameter['name'] for parameter in verify_params}
    assert 'prediction_count' in {parameter['name'] for parameter in recognize_params}


def test_compose_services_mounts_and_credentials():
    spec = load('docker-compose/docker-compose.yml')
    services = spec['services']
    assert {name for name, service in services.items() if not service.get('profiles')} == {'compreface-api','postgres'}
    api, pg = services['compreface-api'], services['postgres']
    assert api['environment']['EXTERNAL_DB'] == 'true'
    assert api['environment']['POSTGRES_URL'].startswith('jdbc:postgresql://postgres:5432/')
    for key in ['POSTGRES_USER','POSTGRES_PASSWORD']:
        assert api['environment'][key] == pg['environment'][key]
    assert any(v.startswith('postgres-data:/var/lib/postgresql/data') for v in pg['volumes'])
    assert not services['redis'].get('ports')
    assert '--requirepass' in ' '.join(services['redis']['command'])
    assert 'consistence/status' in ' '.join(api['healthcheck']['test']) and '"OK"' in ' '.join(api['healthcheck']['test'])
    for service in services.values():
        for volume in service.get('volumes', []):
            source = volume.split(':')[0]
            if source.startswith('.'):
                assert (ROOT/'docker-compose'/source).exists(), source
    test = load('docker-compose/docker-compose.test.yml')
    assert any(v.endswith(':/var/lib/postgresql/data') for v in test['services']['compreface-api']['volumes'])


def kube_documents():
    resources = load('kubernetes/kustomization.yaml')['resources']
    return [doc for filename in resources for doc in yaml.safe_load_all((ROOT/'kubernetes'/filename).read_text(encoding='utf-8')) if doc]


def test_kubernetes_services_and_storage():
    docs = kube_documents()
    services = {d['metadata']['name']: d for d in docs if d['kind']=='Service'}
    deployments = [d for d in docs if d['kind']=='Deployment']
    pvcs = {d['metadata']['name'] for d in docs if d['kind']=='PersistentVolumeClaim'}
    configmaps = {d['metadata']['name'] for d in docs if d['kind']=='ConfigMap'}
    assert {'compreface-api','compreface-ui','postgres'} <= services.keys()
    assert all(d['spec']['type']=='ClusterIP' for d in services.values())
    for ingress in [d for d in docs if d['kind']=='Ingress']:
        assert ingress['spec']['tls']
        for rule in ingress['spec']['rules']:
            for path in rule['http']['paths']:
                assert path['backend']['service']['name'] in services
    for deployment in deployments:
        pod=deployment['spec']['template']['spec']
        for volume in pod.get('volumes', []):
            if 'persistentVolumeClaim' in volume:
                assert volume['persistentVolumeClaim']['claimName'] in pvcs
            if 'configMap' in volume:
                assert volume['configMap']['name'] in configmaps
        for container in pod['containers']:
            for env in container.get('env', []):
                if 'configMapKeyRef' in env.get('valueFrom', {}):
                    assert env['valueFrom']['configMapKeyRef']['name'] in configmaps
    api=next(d for d in deployments if d['metadata']['name']=='compreface-api')
    pod=api['spec']['template']['spec']
    assert not pod.get('volumes')
    container=pod['containers'][0]
    env={v['name']:v for v in container['env']}
    assert env['EXTERNAL_DB']['value']=='true'
    assert env['POSTGRES_URL']['value'].startswith('jdbc:postgresql://')
    assert 'POSTGRES_USER' in env and 'POSTGRES_PASSWORD' in env
    assert '"OK"' in ' '.join(container['readinessProbe']['exec']['command'])
    assert container['startupProbe']['failureThreshold']*container['startupProbe']['periodSeconds']>=300


def test_monitoring_targets_and_health_semantics():
    services=load('docker-compose/docker-compose.yml')['services']
    prometheus=load('monitoring/prometheus/prometheus.yml')
    for scrape in prometheus['scrape_configs']:
        for static in scrape.get('static_configs', []):
            for target in static['targets']:
                host=target.removeprefix('http://').split(':')[0]
                assert host=='localhost' or host in services, target
    rules=load('monitoring/prometheus/alert_rules.yml')
    expressions=' '.join(r['expr'] for g in rules['groups'] for r in g['rules'])
    assert 'probe_success' in expressions and 'pg_up' in expressions
    assert 'http_requests_total' not in expressions and 'node_' not in expressions
    health=load('monitoring/blackbox/blackbox.yml')['modules']['compreface_health']['http']
    regex=health['fail_if_body_not_matches_regexp'][0]
    assert re.search(regex,'{"status": "OK"}')
    for body in ['<html>SPA</html>','{"status":"DOWN"}','{"status":"UP"}']:
        assert not re.search(regex,body)
    assert health['fail_if_header_not_matches']
    datasource=load('monitoring/grafana/provisioning/datasources/prometheus.yml')['datasources'][0]
    dashboard=json.loads((ROOT/'monitoring/grafana/dashboard.json').read_text(encoding='utf-8'))
    assert all(panel['datasource']['uid']==datasource['uid'] for panel in dashboard['panels'])


def test_load_plan_uses_correct_keys_and_multipart_fields():
    plan=ET.parse(ROOT/'tests/performance/jmeter/compreface_load_test.jmx')
    samplers=plan.findall('.//HTTPSamplerProxy')
    assert len(samplers)==2
    paths=[s.find("stringProp[@name='HTTPSampler.path']").text for s in samplers]
    assert paths==['${api_url}/api/v1/detection/detect','${api_url}/api/v1/verification/verify']
    fields=[p.text for p in samplers[1].findall(".//stringProp[@name='File.paramname']")]
    assert fields==['source_image','target_image']
    headers=[p.text for p in plan.findall(".//stringProp[@name='Header.value']")]
    assert headers==['${detection_api_key}','${verification_api_key}']
