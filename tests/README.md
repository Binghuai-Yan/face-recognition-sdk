# 测试

需要 Python 3.11+、Java 11+ / Maven、Go、Node.js 18+ / npm、Docker Compose v2 CLI、kubectl。Compose 与 kustomize 检查不启动容器或连接集群。

```sh
python -m pip install -r tests/requirements.txt
python tests/run_all.py
```

入口会执行 OSS 网关单测与 S3 请求契约验证、Python 全量单测与 HTTP 协议测试、OpenAPI/部署配置验证、源码与 wheel 构建及全新虚拟环境安装；Java clean install（包含测试、源码、Javadoc 和打包）；若依示例编译与权限业务测试；Go test/vet；Node 测试/lint/TypeScript/包内容检查；Vue 组件测试/lint/生产构建；三种 Compose 配置验证、Kubernetes kustomize 和 1.31.0 严格 JSON schema 校验。Schema 下载保留 TLS 校验，缓存于 test-results。

## 真实 OSS 测试

启动主 Compose 配置（默认 RustFS），使用测试专用 Recognition 服务和第二个独立 Recognition 服务。在上述 live 配置之外设置：

```sh
export FACESDK_OTHER_RECOGNITION_API_KEY='<第二个 Recognition key>'
export FACESDK_OSS_ENDPOINT=http://localhost:9000
export FACESDK_OSS_BUCKET=facesdk-images
export FACESDK_OSS_ACCESS_KEY_ID='<测试存储 access ID>'
export FACESDK_OSS_SECRET_ACCESS_KEY='<测试存储 secret>'
python tests/run_all.py --live --oss-live --audit
```

`--oss-live` 缺少任何必需配置会失败。验证 multipart/base64 原图 SHA256、私有 bucket、授权读图和 static 兼容、跨服务访问/删除、批量与 Unicode Subject 删除、拒绝上传无残留。测试只清理自己创建的 Subject。该步骤需要 ListBucket 权限；未开启则不执行，不算通过。

故障与持久化演练只在隔离实例中进行：停止 RustFS 后上传应 503 且没有注册记录；删除应返回 pending 并立即禁止读取；重建网关、恢复 RustFS 后对象应最终删除；保留数据卷重建 RustFS/网关后原图仍可授权读取。PostgreSQL 还需核对新 image_id 未保存图片 bytes。完整备份应包括数据库、bucket 和 journal，详见 [存储说明](../docs/object-storage.md)。

```sh
python tests/runtime/object_storage_faults.py --config test-results/runtime-live.json \
  --env-file test-results/runtime.env --project facesdk-fulltest-20261011
```

此脚本仅允许 facesdk-fulltest-* 项目，自动恢复 RustFS 并清理自己的数据，使用主 Compose 配置；Docker 和 Compose CLI 可通过 --docker、--compose 指定。不要在生产项目中执行。

任一必需工具缺失或命令失败，入口返回非零。日志、JUnit 和 summary.json 保存于 test-results（不提交）。工具路径可通过 FACESDK_MAVEN、FACESDK_GO、FACESDK_NPM、FACESDK_COMPOSE、FACESDK_KUBECTL 覆盖。受网络环境限制时可通过 FACESDK_MAVEN_SETTINGS 指定可信的 HTTPS Maven mirror，避免关闭 TLS 验证。

加入 --audit 可执行 Node.js SDK 和前端的 npm 生产依赖漏洞审计，显式使用官方 registry.npmjs.org，因为部分镜像站未实现审计 API。GitHub Actions 默认启用 --race --audit。

HTTP 协议 fixtures 基于 CompreFace 官方 1.2 文档，由四种 SDK 共用。测试实际本地 HTTP 请求、multipart、Unicode 标识、按服务密钥、响应解析、阈值边界、多脸、错误、完整请求体重试以及非幂等写入不重试。它们不执行人脸模型。

## 真实模型测试

先启动 CompreFace，在管理 UI 建立 Detection / Recognition / Verification 服务。在测试专用应用中设置：

```sh
export FACESDK_LIVE=1
export FACESDK_API_URL=http://localhost:8000
export FACESDK_DETECTION_API_KEY='<Detection key>'
export FACESDK_RECOGNITION_API_KEY='<Recognition key>'
export FACESDK_VERIFICATION_API_KEY='<Verification key>'
export FACESDK_TEST_IMAGE=/path/to/single-face.jpg
python tests/run_all.py --live
```

同步/异步各测试检测→创建→添加→搜索→比对→特征→删除的流程，另测合法空白 PNG、无效密钥、PNG 文件路径、JPEG 文件流、多脸歧义、无效图片、Unicode Subject 和真实特征。共 12 个 Python live 用例。CompreFace 1.2.0 对不存在的服务密钥返回 404，SDK 保留该状态；401 的映射由 HTTP 协议测试覆盖。

启用 live 后还会运行 Java、Go、Node.js 的完整模型生命周期，并检查各语言特征字节的 SHA256 与直接 calculator API 的参考值一致。前端包含 2 项使用 jsdom 实际 XHR 的检测/比对及 CRUD 测试，要求 FACESDK_WEB_URL 指向提供 `/api/` 同源代理的前端 Nginx（不是仅提供静态文件的服务器）。该检查覆盖 API 传输，浏览器 GUI 操作需要独立验证。

Subject 带随机 UUID，并清理测试数据；断言或异常直接失败。未启用 live 时，12 个 Python 用例和 2 个前端 XHR 用例明确跳过，不能据此声称模型测试通过。显式启用后配置缺失会失败。

可以在**全新隔离测试实例**中用真实管理 REST API 创建测试账号及服务，并将凭据存入 Git 忽略目录。请使用自有或已获授权的单脸测试照片：

```sh
python tests/runtime/provision.py --url http://localhost:8000 \
  --image /path/to/single-face.jpg --web-url http://localhost:18083/ \
  --output test-results/runtime-live.json
python tests/run_all.py --live --audit --live-config test-results/runtime-live.json
```

provision 同时生成直接 API 特征的参考 SHA256。不要提交该 JSON、照片、私钥、数据库备份、kubeconfig 或运行环境文件。日志会遮盖配置中的服务密钥，但原始容器日志可能含密钥，分享前仍需脱敏。

## Docker、WSL 与 Kubernetes 运行验证

只在专用测试项目或集群中执行故障和重建。先完成统一入口，切换部署时可用下面命令仅重跑四种语言的真实模型测试（Java jar 必须已构建）：

```sh
python tests/runtime/live_matrix.py --config test-results/runtime-live.json --name compose-external
python tests/runtime/database.py --project facesdk-fulltest-20261011
python tests/runtime/persistence.py --config test-results/runtime-live.json \
  --marker test-results/marker.json create
# 重建 API / PostgreSQL，保留卷，再执行：
python tests/runtime/persistence.py --config test-results/runtime-live.json \
  --marker test-results/marker.json wait
python tests/runtime/persistence.py --config test-results/runtime-live.json \
  --marker test-results/marker.json verify
```

database 执行真实 pg_dump/pg_restore，并校验 canary 与 uuid-ossp。persistence 验证原服务密钥、Subject、已存 image_id 及实际搜索；测试结束用 remove 清理 marker 对应的人脸。wait 要求健康 JSON 为 OK；unavailable 要求数据库停机时 API 健康不再为 OK。

database 另校验恢复后的所有 public 表行数；请在没有并发写入时运行。对隔离 kind 数据库可改用 `--kubectl <路径> --kubeconfig <测试配置>`，仅允许 kind-facesdk-fulltest context。

`check_services.py` 验证 API/Core/数据库、信任证书的 HTTPS、HTTP 跳转、真实 429、Prometheus 指标、Grafana provisioning、Alertmanager 和 Redis 认证。默认端口匹配本次隔离栈的 runtime.env（API 18800、TLS 18443、Prometheus 19090、Grafana 13000）。使用：

```sh
python tests/runtime/check_services.py --config test-results/runtime-live.json \
  --env-file test-results/runtime.env --project facesdk-fulltest-20261011
# 在隔离项目停止 PostgreSQL 后，验证真实告警投递；恢复后验证解除：
python tests/runtime/check_alerts.py firing
python tests/runtime/check_alerts.py resolved
```

内置 PostgreSQL 部署使用 docker-compose.test.yml，设置 COMPREFACE_TEST_PORT=18801。必须重新 provision 该实例的密钥，再执行 live_matrix 及 persistence；它与外部数据库实例的数据互相独立。

`tests/runtime/kind.yaml` 创建隔离 Kubernetes 1.31 集群（HTTP 18082 / HTTPS 18445）。应用仓库资源前，在专用 namespace 创建随机 Secret，替换 Ingress 测试域名并提供带对应 SAN 的 TLS 证书。显式指定测试 kubeconfig，避免操作其他集群。待 API、PostgreSQL、Redis、Ingress controller Ready 后，port-forward API 到 18802，provision 并执行 live_matrix。使用 curl 的 --resolve、--cacert 校验 API/UI 两个域名的 SNI/TLS 路由，不关闭证书验证。

验证 PostgreSQL scale 0→1 时 API readiness 变为 False 并恢复、API restartCount 不增长、PVC 与人脸记录保留。最后再重建 API Pod 验证同一记录。首次模型加载可能需要几分钟；本机内存不足以同时运行多个模型时逐个切换部署，保留数据卷。

可用 `kubernetes_probe.py --kubectl <路径> --kubeconfig <测试配置> --config <live JSON> --marker <marker JSON>` 自动验证约两分钟数据库停机及恢复；该脚本仅接受 kind-facesdk-fulltest context，并在 finally 中恢复数据库副本。`check_ingress.py --config <live JSON> --certificate <CA PEM>` 执行带证书校验的 API/UI TLS 路由和真实检测，结果写入忽略目录。

## 有界负载

```sh
python tests/runtime/load.py --config test-results/runtime-live.json --requests 20 --concurrency 2
```

它断言真实检测、比对响应，输出失败数和延迟。另有 [wrk](performance/wrk/README.md) 检测负载与 JMeter 检测/比对计划。JMeter 可用 -Jdetection_threads、-Jverification_threads、-Jloops、-Jramp_seconds 控制规模；输出使用新文件，避免追加导致统计混淆。这些小规模检查验证请求正确性和测试工具，不代表最大容量或人群准确率评估。

Go race 检查：`python tests/run_all.py --race`，需要可用 C 编译器；也可在 WSL 中对 sdk/go 执行 go test -race ./...。若依测试使用宿主边界桩，完整宿主 JWT、过滤链和方法安全仍需宿主集成测试。实际测试结果见 [修复与验证报告](../docs/repair-report-2026-10-11.md) 和 [全量测试汇总](../docs/full-test-summary-2026-10-11.json)。
