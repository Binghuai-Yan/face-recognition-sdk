# FaceSDK Kubernetes 部署指南

## 快速开始

### 1. 前提条件

- Kubernetes 集群 1.24+
- kubectl 已配置
- (可选) Helm 3.0+
- (可选) Ingress Controller（如 NGINX Ingress）
- (可选) cert-manager（用于自动 TLS 证书）

### 2. 部署步骤

```bash
# 1. 创建命名空间
kubectl apply -f namespace.yaml

# 2. 创建 ConfigMap 和 Secret
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml

# 3. 部署数据库和缓存
kubectl apply -f postgres-deployment.yaml
kubectl apply -f redis-deployment.yaml

# 4. 等待数据库就绪
kubectl wait --for=condition=ready pod -l app=postgres -n facesdk --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n facesdk --timeout=60s

# 5. 部署 CompreFace API
kubectl apply -f compreface-deployment.yaml

# 6. 配置 Ingress（可选）
kubectl apply -f ingress.yaml

# 或使用 Kustomize 一键部署
kubectl apply -k .
```

### 3. 验证部署

```bash
# 查看 Pod 状态
kubectl get pods -n facesdk

# 查看服务
kubectl get svc -n facesdk

# 查看 PVC
kubectl get pvc -n facesdk

# 查看日志
kubectl logs -f deployment/compreface-api -n facesdk

# 端口转发（本地测试）
kubectl port-forward svc/compreface-api 8000:80 -n facesdk
```

## 配置说明

### Secret 管理

生产环境建议使用以下方式管理 Secret：

1. **Sealed Secrets**:
```bash
# 安装 kubeseal
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# 加密 Secret
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml

# 部署加密后的 Secret
kubectl apply -f sealed-secret.yaml
```

2. **External Secrets Operator**:
```bash
# 从外部密钥管理服务（如 AWS Secrets Manager、Azure Key Vault）同步 Secret
```

3. **Vault**:
```bash
# 使用 HashiCorp Vault 管理 Secret
```

### 存储配置

根据集群环境修改 `storageClassName`：

- **AWS EKS**: `gp3` 或 `gp2`
- **Azure AKS**: `managed-csi`
- **GCP GKE**: `standard-rwo`
- **本地集群**: `standard` 或 `hostpath`

### GPU 支持

如需 GPU 加速，修改 `compreface-deployment.yaml`：

```yaml
spec:
  template:
    spec:
      containers:
        - name: compreface-api
          resources:
            limits:
              nvidia.com/gpu: 1  # 请求 1 个 GPU
```

并确保已安装 NVIDIA Device Plugin：
```bash
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml
```

## 运维操作

### 扩容

```bash
# 手动扩容
kubectl scale deployment compreface-api --replicas=5 -n facesdk

# 或使用 HPA
kubectl get hpa -n facesdk
```

### 更新镜像

```bash
# 更新镜像版本
kubectl set image deployment/compreface-api compreface-api=exadel/compreface:1.3.0 -n facesdk

# 查看滚动更新状态
kubectl rollout status deployment/compreface-api -n facesdk

# 回滚
kubectl rollout undo deployment/compreface-api -n facesdk
```

### 备份与恢复

```bash
# 备份 PostgreSQL
kubectl exec -it postgres-0 -n facesdk -- pg_dump -U compreface compreface > backup.sql

# 恢复 PostgreSQL
kubectl exec -i postgres-0 -n facesdk -- psql -U compreface compreface < backup.sql
```

### 监控

```bash
# 查看资源使用
kubectl top pods -n facesdk
kubectl top nodes

# 查看事件
kubectl get events -n facesdk --sort-by='.lastTimestamp'
```

## 故障排查

### Pod 无法启动

```bash
# 查看 Pod 详情
kubectl describe pod <pod-name> -n facesdk

# 查看日志
kubectl logs <pod-name> -n facesdk
kubectl logs <pod-name> -n facesdk --previous
```

### 数据库连接失败

```bash
# 检查网络连通性
kubectl exec -it compreface-api-xxx -n facesdk -- nc -zv postgres 5432

# 检查 Secret
kubectl get secret facesdk-secrets -n facesdk -o yaml
```

### 存储问题

```bash
# 检查 PVC 状态
kubectl get pvc -n facesdk

# 检查 PV
kubectl get pv

# 检查 StorageClass
kubectl get storageclass
```

## 高级配置

### 使用 Helm 部署

```bash
# 添加 Helm Chart 仓库
helm repo add facesdk https://charts.facesdk.io
helm repo update

# 安装
helm install facesdk facesdk/facesdk \
  --namespace facesdk \
  --create-namespace \
  --set compreface.apiKey=your-api-key \
  --set postgres.password=your-db-password
```

### 多环境部署

使用 Kustomize 管理多环境：

```bash
# 开发环境
kubectl apply -k overlays/dev

# 生产环境
kubectl apply -k overlays/prod
```

## 安全建议

1. **启用 RBAC**: 限制 Service Account 权限
2. **网络策略**: 限制 Pod 间通信
3. **Pod 安全策略**: 禁止特权容器
4. **镜像安全**: 使用私有镜像仓库，定期扫描漏洞
5. **TLS**: 启用 Ingress TLS，使用 cert-manager 自动管理证书
