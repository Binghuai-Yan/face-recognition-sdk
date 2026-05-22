#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FaceSDK Python SDK 单元测试
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加 SDK 到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from facesdk import FaceSDKClient, AsyncFaceSDKClient
from facesdk.exceptions import (
    FaceSDKException,
    NoFaceException,
    ApiException,
    ValidationException,
)
from facesdk.models import (
    Face,
    BoundingBox,
    Quality,
    Subject,
    FaceRecord,
    DetectionResult,
    CompareResult,
    SearchResult,
)


class TestModels(unittest.TestCase):
    """测试数据模型"""

    def test_bounding_box_from_dict(self):
        """测试边界框模型"""
        data = {"x_min": 10, "y_min": 20, "x_max": 100, "y_max": 120}
        box = BoundingBox.from_dict(data)
        self.assertEqual(box.x_min, 10)
        self.assertEqual(box.y_min, 20)
        self.assertEqual(box.x_max, 100)
        self.assertEqual(box.y_max, 120)

    def test_quality_from_dict(self):
        """测试质量评分模型"""
        data = {"score": 0.95, "brightness": 0.8, "sharpness": 0.9}
        quality = Quality.from_dict(data)
        self.assertEqual(quality.score, 0.95)
        self.assertEqual(quality.brightness, 0.8)
        self.assertEqual(quality.sharpness, 0.9)

    def test_face_from_dict(self):
        """测试人脸模型"""
        data = {
            "box": {"x_min": 10, "y_min": 20, "x_max": 100, "y_max": 120},
            "landmarks": [[10, 20], [30, 40]],
            "confidence": 0.98,
            "quality": {"score": 0.95, "brightness": 0.8, "sharpness": 0.9},
        }
        face = Face.from_dict(data)
        self.assertEqual(face.bounding_box.x_min, 10)
        self.assertEqual(face.confidence, 0.98)
        self.assertEqual(len(face.landmarks), 2)
        self.assertIsNotNone(face.quality)

    def test_detection_result_from_dict(self):
        """测试检测结果模型"""
        data = {
            "faces": [
                {
                    "box": {"x_min": 10, "y_min": 20, "x_max": 100, "y_max": 120},
                    "confidence": 0.98,
                }
            ],
            "image_id": "test-123",
            "face_count": 1,
        }
        result = DetectionResult.from_dict(data)
        self.assertEqual(result.face_count, 1)
        self.assertEqual(result.image_id, "test-123")
        self.assertEqual(len(result.faces), 1)

    def test_compare_result_from_dict(self):
        """测试比对结果模型"""
        data = {
            "similarity": 0.95,
            "distance": 0.05,
            "threshold": 0.8,
            "is_match": True,
        }
        result = CompareResult.from_dict(data)
        self.assertEqual(result.similarity, 0.95)
        self.assertEqual(result.distance, 0.05)
        self.assertTrue(result.match)

    def test_search_result_from_dict(self):
        """测试搜索结果模型"""
        data = {
            "results": [
                {
                    "subject": "user_001",
                    "similarity": 0.92,
                    "distance": 0.08,
                    "is_match": True,
                }
            ],
            "face_count": 1,
            "image_id": "test-456",
        }
        result = SearchResult.from_dict(data)
        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].subject_id, "user_001")
        self.assertEqual(result.results[0].similarity, 0.92)

    def test_subject_from_dict(self):
        """测试人脸库模型"""
        data = {
            "subject": "user_001",
            "name": "张三",
        }
        subject = Subject.from_dict(data)
        self.assertEqual(subject.subject_id, "user_001")
        self.assertEqual(subject.name, "张三")

    def test_face_record_from_dict(self):
        """测试人脸记录模型"""
        data = {
            "image_id": "face-123",
            "subject": "user_001",
            "metadata": {"source": "camera_01"},
        }
        record = FaceRecord.from_dict(data)
        self.assertEqual(record.image_id, "face-123")
        self.assertEqual(record.subject_id, "user_001")
        self.assertEqual(record.metadata.get("source"), "camera_01")


class TestExceptions(unittest.TestCase):
    """测试异常类"""

    def test_facesdk_exception(self):
        """测试基础异常"""
        e = FaceSDKException("Test error", "TEST_ERROR", 400)
        self.assertEqual(str(e), "[TEST_ERROR] Test error")
        self.assertEqual(e.error_code, "TEST_ERROR")
        self.assertEqual(e.http_status_code, 400)

    def test_no_face_exception(self):
        """测试无人脸异常"""
        e = NoFaceException("No face detected")
        self.assertEqual(e.error_code, "NO_FACE_DETECTED")
        self.assertEqual(e.http_status_code, 400)

    def test_api_exception(self):
        """测试 API 异常"""
        e = ApiException("API error", "API_ERROR", 500)
        self.assertEqual(e.error_code, "API_ERROR")
        self.assertEqual(e.http_status_code, 500)


class TestFaceSDKClient(unittest.TestCase):
    """测试同步客户端"""

    def test_client_initialization(self):
        """测试客户端初始化"""
        client = FaceSDKClient(
            api_url="http://localhost:8000",
            api_key="test-api-key",
            timeout=30,
            max_retries=3,
        )
        self.assertEqual(client.api_url, "http://localhost:8000")
        self.assertEqual(client.api_key, "test-api-key")
        self.assertEqual(client.timeout, 30)
        self.assertEqual(client.max_retries, 3)

    def test_client_strips_trailing_slash(self):
        """测试 URL 尾部斜杠处理"""
        client = FaceSDKClient(
            api_url="http://localhost:8000/",
            api_key="test-api-key",
        )
        self.assertEqual(client.api_url, "http://localhost:8000")

    @patch("facesdk.client.requests.Session.request")
    def test_handle_error_no_face(self, mock_request):
        """测试无人脸错误处理"""
        client = FaceSDKClient(
            api_url="http://localhost:8000",
            api_key="test-api-key",
        )

        # 模拟响应
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.content = b'{"message": "No face detected"}'
        mock_response.json.return_value = {"message": "No face detected"}

        with patch.object(client.session, "request", return_value=mock_response):
            with self.assertRaises(NoFaceException):
                client._handle_response(mock_response)


class TestAsyncFaceSDKClient(unittest.TestCase):
    """测试异步客户端"""

    def test_async_client_initialization(self):
        """测试异步客户端初始化"""
        client = AsyncFaceSDKClient(
            api_url="http://localhost:8000",
            api_key="test-api-key",
            timeout=30,
        )
        self.assertEqual(client.api_url, "http://localhost:8000")
        self.assertEqual(client.api_key, "test-api-key")


class TestClientContextManager(unittest.TestCase):
    """测试上下文管理器"""

    def test_sync_context_manager(self):
        """测试同步上下文管理器"""
        with FaceSDKClient(
            api_url="http://localhost:8000",
            api_key="test-api-key",
        ) as client:
            self.assertIsNotNone(client)
            self.assertEqual(client.api_url, "http://localhost:8000")


if __name__ == "__main__":
    unittest.main(verbosity=2)
