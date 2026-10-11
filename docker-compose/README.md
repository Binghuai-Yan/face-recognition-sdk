# Docker Compose 部署

需要 Docker Engine（Linux 容器）和 Compose v2，至少为 CompreFace 提供约 8GB 内存。默认仅启动 CompreFace 1.2 全功能镜像与 PostgreSQL 15。

```sh
cp .env.example .env
# 替换 POSTGRES_PASSWORD 及要启用的可选服务密码
docker compose config --quiet
docker compose up -d
docker compose ps
```

访问 `http://localhost:8000` 创建账号、应用和三种服务。默认绑定 127.0.0.1；远程访问应配置 TLS gateway。数据库使用 EXTERNAL_DB、JDBC URL 及独立账号密码，通过 init-scripts 创建 uuid-ossp，表由 CompreFace admin Liquibase 初始化。

PostgreSQL 数据存储在命名卷 postgres-data。更改 .env 的密码不会自动更改已有数据库角色密码。升级前应备份数据库；`docker compose down` 保留卷，添加 `-v` 会删除数据。

## 可选 profiles

| profile | 作用 | 准备 |
|---|---|---|
| gateway | Nginx HTTPS 与 API 限流 | 放置 nginx/ssl/fullchain.pem 和 privkey.pem，开放 80/443 |
| monitoring | Prometheus、blackbox、PG exporter、Alertmanager、Grafana | 设置 Grafana 密码；界面端口仅绑定 localhost |
| cache | 应用自用 Redis | 设置 REDIS_PASSWORD；不对宿主机暴露 Redis |
| storage | 应用自用 MinIO | 设置 MINIO_ROOT_PASSWORD；端口仅绑定 localhost |

例如 `docker compose --profile monitoring up -d`。Redis/MinIO 并未接入 CompreFace；CompreFace 将图片和特征保存到 PostgreSQL。Alertmanager 默认仅在本地显示告警，需要另行配置通知接收器。

healthcheck 解析内部 Java 8080 `/api/v1/consistence/status` 的 JSON 并要求 OK，检查数据库/Core，首次加载模型可能需要几分钟。可在根目录运行 `bash tests/health/health_check.sh`。

## 隔离测试环境

```sh
docker compose -p facesdk-test -f docker-compose.test.yml up -d
```

测试配置使用镜像内置数据库，卷挂载 `/var/lib/postgresql/data`；通过 COMPREFACE_TEST_PORT 避免端口冲突。测试卷同样会保留数据。该环境与主配置不要同时使用相同的端口。真实模型测试见 [测试文档](../tests/README.md)。
