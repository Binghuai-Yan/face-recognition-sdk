# Python SDK

Python 3.8+，支持同步 requests 和异步 aiohttp；安装时自动包含 aiofiles。

```sh
python -m pip install ./sdk/python
```

```python
import os
from facesdk import FaceSDKClient, AsyncFaceSDKClient
keys = {s: os.environ[f"FACESDK_{s.upper()}_API_KEY"]
        for s in ("detection", "recognition", "verification")}
with FaceSDKClient("http://localhost:8000", api_keys=keys) as client:
    detection = client.detect("face.jpg", face_plugins="age,gender", status=True)
    comparison = client.compare("face.jpg", "face2.jpg")
    matches = client.search("face.jpg", limit=5, threshold=0.8)
    feature = client.extract_feature("face.jpg")
    client.create_subject("alice")
    record = client.add_face("alice", "face.jpg")
    print([s.subject_id for s in client.list_subjects()])
    client.delete_subject("alice")

async def detect_async():
    async with AsyncFaceSDKClient("http://localhost:8000", api_keys=keys) as client:
        return await client.detect("face.jpg")
```

所有图片参数接受路径、Path、bytes 或二进制文件对象。超时单位为秒；默认连接 5 秒、请求/读取 30 秒、最多重试 3 次、初始延迟 0.5 秒；异步 timeout 是一次请求的总超时。`comparison_threshold` 默认 0.8，`verify_ssl` 默认 true。

异常基类 `FaceSDKException`，常见子类为 `NoFaceException`、`AuthenticationException`、`ValidationException`、`ApiException`。模型可通过属性访问：`DetectionResult.faces/face_count`、`CompareResult.similarity/match`、`SearchResult.results`、`MatchResult.subject_id/similarity`。

密钥、阈值、重试、metadata/name 兼容行为和特征编码详见 [协议](../../docs/protocol.md)。测试运行：`python -m pytest sdk/python/tests`（仓库根目录）。
