# Docker Compose 部署

需要 Docker Engine（Linux 容器）和 Compose v2，至少为 CompreFace 提供约 8GB 内存。默认启动 CompreFace 1.2、PostgreSQL 15、RustFS 1.0.1 和从源码构建的 OSS 网关。

```sh
cp .env.example .env
# 替换 POSTGRES_PASSWORD、RUSTFS_SECRET_KEY 及可选服务密码
docker compose config --quiet
docker compose up -d
docker compose ps
```

访问 `http://localhost:8000` 创建账号、应用和三种服务。默认绑定 127.0.0.1；远程访问应配置 TLS gateway。数据库使用 EXTERNAL_DB、JDBC URL 及独立账号密码，通过 init-scripts 创建 uuid-ossp，表由 CompreFace admin Liquibase 初始化。

原图保存到 rustfs-data，身份与特征保存在 postgres-data，图片关联和待删除任务保存在 oss-journal。必须共同备份三者。更改 .env 的密码不会自动更改已有数据库角色密码。`docker compose down` 保留卷，添加 `-v` 会删除数据。图片通过网关授权读取，bucket 保持私有；RustFS 9000/9001 管理端口仅绑定 localhost。

接入外部 S3 兼容 OSS 时，配置 OSS_ENDPOINT、OSS_BUCKET、OSS_REGION、OSS_ACCESS_KEY_ID 和 OSS_SECRET_ACCESS_KEY，然后使用 `docker compose -f docker-compose.yml -f docker-compose.external-oss.yml up -d`。该覆盖配置不启动 RustFS。完整示例、权限、迁移和恢复限制见 [对象存储](../docs/object-storage.md)。

## 可选 profiles

| profile | 作用 | 准备 |
|---|---|---|
| gateway | Nginx HTTPS 与 API 限流 | 放置 nginx/ssl/fullchain.pem 和 privkey.pem，开放 80/443 |
| monitoring | Prometheus、blackbox、PG exporter、Alertmanager、Grafana | 设置 Grafana 密码；界面端口仅绑定 localhost |
| cache | 应用自用 Redis | 设置 REDIS_PASSWORD；不对宿主机暴露 Redis |

例如 `docker compose --profile monitoring up -d`。Redis 用于应用集成。Alertmanager 默认仅在本地显示告警，需要另行配置通知接收器。

CompreFace healthcheck 检查数据库/Core。公开网关的 `/api/v1/consistence/status` 同时检查对象存储和 journal，全部正常才返回 OK；首次加载模型可能需要几分钟。可在根目录运行 `bash tests/health/health_check.sh`。

## 隔离测试环境

```sh
docker compose -p facesdk-test -f docker-compose.test.yml up -d
```

此兼容测试配置使用镜像内置数据库和图片存储，不包含 OSS 网关，卷挂载 `/var/lib/postgresql/data`；通过 COMPREFACE_TEST_PORT 避免端口冲突。验证 OSS 必须使用主配置和 `--oss-live`，见 [测试文档](../tests/README.md)。
