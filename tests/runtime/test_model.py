"""Extra real-model edge cases; failures are never converted to skips."""
import base64
import hashlib
import io
import os
from pathlib import Path
import sys
import uuid

from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'sdk/python'))
from facesdk import FaceSDKClient
from facesdk.exceptions import FaceSDKException

pytestmark = pytest.mark.skipif(os.getenv('FACESDK_LIVE') != '1', reason='Requires explicitly enabled real service')


@pytest.fixture
def client():
    keys = {s:os.environ['FACESDK_'+s.upper()+'_API_KEY'] for s in ['detection','recognition','verification']}
    with FaceSDKClient(os.environ['FACESDK_API_URL'], api_keys=keys, timeout=120, max_retries=0) as value:
        yield value


def test_real_multiface_ambiguity(client):
    face = Image.open(os.environ['FACESDK_TEST_IMAGE']).convert('RGB')
    # Use two complete copies, preserving each face and providing a visible gap.
    image = Image.new('RGB', (face.width*2+100, face.height), 'white')
    image.paste(face, (0,0)); image.paste(face, (face.width+100,0))
    data = io.BytesIO(); image.save(data, format='JPEG')
    assert client.detect(data.getvalue()).face_count == 2
    with pytest.raises(FaceSDKException):
        client.extract_feature(data.getvalue())
    with pytest.raises(FaceSDKException):
        client.compare(Path(os.environ['FACESDK_TEST_IMAGE']).read_bytes(), data.getvalue())


def test_real_feature_matches_reference(client):
    value = base64.b64decode(client.extract_feature(Path(os.environ['FACESDK_TEST_IMAGE']).read_bytes()), validate=True)
    assert value and len(value)%4 == 0
    if os.getenv('FACESDK_FEATURE_SHA256'):
        assert hashlib.sha256(value).hexdigest() == os.environ['FACESDK_FEATURE_SHA256']


def test_real_invalid_image_is_rejected(client):
    with pytest.raises(FaceSDKException):
        client.detect(b'this is not an image')


def test_real_unicode_subject_lifecycle(client):
    subject = '张三 &? '+uuid.uuid4().hex
    cleanup = False
    try:
        assert client.create_subject(subject).subject_id == subject
        cleanup = True
        assert subject in [s.subject_id for s in client.list_subjects()]
        record = client.add_face(subject, Path(os.environ['FACESDK_TEST_IMAGE']).read_bytes())
        assert record.subject_id == subject
        matches = client.search(Path(os.environ['FACESDK_TEST_IMAGE']).read_bytes(), limit=100)
        assert any(m.subject_id == subject for m in matches.results)
        client.delete_subject(subject)
        cleanup = False
        assert subject not in [s.subject_id for s in client.list_subjects()]
    finally:
        if cleanup:
            client.delete_subject(subject)
