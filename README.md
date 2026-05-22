# FaceSDK - 人脸识别解决方案

FaceSDK 是一套完整的人脸识别解决方案，基于 CompreFace 引擎，提供 REST API 和多种语言的客户端 SDK。

## 功能特性

- **人脸检测**：检测图片中的人脸位置、关键点和质量评分
- **人脸比对（1:1）**：比对两张人脸图片的相似度
- **人脸识别（1:N）**：在人脸库中搜索相似人脸
- **人脸库管理**：创建、删除、列出人脸库
- **人脸管理**：添加、删除、更新人脸
- **多语言 SDK**：Java、Python、Go、Node.js
- **离线部署**：支持完全离线运行
- **生产就绪**：支持高可用、监控、日志

## 快速开始

### 1. 启动服务

```bash
cd docker-compose
cp .env.example .env
# 编辑 .env 文件，设置 API 密钥
docker-compose up -d
```

### 2. 使用 SDK

#### Java

```java
FaceSDK sdk = FaceSDK.builder()
    .apiUrl("http://localhost:8000")
    .apiKey("your-api-key")
    .build();

DetectionResult result = sdk.getClient().detect(imageData);
System.out.println("检测到 " + result.getFaceCount() + " 张人脸");
```

#### Python

```python
from facesdk import FaceSDKClient

client = FaceSDKClient(
    api_url="http://localhost:8000",
    api_key="your-api-key"
)

result = client.detect("/path/to/image.jpg")
print(f"检测到 {result.face_count} 张人脸")
```

#### Go

```go
client := facesdk.NewClient(
    "http://localhost:8000",
    "your-api-key",
)

result, err := client.Detect(ctx, "/path/to/image.jpg", nil)
fmt.Printf("检测到 %d 张人脸\n", result.FaceCount)
```

#### Node.js

```javascript
const { FaceSDKClient } = require('facesdk-nodejs');

const client = new FaceSDKClient({
  apiUrl: 'http://localhost:8000',
  apiKey: 'your-api-key'
});

const result = await client.detect('/path/to/image.jpg');
console.log(`检测到 ${result.face_count} 张人脸`);
```

## 项目结构

```
facesdk/
├── docker-compose/          # Docker Compose 部署配置
│   ├── docker-compose.yml
│   ├── .env.example
│   └── README.md
├── kubernetes/              # Kubernetes 部署配置
│   ├── namespace.yaml
│   ├── compreface-deployment.yaml
│   └── ...
├── sdk/                     # 多语言 SDK
│   ├── java/               # Java SDK
│   ├── python/             # Python SDK
│   ├── go/                 # Go SDK
│   ├── nodejs/             # Node.js SDK
│   └── openapi/            # OpenAPI 规范
├── tests/                   # 测试
│   ├── integration/        # 集成测试
│   ├── performance/        # 性能测试
│   └── health/             # 健康检查
├── monitoring/              # 监控配置
│   ├── prometheus/
│   └── grafana/
├── examples/                # 示例项目
│   ├── ruoyi-integration/  # Ruoyi 集成示例
│   ├── java-example/
│   ├── python-example/
│   ├── go-example/
│   └── node-example/
└── docs/                    # 文档
    ├── architecture.md
    ├── deployment.md
    ├── api_reference.md
    ├── faq.md
    └── troubleshooting.md
```

## 系统要求

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4 CPU 核心
- 8GB 内存
- 20GB 磁盘空间

## 文档

- [部署指南](docker-compose/README.md)
- [Kubernetes 部署](kubernetes/README.md)
- [Java SDK 文档](sdk/java/README.md)
- [Python SDK 文档](sdk/python/README.md)
- [Go SDK 文档](sdk/go/README.md)
- [Node.js SDK 文档](sdk/nodejs/README.md)
- [API 参考](sdk/openapi/compreface-api.yaml)

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 支持

如有问题，请通过以下方式联系我们：

- Email: team@facesdk.io
- GitHub Issues: https://github.com/facesdk/facesdk/issues
