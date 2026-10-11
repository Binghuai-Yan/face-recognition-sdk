"""Verify the provider contract with botocore's request validator, without a server."""
from dataclasses import replace
import io
from pathlib import Path
import sys

from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from botocore.stub import Stubber
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oss_gateway.config import Settings
from oss_gateway.store import S3Store


def settings():
    return Settings(endpoint='https://objects.example.test',access_key='example-id',
                    secret_key='example-secret',region='eu-west-1',addressing_style='virtual')


def test_standard_s3_operations_preserve_bytes_and_do_not_request_public_acl():
    store=S3Store(settings())
    assert store.client.meta.endpoint_url=='https://objects.example.test'
    assert store.client.meta.config.signature_version=='s3v4'
    assert store.client.meta.config.s3['addressing_style']=='virtual'
    data=b'original image bytes'
    body=StreamingBody(io.BytesIO(data),len(data))
    with Stubber(store.client) as stub:
        stub.add_response('head_bucket',{}, {'Bucket':store.bucket})
        stub.add_response('put_object',{}, {'Bucket':store.bucket,'Key':'faces/key','Body':data,'ContentType':'image/jpeg'})
        stub.add_response('get_object',{'Body':body,'ContentType':'image/jpeg'}, {'Bucket':store.bucket,'Key':'faces/key'})
        stub.add_response('delete_object',{}, {'Bucket':store.bucket,'Key':'faces/key'})
        store.initialize()
        store.put('faces/key',data,'image/jpeg')
        assert store.get('faces/key')==(data,'image/jpeg')
        assert body._raw_stream.closed
        store.delete('faces/key')
        stub.assert_no_pending_responses()


@pytest.mark.parametrize('region',['us-east-1','eu-west-1'])
def test_bucket_creation_respects_region(region):
    store=S3Store(replace(settings(),region=region))
    params={'Bucket':store.bucket}
    if region!='us-east-1':
        params['CreateBucketConfiguration']={'LocationConstraint':region}
    with Stubber(store.client) as stub:
        stub.add_client_error('head_bucket','NoSuchBucket',http_status_code=404,expected_params={'Bucket':store.bucket})
        stub.add_response('create_bucket',{},params)
        stub.add_response('head_bucket',{}, {'Bucket':store.bucket})
        store.initialize()
        stub.assert_no_pending_responses()


@pytest.mark.parametrize('status,auto_create',[(403,True),(404,False)])
def test_permission_failure_or_disabled_creation_does_not_create_a_bucket(status,auto_create):
    store=S3Store(replace(settings(),auto_create_bucket=auto_create))
    with Stubber(store.client) as stub:
        stub.add_client_error('head_bucket','AccessDenied',http_status_code=status,expected_params={'Bucket':store.bucket})
        with pytest.raises(ClientError):
            store.initialize()
        stub.assert_no_pending_responses()
