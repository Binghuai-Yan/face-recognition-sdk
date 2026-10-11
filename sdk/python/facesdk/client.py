#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: facesdk/sdk/python/facesdk/client.py
Copyright (c) 2024 FaceSDK Contributors
MIT License

FaceSDK Python SDK - Synchronous Client
"""

import logging
import mimetypes
import time
from typing import Dict, Any, List, Optional, Union, BinaryIO
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ._common import service_for, retryable, validate_search, encode_embedding, path_segment, result_array

from .exceptions import (
    FaceSDKException,
    NoFaceException,
    ApiException,
    AuthenticationException,
    RateLimitException,
    ServerException,
    ValidationException,
)
from .models import (
    DetectionResult,
    CompareResult,
    SearchResult,
    Subject,
    FaceRecord,
)

logger = logging.getLogger(__name__)


class FaceSDKClient:
    """FaceSDK 同步客户端"""

    def __init__(
        self,
        api_url: str,
        api_key: str = "",
        timeout: int = 30,
        connect_timeout: int = 5,
        max_retries: int = 3,
        retry_delay: float = 0.5,
        verify_ssl: bool = True,
        api_keys: Optional[Dict[str, str]] = None,
        comparison_threshold: float = 0.8,
    ):
        """
        初始化 FaceSDK 客户端

        Args:
            api_url: API 基础 URL
            api_key: API 密钥
            timeout: 读取超时时间（秒）
            connect_timeout: 连接超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            verify_ssl: 是否验证 SSL 证书
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.verify_ssl = verify_ssl
        self.api_keys = dict(api_keys or {})
        self.comparison_threshold = comparison_threshold
        if not isinstance(max_retries, int) or isinstance(max_retries, bool) or max_retries < 0 or retry_delay < 0 or not 0 <= comparison_threshold <= 1:
            raise ValueError("Invalid retry configuration or comparison threshold")

        # 创建会话
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})

        # 配置超时
        self._timeout = (connect_timeout, timeout)

        # 配置重试策略
        retry_strategy = Retry(
            total=0,
            backoff_factor=retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"FaceSDKClient initialized with API URL: {api_url}")

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        url = f"{self.api_url}{endpoint}"
        kwargs.setdefault("timeout", self._timeout)
        kwargs.setdefault("verify", self.verify_ssl)

        headers = dict(kwargs.pop("headers", {}))
        key = self.api_keys.get(service_for(endpoint), self.api_key)
        if not key:
            raise AuthenticationException("Missing API key for " + service_for(endpoint))
        headers["x-api-key"] = key
        attempts = self.max_retries if retryable(method, endpoint) else 0
        for attempt in range(attempts + 1):
            try:
                response = self.session.request(method, url, headers=headers, **kwargs)
                try:
                    if response.status_code in (429, 500, 502, 503, 504) and attempt < attempts:
                        time.sleep(self.retry_delay * 2 ** attempt)
                        continue
                    return self._handle_response(response)
                finally:
                    response.close()
            except requests.exceptions.RequestException as e:
                if attempt == attempts:
                    raise ApiException("Request failed: " + str(e)) from e
                time.sleep(self.retry_delay * 2 ** attempt)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """处理 HTTP 响应"""
        try:
            data = response.json() if response.content else {}
        except ValueError as e:
            if 200 <= response.status_code < 300:
                raise ApiException("API returned invalid JSON", "INVALID_RESPONSE") from e
            data = {}

        if 200 <= response.status_code < 300:
            if not isinstance(data, dict):
                raise ApiException("API returned invalid JSON object", "INVALID_RESPONSE")
            return data

        # 处理错误
        message = str(data.get("message") or data.get("error") or "Unknown error") if isinstance(data, dict) else "Unknown error"

        if response.status_code == 400:
            if "no face" in message.lower():
                raise NoFaceException(message)
            raise ApiException(message, "VALIDATION_ERROR", 400)
        elif response.status_code == 401:
            raise AuthenticationException(message)
        elif response.status_code == 429:
            raise RateLimitException(message)
        elif response.status_code >= 500:
            raise ServerException(message)
        else:
            raise ApiException(message, f"HTTP_{response.status_code}", response.status_code)

    def _prepare_file(
        self,
        file: Union[str, Path, bytes, BinaryIO],
        field_name: str = "file",
    ) -> Dict[str, Any]:
        """准备文件上传"""
        if isinstance(file, (str, Path)):
            file_path = Path(file)
            return {
                field_name: (
                    file_path.name,
                    file_path.read_bytes(),
                    mimetypes.guess_type(file_path.name)[0] or "application/octet-stream",
                )
            }
        elif isinstance(file, bytes):
            return {field_name: ("image.jpg", file, "image/jpeg")}
        elif hasattr(file, "read"):
            return {field_name: ("image.jpg", file.read(), "image/jpeg")}
        else:
            raise ValueError(f"Unsupported file type: {type(file)}")

    # ==================== 人脸检测 ====================

    def detect(
        self,
        image: Union[str, Path, bytes, BinaryIO],
        **options,
    ) -> DetectionResult:
        """
        检测图片中的人脸

        Args:
            image: 图片路径、字节数据或文件对象
            **options: 可选参数

        Returns:
            DetectionResult: 检测结果
        """
        logger.debug(f"Detecting faces in image")

        files = self._prepare_file(image)
        data = {k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in options.items()}

        result = self._request(
            "POST",
            "/api/v1/detection/detect",
            files=files,
            params=data,
        )
        return DetectionResult.from_dict(result)

    # ==================== 人脸比对 ====================

    def compare(
        self,
        image1: Union[str, Path, bytes, BinaryIO],
        image2: Union[str, Path, bytes, BinaryIO],
    ) -> CompareResult:
        """
        比对两张人脸图片

        Args:
            image1: 第一张图片
            image2: 第二张图片

        Returns:
            CompareResult: 比对结果
        """
        logger.debug("Comparing two images")

        files = {}
        files.update(self._prepare_file(image1, "source_image"))
        files.update(self._prepare_file(image2, "target_image"))

        result = self._request(
            "POST",
            "/api/v1/verification/verify",
            files=files,
        )
        return CompareResult.from_dict(result, self.comparison_threshold)

    # ==================== 人脸识别（1:N） ====================

    def search(
        self,
        image: Union[str, Path, bytes, BinaryIO],
        limit: int = 1,
        threshold: Optional[float] = None,
    ) -> SearchResult:
        """
        在人脸库中搜索相似人脸

        Args:
            image: 待搜索图片
            limit: 返回结果数量
            threshold: 相似度阈值

        Returns:
            SearchResult: 搜索结果
        """
        logger.debug(f"Searching faces with limit={limit}")
        validate_search(limit, threshold)

        files = self._prepare_file(image)
        data = {"prediction_count": str(limit)}

        result = self._request(
            "POST",
            "/api/v1/recognition/recognize",
            files=files,
            params=data,
        )
        return SearchResult.from_dict(result, threshold)

    # ==================== 特征提取 ====================

    def extract_feature(
        self,
        image: Union[str, Path, bytes, BinaryIO],
    ) -> str:
        """
        提取人脸特征向量

        Args:
            image: 图片路径、字节数据或文件对象

        Returns:
            str: Base64 编码的特征向量
        """
        logger.debug("Extracting face feature")

        files = self._prepare_file(image)

        result = self._request(
            "POST",
            "/api/v1/detection/detect",
            files=files,
            params={"face_plugins": "calculator"},
        )
        return encode_embedding(result)

    # ==================== 人脸库管理 ====================

    def create_subject(self, subject_id: str, name: str = "") -> Subject:
        """
        创建人脸库

        Args:
            subject_id: 人脸库 ID
            name: 人脸库名称

        Returns:
            Subject: 创建的人脸库
        """
        logger.debug(f"Creating subject: {subject_id}")

        result = self._request(
            "POST",
            "/api/v1/recognition/subjects",
            json={"subject": subject_id},
        )
        return Subject.from_dict(result)

    def delete_subject(self, subject_id: str) -> None:
        """
        删除人脸库

        Args:
            subject_id: 人脸库 ID
        """
        logger.debug(f"Deleting subject: {subject_id}")
        self._request("DELETE", f"/api/v1/recognition/subjects/{path_segment(subject_id)}")

    def list_subjects(self) -> List[Subject]:
        """
        列出所有人脸库

        Returns:
            List[Subject]: 人脸库列表
        """
        logger.debug("Listing all subjects")
        result = self._request("GET", "/api/v1/recognition/subjects")
        return [Subject.from_dict(s) for s in result_array(result, key="subjects")]

    # ==================== 人脸管理 ====================

    def add_face(
        self,
        subject_id: str,
        image: Union[str, Path, bytes, BinaryIO],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FaceRecord:
        """
        添加人脸到人脸库

        Args:
            subject_id: 人脸库 ID
            image: 人脸图片
            metadata: 元数据

        Returns:
            FaceRecord: 人脸记录
        """
        logger.debug(f"Adding face to subject: {subject_id}")
        if metadata:
            raise ValidationException("CompreFace 1.2 does not persist metadata; store it in your application")

        files = self._prepare_file(image)
        result = self._request(
            "POST",
            f"/api/v1/recognition/faces",
            params={"subject": subject_id},
            files=files,
        )
        return FaceRecord.from_dict(result)

    def delete_face(self, face_id: str) -> None:
        """
        删除人脸

        Args:
            face_id: 人脸 ID
        """
        logger.debug(f"Deleting face: {face_id}")
        self._request("DELETE", f"/api/v1/recognition/faces/{path_segment(face_id)}")

    def close(self):
        """关闭客户端"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
