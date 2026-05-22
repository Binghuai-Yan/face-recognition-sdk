# FaceSDK Python SDK

FaceSDK Python 客户端库，提供人脸识别、人脸检测、人脸比对等功能。

## 安装

```bash
pip install facesdk-python
```

## 快速开始

### 同步客户端

```python
from facesdk import FaceSDKClient

# 初始化客户端
client = FaceSDKClient(
    api_url="http://localhost:8000",
    api_key="your-api-key",
    timeout=30,
    max_retries=3,
)

# 人脸检测
result = client.detect("/path/to/image.jpg")
print(f"检测到 {result.face_count} 张人脸")
for face in result.faces:
    print(f"置信度: {face.confidence}")
    print(f"位置: {face.bounding_box}")

# 人脸比对
result = client.compare("/path/to/face1.jpg", "/path/to/face2.jpg")
print(f"相似度: {result.similarity}")
print(f"是否匹配: {result.match}")

# 人脸识别（1:N）
result = client.search("/path/to/query.jpg", limit=5)
for match in result.results:
    print(f"Subject: {match.subject_id}, 相似度: {match.similarity}")

# 人脸库管理
subject = client.create_subject("user_001", "张三")
record = client.add_face("user_001", "/path/to/face.jpg")

# 关闭客户端
client.close()
```

### 异步客户端

```python
import asyncio
from facesdk import AsyncFaceSDKClient

async def main():
    # 初始化异步客户端
    client = AsyncFaceSDKClient(
        api_url="http://localhost:8000",
        api_key="your-api-key",
    )

    try:
        # 人脸检测
        result = await client.detect("/path/to/image.jpg")
        print(f"检测到 {result.face_count} 张人脸")

        # 人脸比对
        result = await client.compare("/path/to/face1.jpg", "/path/to/face2.jpg")
        print(f"相似度: {result.similarity}")

        # 人脸识别
        result = await client.search("/path/to/query.jpg", limit=5)
        for match in result.results:
            print(f"Subject: {match.subject_id}, 相似度: {match.similarity}")

    finally:
        await client.close()

# 运行
asyncio.run(main())
```

### 上下文管理器

```python
# 同步
with FaceSDKClient(api_url="http://localhost:8000", api_key="your-api-key") as client:
    result = client.detect("/path/to/image.jpg")
    print(result)

# 异步
async with AsyncFaceSDKClient(api_url="http://localhost:8000", api_key="your-api-key") as client:
    result = await client.detect("/path/to/image.jpg")
    print(result)
```

## 异常处理

```python
from facesdk import (
    FaceSDKClient,
    NoFaceException,
    ApiException,
    AuthenticationException,
)

client = FaceSDKClient(api_url="http://localhost:8000", api_key="your-api-key")

try:
    result = client.detect("/path/to/image.jpg")
except NoFaceException as e:
    print(f"未检测到人脸: {e}")
except AuthenticationException as e:
    print(f"认证失败: {e}")
except ApiException as e:
    print(f"API 错误: {e}")
    print(f"HTTP 状态码: {e.http_status_code}")
    print(f"错误代码: {e.error_code}")
```

## 配置选项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| api_url | - | API 基础 URL |
| api_key | - | API 密钥 |
| timeout | 30 | 请求超时时间（秒） |
| max_retries | 3 | 最大重试次数 |
| retry_delay | 0.5 | 重试延迟（秒） |
| verify_ssl | True | 是否验证 SSL 证书 |

## 许可证

MIT License
