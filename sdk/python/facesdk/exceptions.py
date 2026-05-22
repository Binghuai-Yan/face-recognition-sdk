#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: facesdk/sdk/python/facesdk/exceptions.py
Copyright (c) 2024 FaceSDK Contributors
MIT License

FaceSDK Python SDK - Exceptions
"""

from typing import Optional


class FaceSDKException(Exception):
    """FaceSDK 通用异常类"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        http_status_code: Optional[int] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.http_status_code = http_status_code

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class NoFaceException(FaceSDKException):
    """未检测到人脸异常"""

    def __init__(self, message: str = "No face detected in the image"):
        super().__init__(message, "NO_FACE_DETECTED", 400)


class ApiException(FaceSDKException):
    """API 调用异常"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        http_status_code: Optional[int] = None,
    ):
        super().__init__(message, error_code or "API_ERROR", http_status_code)


class ValidationException(FaceSDKException):
    """参数验证异常"""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR", 400)


class AuthenticationException(FaceSDKException):
    """认证异常"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_ERROR", 401)


class RateLimitException(FaceSDKException):
    """速率限制异常"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "RATE_LIMIT_ERROR", 429)


class ServerException(FaceSDKException):
    """服务器内部错误"""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, "SERVER_ERROR", 500)
