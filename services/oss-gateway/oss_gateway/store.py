"""Object storage contract. Credentials and provider SDKs remain server-side."""
from typing import Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .config import Settings


class ObjectStore(Protocol):
    def initialize(self) -> None: ...
    def check(self) -> None: ...
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> tuple[bytes, str]: ...
    def delete(self, key: str) -> None: ...


class S3Store:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.bucket = settings.bucket
        self.client = boto3.client(
            's3', endpoint_url=settings.endpoint, region_name=settings.region,
            aws_access_key_id=settings.access_key, aws_secret_access_key=settings.secret_key,
            aws_session_token=settings.session_token or None, verify=settings.ca_bundle or True,
            config=Config(signature_version='s3v4', s3={'addressing_style':settings.addressing_style},
                          connect_timeout=5, read_timeout=20, retries={'mode':'standard','total_max_attempts':2},
                          request_checksum_calculation='when_required', response_checksum_validation='when_required'),
        )

    def check(self):
        self.client.head_bucket(Bucket=self.bucket)

    def initialize(self):
        try:
            self.check()
        except ClientError as error:
            status = error.response['ResponseMetadata']['HTTPStatusCode']
            if status != 404 or not self.settings.auto_create_bucket:
                raise
            params = {'Bucket':self.bucket}
            if self.settings.region != 'us-east-1':
                params['CreateBucketConfiguration'] = {'LocationConstraint':self.settings.region}
            try:
                self.client.create_bucket(**params)
            except ClientError as raced:
                if raced.response['Error']['Code'] != 'BucketAlreadyOwnedByYou':
                    raise
            self.check()

    def put(self, key, data, content_type):
        # No public ACL, no public URL, no provider-specific operations.
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key):
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        try:
            return response['Body'].read(), response.get('ContentType', 'application/octet-stream')
        finally:
            response['Body'].close()

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=key)
