#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: facesdk/tests/integration/test_python/test_integration.py
Copyright (c) 2024 FaceSDK Contributors
MIT License

FaceSDK Python Integration Tests
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

# 添加 SDK 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "sdk" / "python"))

from facesdk import FaceSDKClient
from facesdk.exceptions import NoFaceException


class TestFaceSDKIntegration(unittest.TestCase):
    """FaceSDK 集成测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.api_url = os.getenv("FACESDK_API_URL", "http://localhost:8000")
        cls.api_key = os.getenv("FACESDK_API_KEY", "test-api-key")
        cls.client = FaceSDKClient(
            api_url=cls.api_url,
            api_key=cls.api_key,
            timeout=30,
        )
        cls.test_subjects = []

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        # 清理测试数据
        for subject_id in cls.test_subjects:
            try:
                cls.client.delete_subject(subject_id)
            except Exception:
                pass
        cls.client.close()

    def _create_test_image(self, filename="test_face.jpg"):
        """创建测试图片（实际测试应使用真实人脸图片）"""
        # 这里应该返回真实的人脸图片路径
        # 为了测试，我们假设有一个测试图片目录
        test_images_dir = Path(__file__).parent / "test_images"
        test_image = test_images_dir / filename
        if test_image.exists():
            return str(test_image)
        # 如果没有测试图片，创建一个空的临时文件（测试会失败，但代码结构正确）
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake_image_data")
            return f.name

    def test_health_check(self):
        """测试健康检查"""
        import requests
        response = requests.get(f"{self.api_url}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "UP")

    def test_detect_with_no_face(self):
        """测试无脸图片检测"""
        # 创建一个没有脸的图片
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake_image_without_face")
            temp_path = f.name

        try:
            with self.assertRaises(NoFaceException):
                self.client.detect(temp_path)
        finally:
            os.unlink(temp_path)

    def test_subject_management(self):
        """测试人脸库管理"""
        subject_id = "test_subject_001"
        self.test_subjects.append(subject_id)

        # 创建人脸库
        subject = self.client.create_subject(subject_id, "测试人脸库")
        self.assertEqual(subject.subject_id, subject_id)

        # 列出人脸库
        subjects = self.client.list_subjects()
        subject_ids = [s.subject_id for s in subjects]
        self.assertIn(subject_id, subject_ids)

        # 删除人脸库
        self.client.delete_subject(subject_id)
        self.test_subjects.remove(subject_id)

        # 验证删除
        subjects = self.client.list_subjects()
        subject_ids = [s.subject_id for s in subjects]
        self.assertNotIn(subject_id, subject_ids)

    def test_face_management(self):
        """测试人脸管理"""
        subject_id = "test_face_mgmt_001"
        self.test_subjects.append(subject_id)

        try:
            # 创建人脸库
            self.client.create_subject(subject_id, "人脸管理测试")

            # 注意：实际测试需要真实人脸图片
            # 这里仅演示 API 调用流程

        finally:
            # 清理
            try:
                self.client.delete_subject(subject_id)
                self.test_subjects.remove(subject_id)
            except Exception:
                pass


class TestFaceSDKConcurrency(unittest.TestCase):
    """并发测试"""

    @classmethod
    def setUpClass(cls):
        cls.api_url = os.getenv("FACESDK_API_URL", "http://localhost:8000")
        cls.api_key = os.getenv("FACESDK_API_KEY", "test-api-key")
        cls.client = FaceSDKClient(
            api_url=cls.api_url,
            api_key=cls.api_key,
        )

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_concurrent_requests(self):
        """测试并发请求"""
        import concurrent.futures

        def make_request(i):
            try:
                import requests
                response = requests.get(f"{self.api_url}/health")
                return response.status_code == 200
            except Exception as e:
                return False

        # 并发 10 个请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # 所有请求都应该成功
        self.assertTrue(all(results))


if __name__ == "__main__":
    unittest.main()
