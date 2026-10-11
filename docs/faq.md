# FAQ

**为什么检测成功，搜索或比对报 401？**
服务类型和 API Key 必须匹配。分别创建 Detection、Recognition、Verification 服务，并在 SDK/Vue 设置三个密钥；服务端环境变量不创建这些服务。

**检测返回空列表或比对相似度为零？**
后端返回 result 数组，置信度位于 box.probability。更新 SDK 后会正确归一化。1:1 比对/特征提取需要单脸；调用不存在的 recognition/compare 路由不会产生有效结果。

**为什么搜索设置数量和阈值没有作用？**
候选身份数量是 prediction_count；后端 limit 是图片中脸的数量。SDK/Vue 使用 prediction_count，并在客户端过滤 similarity >= threshold。相似度应按真实样本校准。

**是否支持活体、质量、metadata 和显示名称？**
CompreFace 1.2 没有本项目之前声明的独立活体 API 或 quality 插件。Subject 只保存 subject 字符串；metadata/name 需由应用保存。

**健康检查怎么做？**
解析 `/api/v1/consistence/status` 的 JSON，status 必须是 OK。只测试根路径或 /health 的 HTTP 200 可能测到 SPA 页面。Docker/Kubernetes 的 readiness 会直接检查 Java 8080 和实际依赖。

**重启后为什么数据丢失或新密码不生效？**
生产部署使用外部 postgres-data/PVC；内部数据库测试配置挂载 `/var/lib/postgresql/data`。删除卷会丢数据。修改环境变量不会修改已经初始化的数据库密码，需执行数据库账号管理流程。

**当前配置是否实现了加密或高可用？**
TLS 需要部署证书；Base64 不是加密。仓库没有数据库/图片/特征静态加密、高可用数据库或故障切换实现。

**完整测试会连接真实模型吗？**
默认运行 SDK 的本地 HTTP 协议测试、前端组件测试、若依示例逻辑测试、打包与配置检查。真实模型测试必须显式设置 FACESDK_LIVE=1、三种密钥和真实单脸图片；缺失时明确报告跳过，不把模拟结果当作实际模型验证。详见 [tests](../tests/README.md)。
