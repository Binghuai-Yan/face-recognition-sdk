# FaceSDK Docker Compose 部署指南

## 快速开始

### 1. 环境准备

确保已安装以下软件：
- Docker Engine 20.10+
- Docker Compose 2.0+
- (可选) NVIDIA Docker 运行时（用于 GPU 加速）

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，修改以下关键配置：
# - COMPREFACE_API_KEY: 设置强密码
# - POSTGRES_PASSWORD: 设置数据库密码
# - MINIO_ROOT_PASSWORD: 设置对象存储密码
# - GRAFANA_ADMIN_PASSWORD: 设置监控面板密码
```

### 3. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f compreface-api
```

### 4. 验证部署

```bash
# 检查 API 健康状态
curl http://localhost:8000/health

# 检查 API 版本
curl http://localhost:8000/api/v1/info
```

## 服务说明

| 服务 | 端口 | 说明 |
|------|------|------|
| compreface-api | 8000 | 人脸识别核心 API |
| compreface-ui | 8001 | Web 管理界面 |
| postgres | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis 缓存 |
| minio | 9000/9001 | 对象存储 |
| nginx | 80/443 | 反向代理 |
| prometheus | 9090 | 监控指标采集 |
| grafana | 3000 | 监控仪表盘 |

## 常用命令

```bash
# 停止服务
docker-compose down

# 停止并删除数据卷（谨慎使用）
docker-compose down -v

# 重启单个服务
docker-compose restart compreface-api

# 查看服务日志
docker-compose logs -f [service-name]

# 进入容器
docker-compose exec compreface-api sh

# 更新镜像
docker-compose pull
docker-compose up -d
```

## GPU 加速配置

### NVIDIA GPU

1. 安装 NVIDIA Docker 运行时：
```bash
# Ubuntu
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

2. 启用 GPU 支持：
```bash
# 编辑 .env 文件，取消 GPU_SUPPORT 的注释
GPU_SUPPORT=resources: reservations: devices: - driver: nvidia count: 1 capabilities: [gpu]
```

3. 重启服务：
```bash
docker-compose up -d
```

## 数据备份

### 备份所有数据

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# 备份 PostgreSQL
docker-compose exec -T postgres pg_dump -U compreface compreface > $BACKUP_DIR/postgres.sql

# 备份 Redis
docker-compose exec -T redis redis-cli BGSAVE
sleep 2
docker cp facesdk-redis:/data/dump.rdb $BACKUP_DIR/redis.rdb

# 备份 MinIO
docker run --rm -v facesdk_minio-data:/data -v $(pwd)/$BACKUP_DIR:/backup alpine tar czf /backup/minio.tar.gz -C /data .

echo "Backup completed: $BACKUP_DIR"
```

### 恢复数据

```bash
#!/bin/bash
# restore.sh

BACKUP_DIR=$1

# 恢复 PostgreSQL
docker-compose exec -T postgres psql -U compreface compreface < $BACKUP_DIR/postgres.sql

# 恢复 Redis
docker cp $BACKUP_DIR/redis.rdb facesdk-redis:/data/dump.rdb
docker-compose restart redis

# 恢复 MinIO
docker run --rm -v facesdk_minio-data:/data -v $(pwd)/$BACKUP_DIR:/backup alpine sh -c "cd /data && tar xzf /backup/minio.tar.gz"
docker-compose restart minio
```

## 故障排查

### 服务无法启动

1. 检查端口冲突：
```bash
netstat -tlnp | grep -E '8000|5432|6379|9000'
```

2. 检查日志：
```bash
docker-compose logs compreface-api
```

3. 检查资源限制：
```bash
docker stats
```

### 数据库连接失败

1. 检查 PostgreSQL 健康状态：
```bash
docker-compose exec postgres pg_isready -U compreface
```

2. 检查网络连接：
```bash
docker-compose exec compreface-api ping postgres
```

### 性能问题

1. 检查资源使用情况：
```bash
docker stats
```

2. 调整 WORKERS 和 THREADS 参数
3. 启用 GPU 加速
4. 增加 Redis 缓存大小

## 安全建议

1. **修改默认密码**：所有默认密码都应在生产环境中修改
2. **启用 HTTPS**：配置 SSL 证书
3. **限制网络访问**：使用防火墙限制端口访问
4. **定期备份**：设置自动备份任务
5. **更新镜像**：定期更新到最新版本

## 安全注意事项

- 复制 `.env.example` 为 `.env` 并修改配置值
- **切勿将 `.env` 文件提交到版本控制系统**
- 生产环境必须修改所有默认密码
- 建议使用 `openssl rand -base64 32` 生成强随机密钥

## 升级指南

```bash
# 1. 备份数据
./backup.sh

# 2. 拉取新版本镜像
docker-compose pull

# 3. 停止服务
docker-compose down

# 4. 启动新版本
docker-compose up -d

# 5. 验证升级
curl http://localhost:8000/api/v1/info
```
