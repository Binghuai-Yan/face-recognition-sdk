# Vue 管理界面

Node.js 18+，Vue 3 / Element Plus，支持中英切换。此界面独立于 CompreFace 镜像自带管理界面。

```sh
npm ci
npm run serve
```

开发服务为 `http://localhost:8080`，`/api` 代理到 `http://localhost:8000`。先使用 CompreFace 自带 UI 创建三种服务，在此界面设置 Detection、Recognition、Verification 密钥。

密钥保存于当前浏览器 localStorage，本界面适用于可信操作者。面向普通用户发布时应由应用后端代理 API 并实现用户权限。生产构建为 `npm run build`，需在入口服务器将 `/api` 转发至 CompreFace。

功能包含检测、比对、按阈值搜索、Subject 创建/删除/添加人脸。搜索数量是每张脸候选身份数；人脸库数量使用后端 total_elements，避免分页低估。不提供后端不支持的质量插件或独立活体检测，也不保存单独 Subject 显示名称。

验证：`npm test`、`npm run lint -- --no-fix`、`npm run build`。协议详见 [文档](../docs/protocol.md)。
