"""Shared CompreFace protocol helpers."""

import base64
import struct
from urllib.parse import quote

from .exceptions import ApiException, ValidationException, NoFaceException


def result_array(data, key="result", legacy=None):
    value = data.get(key, data.get(legacy) if legacy else None)
    if not isinstance(value, list):
        raise ApiException("Missing or invalid " + key + " array", "INVALID_RESPONSE")
    return value


def service_for(endpoint):
    return endpoint.split("/")[3]


def retryable(method, endpoint):
    return method in ("GET", "HEAD", "DELETE") or endpoint in (
        "/api/v1/detection/detect", "/api/v1/verification/verify",
        "/api/v1/recognition/recognize",
    )


def validate_search(limit, threshold):
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValidationException("limit must be a positive integer")
    if threshold is not None and not 0 <= threshold <= 1:
        raise ValidationException("threshold must be between 0 and 1")


def encode_embedding(response):
    faces = result_array(response)
    if not faces:
        raise NoFaceException()
    if len(faces) != 1:
        raise ValidationException("Feature extraction requires exactly one face")
    embedding = faces[0].get("embedding")
    if not embedding:
        raise ApiException("The calculator plugin did not return an embedding", "NO_EMBEDDING")
    # All SDKs use IEEE 754 float32, little endian, then standard Base64.
    return base64.b64encode(struct.pack("<%sf" % len(embedding), *embedding)).decode("ascii")


def path_segment(value):
    if not value or value in (".", ".."):
        raise ValidationException("Identifier must not be empty or a dot segment")
    return quote(value, safe="")
