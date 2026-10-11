# FaceSDK

FaceSDK 提供 CompreFace 1.2.0 的 Python（同步/异步）、Java、Node.js、Go 客户端，以及 Vue 管理界面、部署配置和若依集成示例。

## 启动服务

安装支持 Linux 容器的 Docker Engine 和 Docker Compose v2，然后执行：

```sh
cd docker-compose
cp .env.example .env
# 编辑 .env，替换 PostgreSQL、RustFS 及可选服务密码
docker compose up -d
```

默认启动 CompreFace、PostgreSQL、RustFS 和 OSS 存储网关，端口为 `127.0.0.1:8000`。新增人脸的原图保存到 RustFS，身份与特征保存在 PostgreSQL；可通过 endpoint、bucket、region 和凭据接入其他 S3 兼容 OSS，见 [对象存储配置](docs/object-storage.md)。在 CompreFace 自带管理界面创建应用及 Detection、Recognition、Verification 三种服务，分别保存三个 API Key。环境变量不会自动创建服务或密钥。

## 使用 SDK

```sh
python -m pip install ./sdk/python
```

```python
import os
from facesdk import FaceSDKClient

with FaceSDKClient("http://localhost:8000", api_keys={
    "detection": os.environ["FACESDK_DETECTION_API_KEY"],
    "recognition": os.environ["FACESDK_RECOGNITION_API_KEY"],
    "verification": os.environ["FACESDK_VERIFICATION_API_KEY"],
}) as client:
    print(client.detect("face.jpg").face_count)
    print(client.compare("face.jpg", "face.jpg").similarity)
    print(client.search("face.jpg", limit=5, threshold=0.8).results)
```

人脸库最小流程是 `create_subject` → `add_face` → `search` → `delete_subject`。比较与特征提取要求每张图片恰好包含一张人脸。搜索 `limit` 表示每张脸的候选身份数量，阈值由客户端过滤。

## 文档和测试

- [协议与兼容性](docs/protocol.md)；[OpenAPI](sdk/openapi/compreface-api.yaml)
- [Python](sdk/python/README.md)、[Java](sdk/java/README.md)、[Node.js](sdk/nodejs/README.md)、[Go](sdk/go/README.md)
- [Docker](docker-compose/README.md)、[Kubernetes](kubernetes/README.md)、[Vue 界面](facesdk-web/README.md)
- [通用 OSS / 默认 RustFS](docs/object-storage.md)
- [若依示例](examples/ruoyi-integration/README.md)、[架构](docs/architecture.md)、[FAQ](docs/faq.md)
- [完整测试入口](tests/README.md)、[修复与验证报告](docs/repair-report-2026-10-11.md)、[全量测试汇总](docs/full-test-summary-2026-10-11.json)
- [OSS 接入测试报告](docs/oss-report-2026-10-12.md)、[OSS 测试汇总](docs/oss-test-summary-2026-10-12.json)

本仓库配置单个数据库实例，未提供数据库高可用或存储加密实现。模型准确率、容量和生产可用性需要在实际环境验证。许可证为 MIT。
