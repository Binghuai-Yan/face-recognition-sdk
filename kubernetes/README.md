# Kubernetes 部署

默认部署单个 CompreFace 1.2、PostgreSQL、RustFS 和 OSS 网关。需要默认 StorageClass、Ingress Nginx；示例域名须替换。网关使用单个 worker 和单副本 Recreate，SQLite journal 与 RustFS 各使用独立 RWO PVC。

```sh
kubectl apply -f namespace.yaml
kubectl -n facesdk create secret generic facesdk-secrets \
  --from-literal=POSTGRES_PASSWORD='<随机数据库密码>' \
  --from-literal=OSS_ACCESS_KEY_ID='<对象存储访问 ID>' \
  --from-literal=OSS_SECRET_ACCESS_KEY='<随机对象存储密码>'
# 构建并推送到你的容器仓库，在 kustomization.yaml 设置对应的 newName/newTag
docker build -t YOUR_REGISTRY/facesdk-oss-gateway:1.0.0 ../services/oss-gateway
docker push YOUR_REGISTRY/facesdk-oss-gateway:1.0.0
# 修改 ingress.yaml 的域名，并通过 cert-manager 或人工创建 facesdk-tls 证书 Secret
kubectl kustomize .
kubectl apply -k .
```

`secret.yaml` 仅作为格式示例，不包含在默认 kustomization 中，不要直接使用占位密码。默认只提供 ClusterIP，API/UI 两个公网域名均经 TLS Ingress 转发至 oss-gateway:8080，网关代理管理 UI；compreface-api:80 是内部后端。自定义 Vue 管理界面需单独构建部署，其 API 代理也必须指向网关。

外部 S3 兼容 OSS：修改 facesdk-config 的 OSS_ENDPOINT、OSS_BUCKET、OSS_REGION、OSS_ADDRESSING_STYLE，设置 OSS_AUTO_CREATE_BUCKET=false，并使用外部凭据。删除 kustomization.yaml 的 rustfs-deployment.yaml resource。自有 CA 可通过只读 Secret/ConfigMap 文件挂载并设置 OSS_CA_BUNDLE。详见 [配置和备份](../docs/object-storage.md)。

数据库凭据同时供 API/admin 和外部 PostgreSQL 使用。POSTGRES_URL 是 JDBC URL，EXTERNAL_DB=true。数据库通过 ConfigMap 初始化 uuid-ossp，PVC 挂载 `/var/lib/postgresql/data`。升级已有数据库时初始化脚本不会再次执行，需确认扩展存在。

API 不使用共享 RWO 数据卷。startupProbe 最多允许约十分钟加载模型；readinessProbe 解析 Java 8080 的真实依赖健康 JSON，livenessProbe 检查 Java 进程端口，数据库短暂故障不会重启所有 API。数据库采用 Recreate 以避免两个 Pod 同时写同一数据卷。

本版停止将版本标签注入 Deployment selector，以便后续改版本标签。升级旧 kustomization 创建的集群时，若已有 selector 包含 app.kubernetes.io/version 等标签，Kubernetes 会拒绝修改这个不可变字段；应先备份，在维护窗口保留 PVC 并重建对应 Deployment，再 apply 新配置。该过程会中断服务，PVC 应继续保留。

Redis 是应用自用的可选组件，未在默认 kustomization 中启用。需要时先给 facesdk-secrets 增加 REDIS_PASSWORD，再单独部署 redis-deployment.yaml；服务仅在集群内暴露，并开启认证。

正式扩容需要验证 CompreFace admin 初始化、模型内存、并发写入和数据库容量。本轮在单节点 kind 1.31 集群验证了真实模型、Ingress TLS、数据库停机时 readiness 撤销及恢复、liveness 不重启 API 和 PVC 数据保留；结果见 [测试报告](../docs/repair-report-2026-10-11.md)。它不替代多节点或生产存储灾备验证。复现步骤见 [tests](../tests/README.md)。
