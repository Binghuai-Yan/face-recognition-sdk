# Kubernetes 部署

默认部署单个全功能 CompreFace 1.2 Pod 与单个 PostgreSQL。需要可用的默认 StorageClass、Ingress Nginx；示例域名须替换。此配置没有数据库高可用，未默认启用 API 水平扩缩容。

```sh
kubectl apply -f namespace.yaml
kubectl -n facesdk create secret generic facesdk-secrets --from-literal=POSTGRES_PASSWORD='<随机数据库密码>'
# 修改 ingress.yaml 的域名，并通过 cert-manager 或人工创建 facesdk-tls 证书 Secret
kubectl kustomize .
kubectl apply -k .
```

`secret.yaml` 仅作为格式示例，不包含在默认 kustomization 中，不要直接使用占位密码。默认只提供 ClusterIP，公网流量经 TLS Ingress。compreface-ui 和 compreface-api 指向同一个镜像内置 Nginx 的 80 端口；自定义 Vue 管理界面需要单独构建部署。

数据库凭据同时供 API/admin 和外部 PostgreSQL 使用。POSTGRES_URL 是 JDBC URL，EXTERNAL_DB=true。数据库通过 ConfigMap 初始化 uuid-ossp，PVC 挂载 `/var/lib/postgresql/data`。升级已有数据库时初始化脚本不会再次执行，需确认扩展存在。

API 不使用共享 RWO 数据卷。startupProbe 最多允许约十分钟加载模型；readinessProbe 解析 Java 8080 的真实依赖健康 JSON，livenessProbe 检查 Java 进程端口，数据库短暂故障不会重启所有 API。数据库采用 Recreate 以避免两个 Pod 同时写同一数据卷。

Redis 是应用自用的可选组件，未在默认 kustomization 中启用。需要时先给 facesdk-secrets 增加 REDIS_PASSWORD，再单独部署 redis-deployment.yaml；服务仅在集群内暴露，并开启认证。

正式扩容需要验证 CompreFace admin 初始化、模型内存、并发写入和数据库容量。本轮在单节点 kind 1.31 集群验证了真实模型、Ingress TLS、数据库停机时 readiness 撤销及恢复、liveness 不重启 API 和 PVC 数据保留；结果见 [测试报告](../docs/repair-report-2026-10-11.md)。它不替代多节点或生产存储灾备验证。复现步骤见 [tests](../tests/README.md)。
