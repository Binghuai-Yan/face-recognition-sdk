#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: facesdk/sdk/python/facesdk/__init__.py
Copyright (c) 2024 FaceSDK Contributors
MIT License

FaceSDK Python SDK - Package Initialization
"""

__version__ = "1.0.0"
__author__ = "FaceSDK Team"
__email__ = "team@facesdk.io"

from .client import FaceSDKClient
from .async_client import AsyncFaceSDKClient
from .exceptions import (
    FaceSDKException,
    NoFaceException,
    ApiException,
    ValidationException,
    AuthenticationException,
    RateLimitException,
)
from .models import (
    Face,
    BoundingBox,
    Quality,
    Subject,
    FaceRecord,
    DetectionResult,
    CompareResult,
    SearchResult,
    MatchResult,
)

__all__ = [
    "FaceSDKClient",
    "AsyncFaceSDKClient",
    "FaceSDKException",
    "NoFaceException",
    "ApiException",
    "ValidationException",
    "AuthenticationException",
    "RateLimitException",
    "Face",
    "BoundingBox",
    "Quality",
    "Subject",
    "FaceRecord",
    "DetectionResult",
    "CompareResult",
    "SearchResult",
    "MatchResult",
]
