#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: facesdk/sdk/python/facesdk/async_client.py
Copyright (c) 2024 FaceSDK Contributors
MIT License

FaceSDK Python SDK - Asynchronous Client
"""

import logging
import asyncio
import mimetypes
from typing import Dict, Any, List, Optional, Union, BinaryIO
from pathlib import Path

import aiohttp
import aiofiles
from ._common import service_for, retryable, validate_search, encode_embedding, path_segment, result_array

from .exceptions import (
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


class AsyncFaceSDKClient:
    """FaceSDK 异步客户端"""

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
        初始化 FaceSDK 异步客户端

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
        self.timeout = aiohttp.ClientTimeout(total=timeout, connect=connect_timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.verify_ssl = verify_ssl
        self.api_keys = dict(api_keys or {})
        self.comparison_threshold = comparison_threshold
        if not isinstance(max_retries, int) or isinstance(max_retries, bool) or max_retries < 0 or retry_delay < 0 or not 0 <= comparison_threshold <= 1:
            raise ValueError("Invalid retry configuration or comparison threshold")
        self._session: Optional[aiohttp.ClientSession] = None

        logger.info(f"AsyncFaceSDKClient initialized with API URL: {api_url}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp 会话"""
        if self._session is None or self._session.closed:
            headers = {"x-api-key": self.api_key}
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=self.timeout,
            )
        return self._session

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """发送异步 HTTP 请求"""
        url = f"{self.api_url}{endpoint}"

        session = await self._get_session()
        factory = kwargs.pop("data_factory", None)
        headers = dict(kwargs.pop("headers", {}))
        key = self.api_keys.get(service_for(endpoint), self.api_key)
        if not key:
            raise AuthenticationException("Missing API key for " + service_for(endpoint))
        headers["x-api-key"] = key
        attempts = self.max_retries if retryable(method, endpoint) else 0
        for attempt in range(attempts + 1):
            try:
                if factory:
                    kwargs["data"] = factory()
                async with session.request(
                    method, url, ssl=self.verify_ssl, headers=headers, **kwargs
                ) as response:
                    if response.status in (429, 500, 502, 503, 504) and attempt < attempts:
                        await response.read()
                        await asyncio.sleep(self.retry_delay * 2 ** attempt)
                        continue
                    return await self._handle_response(response)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < attempts:
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying...")
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise ApiException(f"Request failed after {attempts + 1} attempts: {str(e)}") from e

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """处理 HTTP 响应"""
        try:
            content = await response.read()
            data = await response.json() if content else {}
        except (ValueError, aiohttp.ContentTypeError) as e:
            if 200 <= response.status < 300:
                raise ApiException("API returned invalid JSON", "INVALID_RESPONSE") from e
            data = {}

        if 200 <= response.status < 300:
            if not isinstance(data, dict):
                raise ApiException("API returned invalid JSON object", "INVALID_RESPONSE")
            return data

        # 处理错误
        message = str(data.get("message") or data.get("error") or "Unknown error") if isinstance(data, dict) else "Unknown error"

        if response.status == 400:
            if "no face" in message.lower():
                raise NoFaceException(message)
            raise ApiException(message, "VALIDATION_ERROR", 400)
        elif response.status == 401:
            raise AuthenticationException(message)
        elif response.status == 429:
            raise RateLimitException(message)
        elif response.status >= 500:
            raise ServerException(message)
        else:
            raise ApiException(message, f"HTTP_{response.status}", response.status)

    async def _read_file(
        self,
        file: Union[str, Path, bytes, BinaryIO],
    ) -> bytes:
        """读取文件内容"""
        if isinstance(file, (str, Path)):
            async with aiofiles.open(file, "rb") as f:
                return await f.read()
        elif isinstance(file, bytes):
            return file
        elif hasattr(file, "read"):
            return file.read()
        else:
            raise ValueError(f"Unsupported file type: {type(file)}")

    # ==================== 人脸检测 ====================

    async def detect(
        self,
        image: Union[str, Path, bytes, BinaryIO],
        **options,
    ) -> DetectionResult:
        """
        异步检测图片中的人脸

        Args:
            image: 图片路径、字节数据或文件对象
            **options: 可选参数

        Returns:
            DetectionResult: 检测结果
        """
        logger.debug("Detecting faces in image (async)")

        image_data = await self._read_file(image)
        filename = "image.jpg"
        if isinstance(image, (str, Path)):
            filename = Path(image).name

        result = await self._request(
            "POST",
            "/api/v1/detection/detect",
            data_factory=lambda: self._form([("file", image_data, filename)]),
            params={k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in options.items()},
        )
        return DetectionResult.from_dict(result)

    # ==================== 人脸比对 ====================

    async def compare(
        self,
        image1: Union[str, Path, bytes, BinaryIO],
        image2: Union[str, Path, bytes, BinaryIO],
    ) -> CompareResult:
        """
        异步比对两张人脸图片

        Args:
            image1: 第一张图片
            image2: 第二张图片

        Returns:
            CompareResult: 比对结果
        """
        logger.debug("Comparing two images (async)")

        image1_data = await self._read_file(image1)
        image2_data = await self._read_file(image2)

        result = await self._request(
            "POST",
            "/api/v1/verification/verify",
            data_factory=lambda: self._form([("source_image", image1_data, "image1.jpg"),
                                            ("target_image", image2_data, "image2.jpg")]),
        )
        return CompareResult.from_dict(result, self.comparison_threshold)

    # ==================== 人脸识别（1:N） ====================

    async def search(
        self,
        image: Union[str, Path, bytes, BinaryIO],
        limit: int = 1,
        threshold: Optional[float] = None,
    ) -> SearchResult:
        """
        异步在人脸库中搜索相似人脸

        Args:
            image: 待搜索图片
            limit: 返回结果数量
            threshold: 相似度阈值

        Returns:
            SearchResult: 搜索结果
        """
        logger.debug(f"Searching faces with limit={limit} (async)")
        validate_search(limit, threshold)

        image_data = await self._read_file(image)

        result = await self._request(
            "POST",
            "/api/v1/recognition/recognize",
            data_factory=lambda: self._form([("file", image_data, "image.jpg")]),
            params={"prediction_count": str(limit)},
        )
        return SearchResult.from_dict(result, threshold)

    # ==================== 特征提取 ====================

    async def extract_feature(
        self,
        image: Union[str, Path, bytes, BinaryIO],
    ) -> str:
        """
        异步提取人脸特征向量

        Args:
            image: 图片路径、字节数据或文件对象

        Returns:
            str: Base64 编码的特征向量
        """
        logger.debug("Extracting face feature (async)")

        image_data = await self._read_file(image)

        result = await self._request(
            "POST",
            "/api/v1/detection/detect",
            data_factory=lambda: self._form([("file", image_data, "image.jpg")]),
            params={"face_plugins": "calculator"},
        )
        return encode_embedding(result)

    # ==================== 人脸库管理 ====================

    async def create_subject(self, subject_id: str, name: str = "") -> Subject:
        """
        异步创建人脸库

        Args:
            subject_id: 人脸库 ID
            name: 人脸库名称

        Returns:
            Subject: 创建的人脸库
        """
        logger.debug(f"Creating subject: {subject_id} (async)")

        result = await self._request(
            "POST",
            "/api/v1/recognition/subjects",
            json={"subject": subject_id},
        )
        return Subject.from_dict(result)

    async def delete_subject(self, subject_id: str) -> None:
        """
        异步删除人脸库

        Args:
            subject_id: 人脸库 ID
        """
        logger.debug(f"Deleting subject: {subject_id} (async)")
        await self._request("DELETE", f"/api/v1/recognition/subjects/{path_segment(subject_id)}")

    async def list_subjects(self) -> List[Subject]:
        """
        异步列出所有人脸库

        Returns:
            List[Subject]: 人脸库列表
        """
        logger.debug("Listing all subjects (async)")
        result = await self._request("GET", "/api/v1/recognition/subjects")
        return [Subject.from_dict(s) for s in result_array(result, key="subjects")]

    # ==================== 人脸管理 ====================

    async def add_face(
        self,
        subject_id: str,
        image: Union[str, Path, bytes, BinaryIO],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FaceRecord:
        """
        异步添加人脸到人脸库

        Args:
            subject_id: 人脸库 ID
            image: 人脸图片
            metadata: 元数据

        Returns:
            FaceRecord: 人脸记录
        """
        logger.debug(f"Adding face to subject: {subject_id} (async)")
        if metadata:
            raise ValidationException("CompreFace 1.2 does not persist metadata; store it in your application")

        image_data = await self._read_file(image)

        result = await self._request(
            "POST",
            "/api/v1/recognition/faces",
            params={"subject": subject_id},
            data_factory=lambda: self._form([("file", image_data, "image.jpg")]),
        )
        return FaceRecord.from_dict(result)

    async def delete_face(self, face_id: str) -> None:
        """
        异步删除人脸

        Args:
            face_id: 人脸 ID
        """
        logger.debug(f"Deleting face: {face_id} (async)")
        await self._request("DELETE", f"/api/v1/recognition/faces/{path_segment(face_id)}")

    @staticmethod
    def _form(parts):
        data = aiohttp.FormData()
        for field, content, filename in parts:
            data.add_field(field, content, filename=filename,
                           content_type=mimetypes.guess_type(filename)[0] or "application/octet-stream")
        return data

    async def close(self):
        """关闭客户端"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
