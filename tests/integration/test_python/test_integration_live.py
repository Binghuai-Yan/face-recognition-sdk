"""Opt-in tests against a real CompreFace model and persistent collection.

No downloads, fake images or swallowed failures. See tests/README.md.
"""
import base64
import io
import os
import struct
import sys
import uuid
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'sdk/python'))
from facesdk import FaceSDKClient, AsyncFaceSDKClient
from facesdk.exceptions import NoFaceException, ApiException

pytestmark = pytest.mark.skipif(os.getenv('FACESDK_LIVE') != '1', reason='Real CompreFace tests require FACESDK_LIVE=1, three service keys and a real single-face image')


def config():
    required = ['FACESDK_API_URL', 'FACESDK_DETECTION_API_KEY', 'FACESDK_RECOGNITION_API_KEY', 'FACESDK_VERIFICATION_API_KEY', 'FACESDK_TEST_IMAGE']
    missing = [key for key in required if not os.getenv(key)]
    assert not missing, 'Live test configuration missing: ' + ', '.join(missing)
    image = Path(os.environ['FACESDK_TEST_IMAGE']).read_bytes()
    with Image.open(io.BytesIO(image)) as decoded:
        decoded.verify()
    return os.environ['FACESDK_API_URL'], {service: os.environ[f'FACESDK_{service.upper()}_API_KEY'] for service in ['detection', 'recognition', 'verification']}, image


@pytest.mark.parametrize('asynchronous', [False, True])
@pytest.mark.asyncio
async def test_real_lifecycle(asynchronous):
    url, keys, image = config()
    client = (AsyncFaceSDKClient if asynchronous else FaceSDKClient)(url, api_keys=keys, timeout=120, max_retries=0)
    subject = 'facesdk-test-' + uuid.uuid4().hex
    cleanup = False
    async def call(method, *args, **kwargs):
        result = getattr(client, method)(*args, **kwargs)
        return await result if asynchronous else result
    try:
        assert (await call('detect', image)).face_count == 1
        assert (await call('create_subject', subject)).subject_id == subject
        cleanup = True
        assert subject in [s.subject_id for s in await call('list_subjects')]
        record = await call('add_face', subject, image)
        assert record.image_id and record.subject_id == subject
        search = await call('search', image, limit=100, threshold=0.8)
        assert search.face_count == 1
        assert any(match.subject_id == subject and match.match for match in search.results)
        comparison = await call('compare', image, image)
        assert comparison.match and 0.8 <= comparison.similarity <= 1
        feature = base64.b64decode(await call('extract_feature', image), validate=True)
        assert len(feature) > 0 and len(feature) % 4 == 0
        assert all(abs(value) < float('inf') for value in struct.unpack('<%sf' % (len(feature) // 4), feature))
        await call('delete_face', record.image_id)
        if subject not in [s.subject_id for s in await call('list_subjects')]:
            await call('create_subject', subject)
        await call('delete_subject', subject)
        cleanup = False
        assert subject not in [s.subject_id for s in await call('list_subjects')]
    finally:
        try:
            if cleanup:
                await call('delete_subject', subject)
        finally:
            if asynchronous:
                await client.close()
            else:
                client.close()


@pytest.mark.parametrize('asynchronous', [False, True])
@pytest.mark.asyncio
async def test_real_blank_image_and_authentication(asynchronous):
    url, keys, _ = config()
    buffer = io.BytesIO()
    Image.new('RGB', (640, 480), 'white').save(buffer, format='PNG')
    cls = AsyncFaceSDKClient if asynchronous else FaceSDKClient
    client = cls(url, api_keys=keys, max_retries=0)
    try:
        with pytest.raises(NoFaceException):
            if asynchronous:
                await client.detect(buffer.getvalue())
            else:
                client.detect(buffer.getvalue())
        client.api_keys['detection'] = str(uuid.uuid4())
        # CompreFace 1.2 reports an unknown service key as HTTP 404.
        with pytest.raises(ApiException) as invalid_key:
            if asynchronous:
                await client.detect(buffer.getvalue())
            else:
                client.detect(buffer.getvalue())
        assert invalid_key.value.http_status_code == 404
        assert invalid_key.value.error_code == 'HTTP_404'
    finally:
        if asynchronous:
            await client.close()
        else:
            client.close()


@pytest.mark.parametrize('asynchronous', [False, True])
@pytest.mark.parametrize('input_kind', ['png-path', 'jpeg-stream'])
@pytest.mark.asyncio
async def test_real_image_formats_and_inputs(asynchronous, input_kind, tmp_path):
    url, keys, image = config()
    if input_kind == 'png-path':
        value = tmp_path/'face.png'
        with Image.open(io.BytesIO(image)) as decoded:
            decoded.save(value, format='PNG')
    else:
        value = io.BytesIO(image)
    client = (AsyncFaceSDKClient if asynchronous else FaceSDKClient)(url, api_keys=keys, timeout=120, max_retries=0)
    try:
        result = await client.detect(value) if asynchronous else client.detect(value)
        assert result.face_count == 1
    finally:
        if asynchronous:
            await client.close()
        else:
            client.close()
        if hasattr(value, 'close'):
            value.close()
