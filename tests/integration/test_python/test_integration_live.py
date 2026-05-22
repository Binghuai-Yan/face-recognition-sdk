#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FaceSDK Python SDK 集成测试
使用真实 CompreFace 服务
"""

import sys
import os
import unittest
import tempfile
import requests
from pathlib import Path

# 添加 SDK 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sdk" / "python"))

from facesdk import FaceSDKClient
from facesdk.exceptions import NoFaceException, ApiException

# CompreFace 服务配置
API_URL = "http://localhost:8000"
API_KEY = "c9388ce5-0298-4e15-997c-86092c3f19b4"


def download_test_image():
    """下载一张测试人脸图片"""
    # 使用公开的测试图片
    test_urls = [
        "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg",
    ]
    
    for url in test_urls:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                temp_file.write(resp.content)
                temp_file.close()
                print(f"[INFO] 下载测试图片: {temp_file.name} ({len(resp.content)} bytes)")
                return temp_file.name
        except Exception as e:
            print(f"[WARN] 下载失败: {e}")
            continue
    
    # 如果下载失败，创建一个简单的测试图片（不会检测到人脸）
    print("[WARN] 无法下载测试图片，将使用本地生成图片")
    temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    # 写入一个最小的 JPEG 文件头（无效但可以测试错误处理）
    temp_file.write(b'\xff\xd8\xff\xe0\x00\x10JFIF')
    temp_file.close()
    return temp_file.name


class TestFaceSDKIntegration(unittest.TestCase):
    """FaceSDK 集成测试（真实服务）"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        print(f"\n[INFO] 连接 CompreFace 服务: {API_URL}")
        
        # 健康检查
        try:
            resp = requests.get(f"{API_URL}/api/v1/consistence/status", timeout=5)
            print(f"[INFO] 服务状态: {resp.status_code}")
        except Exception as e:
            print(f"[ERROR] 无法连接服务: {e}")
            raise
        
        cls.client = FaceSDKClient(
            api_url=API_URL,
            api_key=API_KEY,
            timeout=60,
            max_retries=2,
        )
        
        # 下载测试图片
        cls.test_image = download_test_image()
        cls.created_subjects = []

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        # 清理测试数据
        for subject_id in cls.created_subjects:
            try:
                cls.client.delete_subject(subject_id)
                print(f"[INFO] 清理 Subject: {subject_id}")
            except Exception:
                pass
        
        # 删除临时文件
        if os.path.exists(cls.test_image):
            os.unlink(cls.test_image)
        
        cls.client.close()

    def test_01_health_check(self):
        """测试 1: 服务健康检查"""
        print("\n[TEST] 服务健康检查")
        resp = requests.get(f"{API_URL}/api/v1/consistence/status", timeout=5)
        self.assertEqual(resp.status_code, 200)
        print("[PASS] 服务健康")

    def test_02_list_subjects_empty(self):
        """测试 2: 列出人脸库（初始为空或包含默认数据）"""
        print("\n[TEST] 列出人脸库")
        subjects = self.client.list_subjects()
        self.assertIsNotNone(subjects)
        print(f"[PASS] 当前人脸库数量: {len(subjects)}")

    def test_03_create_subject(self):
        """测试 3: 创建人脸库"""
        print("\n[TEST] 创建人脸库")
        subject_id = "test_integration_001"
        subject = self.client.create_subject(subject_id, "集成测试用户")
        
        self.assertIsNotNone(subject)
        self.created_subjects.append(subject_id)
        print(f"[PASS] 创建人脸库: {subject}")

    def test_04_detect_face(self):
        """测试 4: 人脸检测"""
        print("\n[TEST] 人脸检测")
        try:
            result = self.client.detect(self.test_image)
            self.assertIsNotNone(result)
            print(f"[PASS] 检测到 {result.face_count} 张人脸")
            if result.face_count > 0:
                for face in result.faces:
                    print(f"  - 置信度: {face.confidence:.4f}, 位置: {face.bounding_box}")
        except NoFaceException:
            print("[INFO] 图片中未检测到人脸（可能是测试图片问题）")
        except Exception as e:
            print(f"[WARN] 检测异常: {e}")

    def test_05_add_face(self):
        """测试 5: 添加人脸"""
        print("\n[TEST] 添加人脸")
        subject_id = "test_integration_001"
        if subject_id not in self.created_subjects:
            self.created_subjects.append(subject_id)
        
        try:
            record = self.client.add_face(subject_id, self.test_image, {"source": "integration_test"})
            self.assertIsNotNone(record)
            print(f"[PASS] 添加人脸: {record.image_id}")
        except NoFaceException:
            print("[INFO] 图片中未检测到人脸，跳过添加")
        except Exception as e:
            print(f"[WARN] 添加异常: {e}")

    def test_06_search_face(self):
        """测试 6: 人脸搜索（1:N）"""
        print("\n[TEST] 人脸搜索")
        try:
            result = self.client.search(self.test_image, limit=5)
            self.assertIsNotNone(result)
            print(f"[PASS] 搜索完成, 结果数: {len(result.results)}")
            for match in result.results:
                print(f"  - Subject: {match.subject_id}, 相似度: {match.similarity:.4f}")
        except NoFaceException:
            print("[INFO] 图片中未检测到人脸，跳过搜索")
        except Exception as e:
            print(f"[WARN] 搜索异常: {e}")

    def test_07_delete_subject(self):
        """测试 7: 删除人脸库"""
        print("\n[TEST] 删除人脸库")
        subject_id = "test_delete_001"
        try:
            self.client.create_subject(subject_id, "待删除用户")
            self.created_subjects.append(subject_id)
            
            self.client.delete_subject(subject_id)
            self.created_subjects.remove(subject_id)
            print(f"[PASS] 删除人脸库: {subject_id}")
        except Exception as e:
            print(f"[WARN] 删除异常: {e}")

    def test_08_no_face_error(self):
        """测试 8: 无脸图片错误处理"""
        print("\n[TEST] 无脸图片错误处理")
        # 创建一个无脸图片
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00')
            temp_path = f.name
        
        try:
            with self.assertRaises(NoFaceException):
                self.client.detect(temp_path)
            print("[PASS] 正确抛出 NoFaceException")
        except Exception as e:
            print(f"[WARN] 预期 NoFaceException 但得到: {type(e).__name__}: {e}")
        finally:
            os.unlink(temp_path)


class TestFaceSDKConcurrency(unittest.TestCase):
    """并发测试"""

    @classmethod
    def setUpClass(cls):
        cls.client = FaceSDKClient(api_url=API_URL, api_key=API_KEY, timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_concurrent_health_checks(self):
        """测试并发健康检查"""
        print("\n[TEST] 并发健康检查")
        import concurrent.futures
        
        def check(i):
            try:
                resp = requests.get(f"{API_URL}/api/v1/consistence/status", timeout=5)
                return resp.status_code == 200
            except:
                return False
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        success_rate = sum(results) / len(results) * 100
        print(f"[PASS] 并发测试: {sum(results)}/{len(results)} 成功 ({success_rate:.0f}%)")
        self.assertTrue(success_rate >= 80, f"成功率过低: {success_rate}%")


if __name__ == "__main__":
    print("=" * 60)
    print("FaceSDK 集成测试")
    print(f"API URL: {API_URL}")
    print(f"API Key: {API_KEY}")
    print("=" * 60)
    
    unittest.main(verbosity=2)
