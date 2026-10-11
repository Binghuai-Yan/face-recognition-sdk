# CompreFace 1.2 协议与 SDK 兼容性

依据 [官方 v1.2.0 REST 文档](https://github.com/exadel-inc/CompreFace/blob/v1.2.0/docs/Rest-API-description.md)。OpenAPI 描述本仓库使用的后端接口；SDK 的结果模型包含客户端归一化字段。

| 操作 | 服务 / 后端请求 | SDK 结果 |
|---|---|---|
| 检测 | Detection，POST `/api/v1/detection/detect`，multipart `file` | `result[]` 转为 `faces`，置信度取 `box.probability` |
| 比对 | Verification，POST `/api/v1/verification/verify`，`source_image`、`target_image` | 读取 `result[].face_matches[].similarity`，按客户端阈值判断 |
| 搜索 | Recognition，POST `/api/v1/recognition/recognize?prediction_count=N`，`file` | 展开每张脸的 `subjects[]`，过滤阈值并按相似度降序排列 |
| 特征提取 | Detection，检测接口加 `face_plugins=calculator` | `embedding[]` 转为 little-endian IEEE 754 float32，再使用标准 Base64 |
| Subject 列表 | Recognition，GET `/api/v1/recognition/subjects` | `{"subjects":["alice"]}` 转为 Subject 对象列表 |
| 创建 Subject | Recognition，POST `/api/v1/recognition/subjects`，JSON `subject` | 返回 Subject |
| 添加人脸 | Recognition，POST `/api/v1/recognition/faces?subject=...`，`file` | 返回 `image_id`、`subject` |
| 删除 | Recognition，DELETE `/api/v1/recognition/subjects/{subject}` 或 `/faces/{image_id}` | 无返回值；接受 2xx |

Detection、Recognition、Verification 密钥属于不同服务类型。所有客户端支持分服务密钥；旧单密钥字段只作为缺少对应配置时的回退。空的分服务密钥会报认证错误。

CompreFace 1.2.0 对不存在的服务密钥返回 HTTP 404（服务不存在），SDK 保留该状态，不将它改写为 401。调用方判断密钥错误时需同时考虑客户端的认证异常及后端服务查找失败。

搜索方法的 `limit` 对应 `prediction_count`（每张脸最多 N 个身份），与后端的 `limit`（检测多少张脸）不同。相似度阈值范围为 0–1，边界包含等号。搜索可包含多脸；1:1 比对和特征提取遇到多脸会失败，以免默认选择错误身份。默认比对阈值为 0.8，请根据数据校准。

后端可选参数通过 URL query 传递。支持插件依赖部署模型，常见插件为 age、gender、pose、landmarks、calculator、mask。CompreFace 1.2 没有 `quality` 插件或本项目先前声明的独立活体检测接口。

后端只持久化 `subject`，没有单独显示名称或自定义人脸 metadata。SDK 保留 `createSubject` 的 name 参数以兼容调用代码，但不会保存它；非空 metadata 会明确报错。需要这些信息时请使用应用自己的数据库。

四种 SDK 对同一向量使用一致的 float32 LE/Base64 编码；例如 `[1,-2,0.5]` 是 `AACAPwAAAMAAAAA/`。这只是编码，不是加密。旧 distance、quality、name 等模型字段仅保留兼容性，后端不会自动产生这些值。

检测、搜索、比对、读取、删除可重试暂时性网络错误及 429/500/502/503/504。每次重试包含完整图片；401 和参数错误不重试。创建 Subject 和添加人脸不自动重试，避免连接中断后重复写入。`maxRetries=0` 关闭重试。图片输入会缓冲到内存，应用应控制上传大小。

健康检查访问 `/api/v1/consistence/status`，解析 JSON 并要求 `status == "OK"`。容器内部检查 Java 8080；客户端经入口 80/8000 访问同一路径。`/health` 可能返回 SPA HTML，不能作为健康依据。
