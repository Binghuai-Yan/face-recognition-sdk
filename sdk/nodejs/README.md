# FaceSDK Node.js SDK

FaceSDK Node.js 客户端库，提供人脸识别、人脸检测、人脸比对等功能。

## 安装

```bash
npm install facesdk-nodejs
```

## 快速开始

```javascript
const { FaceSDKClient } = require('facesdk-nodejs');

// 创建客户端
const client = new FaceSDKClient({
  apiUrl: 'http://localhost:8000',
  apiKey: 'your-api-key',
  timeout: 30000,
  maxRetries: 3,
});

async function main() {
  try {
    // 人脸检测
    const detectionResult = await client.detect('/path/to/image.jpg');
    console.log(`检测到 ${detectionResult.face_count} 张人脸`);

    // 人脸比对
    const compareResult = await client.compare(
      '/path/to/face1.jpg',
      '/path/to/face2.jpg'
    );
    console.log(`相似度: ${compareResult.similarity}, 是否匹配: ${compareResult.is_match}`);

    // 人脸识别（1:N）
    const searchResult = await client.search('/path/to/query.jpg', 5);
    for (const match of searchResult.results) {
      console.log(`Subject: ${match.subject}, 相似度: ${match.similarity}`);
    }

    // 创建人脸库
    const subject = await client.createSubject('user_001', '张三');
    console.log(`创建人脸库: ${subject.subject}`);

    // 添加人脸
    const record = await client.addFace('user_001', '/path/to/face.jpg', {
      source: 'camera_01',
    });
    console.log(`添加人脸: ${record.image_id}`);

  } catch (error) {
    console.error('Error:', error.message);
  }
}

main();
```

## 使用 Buffer

```javascript
const fs = require('fs');

// 从 Buffer 检测人脸
const imageBuffer = fs.readFileSync('/path/to/image.jpg');
const result = await client.detect(imageBuffer);

// 从 Buffer 比对人脸
const image1 = fs.readFileSync('/path/to/face1.jpg');
const image2 = fs.readFileSync('/path/to/face2.jpg');
const compareResult = await client.compare(image1, image2);
```

## 错误处理

```javascript
const { FaceSDKClient, NoFaceError, APIError } = require('facesdk-nodejs');

try {
  const result = await client.detect('/path/to/image.jpg');
} catch (error) {
  if (error instanceof NoFaceError) {
    console.log('未检测到人脸');
  } else if (error instanceof APIError) {
    console.log(`API 错误: ${error.message} (HTTP ${error.httpStatusCode})`);
  } else {
    console.log(`其他错误: ${error.message}`);
  }
}
```

## 配置选项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| apiUrl | string | - | API 基础 URL |
| apiKey | string | - | API 密钥 |
| timeout | number | 30000 | 请求超时时间（毫秒） |
| maxRetries | number | 3 | 最大重试次数 |
| retryDelay | number | 500 | 重试延迟（毫秒） |

## 许可证

MIT License
