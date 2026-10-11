# FaceSDK 修复与验证报告

日期：2026-10-11。审查基线：`56e979f`。范围包括四种语言 SDK、Vue 前端、OpenAPI、Docker Compose、Kubernetes、监控、若依示例和测试。本报告随代码一并提交至 GitHub。

原审查中的 20 项问题均已落实代码或配置修复，并增加对应回归检查。接口实现对照 CompreFace 官方 `v1.2.0` 文档及控制器源码。本轮在本机 Docker Desktop、Ubuntu 24.04 WSL2 和隔离 kind Kubernetes 1.31 集群执行真实 CompreFace 1.2.0 模型、持久化、TLS、监控和故障恢复测试。可提交的脱敏结果见 [全量测试汇总](full-test-summary-2026-10-11.json)。未覆盖范围列在文末。

## 20 项审查问题的处理

| 编号 | 原问题 | 修复与验证 |
|---|---|---|
| 1 / P1 | Java SSLContext 调用导致编译失败 | 保存并复用同一 X509TrustManager；完成 Java clean install、10 项测试以及 jar、源码、Javadoc 打包。 |
| 2 / P1 | Python 安装后缺少 aiofiles、入口不能导入 | 补充声明依赖，移除不存在的 CLI 入口；wheel/sdist 构建、全新虚拟环境安装、同步与异步入口导入、pip check 均通过。 |
| 3 / P1 | 检测、识别响应静默解析为空 | 四种 SDK 解析真实 result 数组和 box.probability，识别展开 subjects；共享官方协议样例与实际本地 HTTP 回归测试通过。 |
| 4 / P1 | 比对与特征调用不存在的路由 | 比对使用 verification/verify 与 source_image/target_image；特征使用检测 calculator 插件；验证解析、多脸拒绝和跨语言 float32 LE/Base64 一致性。 |
| 5 / P1 | 单密钥无法覆盖不同服务 | 所有 SDK 及若依示例支持 Detection、Recognition、Verification 独立密钥；保留旧单密钥回退；协议测试检查各请求实际使用的密钥。 |
| 6 / P1 | 数据库连接参数与镜像不兼容 | Compose/Kubernetes 配置 EXTERNAL_DB=true、JDBC URL 和独立用户名/密码；真实外部 PostgreSQL 连接、模型请求、备份恢复和持久化均验证。 |
| 7 / P1 | 默认启动缺失 Nginx 配置 | 补齐 Nginx TLS 配置与证书目录，将网关放入 gateway profile；信任测试证书的真实 HTTPS、HTTP 跳转与 429 限流通过。 |
| 8 / P1 | Redis 未认证且暴露公网端口 | 作为可选 cache profile，要求密码并移除外部端口；Compose 和 Kubernetes 实例均拒绝未认证请求，认证后 PONG。 |
| 9 / P1 | 公网 LoadBalancer 绕过 TLS Ingress | 删除默认公网 LoadBalancer，Service 使用 ClusterIP；真实 Nginx Ingress 的 API/UI SNI、证书校验、跳转及模型检测通过。 |
| 10 / P1 | 若依绑定/删除缺少用户归属检查 | 自助注册取当前用户；控制器要求认证，服务检查绑定、删除、查询所有权；6 项示例业务测试通过，完整宿主认证链仍需验证。 |
| 11 / P2 | Subject 字符串数组解析错误 | 四种 SDK 将 subjects 字符串列表转换为统一 Subject 模型；包含 Unicode 名称的 HTTP 回归通过。 |
| 12 / P2 | 前端删除按钮使用未定义 $t | 使用 useI18n().t，正确处理取消/关闭；组件测试验证确认删除、取消和请求行为。另补充空/dot 删除 ID 拒绝与路径编码。 |
| 13 / P2 | 搜索候选数量与阈值无效 | prediction_count 控制候选数量；SDK 和前端按相似度过滤并降序，阈值包含等号；协议和组件回归通过。 |
| 14 / P2 | 重试不能重放完整上传体 | 重试时重建请求/上传体，maxRetries=0 生效；暂时性错误可重试，401/参数错误及创建/添加写入不重试；各语言 HTTP 测试验证完整请求体与请求次数。 |
| 15 / P2 | 实时测试吞掉失败并误报成功 | 重写真实服务测试，断言/异常直接失败；显式启用但配置缺失会失败；三种部署分别运行 12 个 Python 用例和 Java/Go/Node 生命周期，前端另有 2 项真实 XHR 测试。 |
| 16 / P2 | 活体与质量 UI 没有后端实现 | 移除不存在的活体路由、quality 插件、开关、设置和能力声明，删除虚构服务初始化 SQL；前端测试、lint、构建通过。 |
| 17 / P2 | 健康探针把 SPA 页面当作 API | 使用真实 consistence/status 并要求 status=OK；真实启动、数据库停机时撤销健康/就绪、恢复后重新就绪及独立 liveness 均验证。 |
| 18 / P2 | 数据库目录未持久化、共享 PVC 扩容风险 | 内置 PGDATA 与外部 PostgreSQL/PVC 均实际重建验证；原账号、服务密钥、Subject、人脸 ID 和搜索保留；真实 pg_dump/pg_restore 通过。 |
| 19 / P2 | UI Ingress 指向缺失 Service | 补齐 compreface-ui Service，指向含 UI 的单容器；真实 HTTPS UI HTML、API 健康及检测请求均验证。 |
| 20 / P2 | 默认监控目标和 provisioning 缺失 | 补齐 exporters、Alertmanager、规则与 Grafana provisioning；真实指标采集、仪表盘、停库后两条告警在 Prometheus/Alertmanager firing、恢复后解除均通过。 |

## 协议与行为约定

详细协议见 [protocol.md](protocol.md) 和 [OpenAPI](../sdk/openapi/compreface-api.yaml)。OpenAPI 的删除 Subject 成功响应为 Subject，删除人脸成功响应为 FaceRecord；verification 不声明未实现的 prediction_count 参数。

比对默认阈值 0.8，边界包含等号；比对和特征提取拒绝多脸歧义。特征格式是 IEEE 754 float32 小端字节序再 Base64，例如 `[1,-2,0.5]` 对应 `AACAPwAAAMAAAAA/`。非空 metadata 明确拒绝；保留的 name 参数不被后端保存。显示名称和应用元数据应由应用数据库管理。

若依 `/face/login` 保留兼容路由，但行为为已登录用户的身份复核，不签发登录 token，仅返回必要验证字段。宿主必须启用方法级安全；示例不再声称直接提供独立人脸登录。详见 [集成说明](../examples/ruoyi-integration/README.md)。

## 测试结果

统一入口：[tests/run_all.py](../tests/run_all.py)。使用方式、真实服务环境变量及工具路径覆盖见 [测试说明](../tests/README.md)。日志、JUnit XML 和机器可读汇总写入 `test-results/`，该目录已被 Git 忽略。

最终统一入口启用 live 和生产依赖审计，共 30 个检查步骤全部通过，无失败或跳过步骤，退出码为 0。Go race 在 WSL 单独通过；部署及故障测试独立执行。`git diff --check` 通过。脱敏结果已收录 [full-test-summary-2026-10-11.json](full-test-summary-2026-10-11.json)；原始日志、凭据和备份仅保留于本机忽略目录，不上传。

| 模块 | 本地结果 |
|---|---|
| Python SDK / 配置 | 26 项通过：SDK 21 项、OpenAPI/部署/监控/负载配置 5 项。 |
| Python 分发 | 安装、wheel/sdist 构建、全新虚拟环境安装、包导入、依赖一致性检查通过。 |
| Java SDK | 10 项通过；clean install 和分发产物构建通过。 |
| 若依示例 | 6 项通过；clean verify、真实 Spring 依赖下编译通过。 |
| Go | 5 个顶层测试及 7 个子案例通过；go vet 通过。 |
| Node.js | 11 项通过；ESLint、TypeScript 类型检查、npm pack --dry-run 通过。 |
| Vue 前端 | 8 项通过：6 项组件/协议测试和 2 项真实 jsdom XHR API 测试；lint 与生产构建通过。 |
| Docker Compose | 主配置全部 profiles、测试配置均通过 config --quiet。 |
| Kubernetes | Kustomize 渲染通过；14 个资源通过 Kubernetes 1.31.0 严格 JSON Schema 验证，包含可选 Redis 和 Secret 示例。 |
| 真实服务测试 | Compose 外部数据库、内置数据库、Kubernetes 各 12 个 Python 用例及 Java/Go/Node 完整生命周期通过；各语言真实特征与直接 calculator API 参考 SHA256 一致。 |
| Go race | Ubuntu 24.04 WSL2 / gcc / Go 1.22 下通过，无 race 报告。远端 CI 另执行 --race。 |
| npm 生产依赖审计 | 官方 Registry 下 Node.js SDK 与前端均为 0 项已知漏洞；前端原锁文件 9 项漏洞已通过主版本内升级修复，并提高直接依赖最低版本。 |

HTTP 回归测试覆盖 multipart 字段、query、密钥、响应映射、阈值、特殊字符、错误、多脸及重试。真实模型测试另覆盖 JPEG/PNG、文件路径/字节/文件流、空白图、坏图、多脸拒绝、Unicode Subject、生命周期和 embedding。真实服务将不存在的密钥报告为 404，已修正原测试对 401 的错误预期。若依测试使用宿主边界桩，不覆盖完整若依系统。

补充依赖审计修复 Axios、Vue、vue-i18n 及相关传递依赖的已知漏洞，锁定当前修复版本，保留原主版本。Node.js SDK 同样提高 Axios/form-data 最低版本。统一入口提供 --audit，GitHub Actions 也执行生产 npm 审计；它只覆盖所查 Registry 已收录的 npm 生产依赖漏洞，不代表所有生态和容器镜像均已完成漏洞审计。

本机工具：Python 3.12.14、JDK 21.0.8、Maven 3.9.9、Go 1.27.2、Node.js 24.14.0、npm 11.9.0、Docker Compose CLI 2.29.7、kubectl 1.31.1。Maven 使用保留 TLS 校验的 HTTPS mirror，未关闭证书验证。GitHub Actions 定义了独立 Linux 检查入口，实际 CI 结果需以远端执行为准。

## 真实部署、故障和负载结果

- Compose 外部数据库：API/Core/PostgreSQL 健康，Redis 认证、Nginx TLS/跳转/限流、Prometheus 指标、Grafana datasource/dashboard、Alertmanager 配置与运行均通过。promtool 检查主配置及两条告警规则，amtool 检查告警配置。
- 外部数据库和 API force-recreate 后，原服务密钥、Subject、人脸 image_id 和实际识别结果保留。停库后 API 不再报告 OK，API/数据库两条告警均实际进入 Prometheus 和 Alertmanager；恢复后告警解除。
- 内置数据库：实际 SHOW data_directory 为 /var/lib/postgresql/data；隔离卷挂载正确。单容器重建后原账号/服务密钥和人脸记录仍可使用。
- Compose 与 Kubernetes 数据库均执行真实 pg_dump/pg_restore，所有 public 表行数、canary 和 uuid-ossp 校验一致；恢复库在校验后删除，原测试数据库保留。
- kind Kubernetes 1.31.0：API、PostgreSQL、Redis Ready，PVC Bound，Nginx Ingress API/UI 两个域名使用正确 SNI 并校验信任证书，真实检测通过。数据库约两分钟停机使 API readiness=False，恢复后 True；API Pod 未发生 liveness 重启，PVC 数据可识别；另重建 API Pod 后再次验证数据。
- Python 有界检测/比对负载：20 请求、并发 2、0 失败，平均延迟约 2298 ms、最大约 2479 ms。该运行与其他验证共享主机资源。
- WSL wrk 检测：2 线程、2 连接、20 秒，208/208 HTTP 200，0 socket 错误，10.39 req/s；平均 191.15 ms、P90 216.21 ms、P99 231.92 ms。
- JMeter 检测/比对：6/6 HTTP 200，0 错误。JMeter distribution SHA512、kind 及镜像下载的 SHA256/digest 已校验。CompreFace amd64 manifest 为 sha256:0a36c8d2f089a0166c282a9ddbb61c2c845574c27e2586cc422a3a5cdf71c5ac。

这些结果来自 CPU 模型、官方单脸样例和有限并发，是功能及恢复验证，不是生产最大吞吐量、长期稳定性或人群精度评估。各负载工具的请求组合和测试时主机负载不同，延迟不应直接横向比较。

模型测试使用 CompreFace v1.2.0 的 [FACE_1.jpg 样例](https://github.com/exadel-inc/CompreFace/blob/v1.2.0/load-tests/docker/tests/detect/faces/FACE_1.jpg)，双脸测试由两张完整样例拼接；照片不上传至本仓库。

## 未覆盖范围

- 可选 MinIO storage profile 未实际运行：原固定 release 的多个 Registry/镜像中转返回 404、502 或认证拒绝；未更换或冒用镜像标签。它是应用自用存储，CompreFace 实际人脸数据保存在已验证的 PostgreSQL。storage 配置检查通过，但不能声称 MinIO 运行通过。
- 当前没有可用的浏览器 UI 自动化连接，已执行 Vue 组件测试及真实 XHR；浏览器 GUI、交互布局和不同浏览器兼容性未验证。
- 完整若依宿主的 JWT、过滤链、方法安全启用和数据权限尚未验证。新增示例测试不替代宿主集成测试。
- 未执行人群准确率/误识率、长时间 soak、多节点高可用、GPU 与生产容量评估。单机 kind 的 PVC 恢复不能替代真实存储系统灾备演练。
- 前端构建保留约 1.69 MiB 入口资源体积警告与 Vite CJS API 弃用提示；Java 构建保留 shade 重叠/Javadoc 警告，若依测试有 Mockito 动态 agent 提示。它们未导致本次测试失败，不能据此声称构建完全无警告。

本轮保留已有 `docs/liveness-quality-plan.md`，未将其中的新能力设计作为已实现功能。

## 官方核对依据

- [CompreFace v1.2.0 REST API](https://github.com/exadel-inc/CompreFace/blob/v1.2.0/docs/Rest-API-description.md)
- [Verification 控制器](https://github.com/exadel-inc/CompreFace/blob/v1.2.0/java/api/src/main/java/com/exadel/frs/core/trainservice/controller/VerifyController.java)
- [Recognition 控制器](https://github.com/exadel-inc/CompreFace/blob/v1.2.0/java/api/src/main/java/com/exadel/frs/core/trainservice/controller/RecognizeController.java)
- [单容器 Dockerfile](https://github.com/exadel-inc/CompreFace/blob/v1.2.0/custom-builds/Single-Docker-File/Dockerfile) 与 [启动脚本](https://github.com/exadel-inc/CompreFace/blob/v1.2.0/custom-builds/Single-Docker-File/startup.sh)
- [API 数据库配置](https://github.com/exadel-inc/CompreFace/blob/v1.2.0/java/api/src/main/resources/application.yml)
