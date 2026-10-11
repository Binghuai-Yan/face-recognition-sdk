from dataclasses import dataclass, field
import os
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    upstream: str = 'http://compreface-api:80'
    endpoint: str = 'http://rustfs:9000'
    bucket: str = 'facesdk-images'
    region: str = 'us-east-1'
    access_key: str = field(default='', repr=False)
    secret_key: str = field(default='', repr=False)
    session_token: str = field(default='', repr=False)
    addressing_style: str = 'path'
    ca_bundle: str = ''
    auto_create_bucket: bool = True
    prefix: str = 'faces'
    database: str = '/data/storage.sqlite3'
    max_body_bytes: int = 10 * 1024 * 1024
    poll_seconds: float = 5

    @classmethod
    def from_env(cls):
        if os.getenv('OSS_PROVIDER', 's3') != 's3':
            raise ValueError('OSS_PROVIDER must be s3 (S3-compatible object storage)')
        return cls(
            upstream=os.getenv('COMPREFACE_UPSTREAM', cls.upstream).rstrip('/'),
            endpoint=os.getenv('OSS_ENDPOINT', cls.endpoint).rstrip('/'),
            bucket=os.getenv('OSS_BUCKET', cls.bucket), region=os.getenv('OSS_REGION', cls.region),
            access_key=os.getenv('OSS_ACCESS_KEY_ID', ''), secret_key=os.getenv('OSS_SECRET_ACCESS_KEY', ''),
            session_token=os.getenv('OSS_SESSION_TOKEN', ''),
            addressing_style=os.getenv('OSS_ADDRESSING_STYLE', 'path'),
            ca_bundle=os.getenv('OSS_CA_BUNDLE', ''),
            auto_create_bucket=os.getenv('OSS_AUTO_CREATE_BUCKET', 'true').lower() == 'true',
            prefix=os.getenv('OSS_PREFIX', 'faces').strip('/'),
            database=os.getenv('OSS_JOURNAL_PATH', cls.database),
            max_body_bytes=int(os.getenv('OSS_MAX_BODY_BYTES', str(cls.max_body_bytes))),
            poll_seconds=float(os.getenv('OSS_POLL_SECONDS', '5')),
        )

    def validate(self):
        for name, value in [('COMPREFACE_UPSTREAM', self.upstream), ('OSS_ENDPOINT', self.endpoint)]:
            url = urlsplit(value)
            if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError(name+' must be an HTTP(S) URL without embedded credentials or query')
        if self.addressing_style not in ('path', 'virtual', 'auto'):
            raise ValueError('Invalid OSS_ADDRESSING_STYLE')
        if not self.bucket or not self.prefix or not self.access_key or not self.secret_key:
            raise ValueError('Configure OSS bucket, prefix and credentials')
        if self.max_body_bytes < 1 or self.poll_seconds <= 0:
            raise ValueError('Invalid gateway limits')
