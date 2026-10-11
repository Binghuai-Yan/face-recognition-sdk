# Node.js SDK

Node.js 18+ 推荐。安装本地包：`npm install ./sdk/nodejs`。包同时提供 CommonJS 和 TypeScript 声明。

```javascript
const { FaceSDKClient } = require('facesdk-nodejs');
async function main() {
  const client = new FaceSDKClient({
    apiUrl: 'http://localhost:8000',
    apiKeys: {
      detection: process.env.FACESDK_DETECTION_API_KEY,
      recognition: process.env.FACESDK_RECOGNITION_API_KEY,
      verification: process.env.FACESDK_VERIFICATION_API_KEY
    },
    comparisonThreshold: 0.8
  });
  console.log(await client.detect('face.jpg'));
  console.log(await client.compare('face.jpg', 'face2.jpg'));
  console.log(await client.search('face.jpg', 5, 0.8));
  console.log(await client.extractFeature('face.jpg'));
  await client.createSubject('alice');
  await client.addFace('alice', 'face.jpg');
  console.log(await client.listSubjects());
  await client.deleteSubject('alice');
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
```

图片接受路径、Buffer、Readable；Stream 会先完整缓冲以支持重试。timeout、retryDelay 单位为毫秒，默认 30000 和 500；maxRetries 默认 3，可设为 0。错误为 `FaceSDKError`、`APIError`、`NoFaceError`，携带 errorCode/httpStatusCode。

返回 `faces/face_count`、`similarity/is_match/threshold`、`results/face_count`；保留原始响应字段。Subject 列表返回 `{subject}` 对象数组。详见 [协议](../../docs/protocol.md)。在本目录运行 `npm ci && npm test && npm run lint`。
