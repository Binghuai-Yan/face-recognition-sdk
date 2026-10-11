# OSS 接入与测试报告（2026-10-12）

本轮将主部署改为默认保存原图到 RustFS 1.0.1，通过标准 S3 SigV4 接入可配置的对象存储。CompreFace 1.2 设置 SAVE_IMAGES_TO_DB=false，PostgreSQL 保留身份、image_id 与 embedding。SDK 和 Vue 通过 OSS 网关访问原有 API，私有图片由服务密钥授权读取。

网关新增持久化 SQLite 图片关联、上传意图与删除 outbox；不保存服务 API Key。OSS 上传失败不注册人脸，注册拒绝后清理对象，提交后响应丢失可凭下次认证请求恢复。后端删除后立即撤销读图，OSS 删除失败会持久化排队并在恢复后重试。重复 file / Subject 参数被拒绝，避免图片与后台注册数据不一致。Unicode、问号、&、字面 %xx 和路径分隔符只解码一次。

Compose 默认启用 RustFS 和网关；外部 OSS 覆盖文件关闭本地 RustFS。Kubernetes 新增各自的 PVC、Deployment 和 Service，API/UI Ingress 均指向网关。网关使用单副本 Recreate，健康探针区分进程存活和依赖就绪。Nginx 动态解析网关地址以支持容器重建；静态图片旧 URL 含密钥，因此默认代理避免记录此类访问路径。

## 测试结果

最终版本的统一入口执行 `tests/run_all.py --live --oss-live --audit --live-config <私密配置>`，34/34 检查通过，无跳过项。检查包含安装、单测、打包、lint、类型检查、三个 Compose 配置、Kubernetes 严格 Schema、四语言真实模型和真实对象存储。具体用例：

| 测试 | 结果 |
|---|---|
| OSS 网关和标准 S3 请求契约 | 26 项通过 |
| Python SDK / OpenAPI / 配置 | 26 项通过 |
| Java SDK / 若依 | 10 / 6 项通过 |
| Go | 5 个顶层测试、vet 通过；Ubuntu 24.04 WSL 的 race 和 vet 通过 |
| Node.js SDK | 11 项通过，lint、TypeScript、打包通过 |
| Vue | 8 项通过，包含 2 项通过同源代理的真实 XHR；lint、构建通过 |
| Python 真实模型 | 12 项通过，包含同步/异步、Unicode、多脸、非法图片和特征参考 SHA256 |
| Java / Go / Node.js 真实模型 | Docker 与 kind 两种部署的生命周期全部通过 |
| 真实 OSS | 默认 Docker、kind、外部 endpoint 配置各 5 项通过 |
| Kubernetes 1.31.0 严格 Schema | 20 个资源通过 |
| Node / Vue 生产依赖审计 | 均为 0 个漏洞 |

真实 OSS 用例直接读取 RustFS 对象并核对输入 SHA256，验证 multipart/base64、私有 bucket、现代/旧图片路由、跨服务读图与删除隔离、删除后 404、批量和 Unicode Subject 删除、注册拒绝无残留、重复上传参数拒绝。

网关单测另验证后台超时后延迟提交上传/删除、网关重启后的意图保留与恢复、未决状态阻止重复写入，以及旧数据库图片迁移失败后的重试，避免将暂时未观察到提交误判为失败而丢失原图或删除任务。

Docker 故障与恢复演练 7/7 通过：

1. 新 image_id 的 embedding 存在，关联原图的 PostgreSQL bytes 为空。
2. SQLite backup API 恢复图片关联后，原图字节再次可读取。
3. 保留卷重建 RustFS 和网关后，图片完整保留。
4. RustFS 停机后依赖健康返回 503，独立 liveness 保持 200。
5. OSS 停机上传返回 503，后端没有新增人脸。
6. OSS 停机删除返回 pending，后端删除成功且图片立即不可读。
7. 停机期间重建网关，恢复 RustFS 后持久化删除队列自动完成。

kind 的 RustFS / 网关 Pod 重建后，PVC 内关联和原图保留，同一 image_id 可授权读取，搜索结果正确。API/UI 域名的 SNI、可信证书 TLS、HTTP 跳转和真实检测通过。Docker TLS、429 限流、Prometheus 数据库/网关探测、Grafana、Alertmanager 与 Redis 认证复测通过。

外部配置测试使用同一真实 RustFS，经 host.docker.internal 的不同 endpoint 连接，并使用独立 bucket / prefix、独立 journal 和关闭本地 RustFS 的 Compose 覆盖配置。它验证配置可替换和标准 S3 接入，不代表 AWS 或其他云厂商账号已经实际验证。

## 使用边界

支持提供相应 S3 兼容接口的对象存储；阿里云 OSS / COS 原生专属协议未实现。网关当前要求单进程、单副本；多副本需共享事务数据库和分布式协调。服务密钥轮换、多个新增 image_id 的上传恢复歧义、管理端删除产生的孤立对象需人工对账。已存在的 PostgreSQL 原图在首次授权读取时复制到 OSS，不会自动清空旧数据库图片。

必须共同备份 PostgreSQL、bucket 和 journal。新图片未写入 PostgreSQL，遗失 journal 时须恢复备份。小规模功能测试不能替代生产容量、多节点灾备和模型准确率评估。

配置与恢复步骤见 [object-storage.md](object-storage.md)，复现入口见 [tests](../tests/README.md)。脱敏结果见 [oss-test-summary-2026-10-12.json](oss-test-summary-2026-10-12.json)。此前修复结果保留在 [2026-10-11 报告](repair-report-2026-10-11.md)，不将历史检查冒充本轮结果。原始日志、照片、凭据、证书私钥、备份和 kubeconfig 未提交。
