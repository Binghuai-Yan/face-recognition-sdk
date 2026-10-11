# 通用 OSS 与默认 RustFS

主 Docker / Kubernetes 部署默认将新增人脸的原图存到 RustFS 1.0.1。OSS 网关使用标准 S3 SigV4 协议，支持配置任意提供相应 S3 兼容接口的对象存储。这里的 OSS 泛指对象存储；阿里云 OSS、腾讯 COS 等提供商的原生专属协议未实现，不能仅因填写其域名便假定兼容。

CompreFace 1.2 没有原生可配置 OSS 图片接口，因此由本仓库网关保存原图，再原样转发注册请求。CompreFace 设置 `SAVE_IMAGES_TO_DB=false`，PostgreSQL 继续保留 Subject、image_id 和 embedding。检测、比对、搜索及四种 SDK 的协议保持兼容，所有客户请求和 UI 的 API 代理都必须指向网关。不要对外开放 CompreFace 内部端口。

## 默认 RustFS

复制 docker-compose/.env.example，填写随机 POSTGRES_PASSWORD、RUSTFS_SECRET_KEY，然后运行 `docker compose up -d`。第一次启动从 services/oss-gateway 构建镜像。OSS 凭据为空时使用 RustFS 的 ID/密码。RustFS 服务、网关和数据库分别持久化 rustfs-data、oss-journal、postgres-data。

公开服务是 localhost:8000。RustFS S3/控制台默认仅绑定 localhost:9000/9001；bucket 不设置公开 ACL。图片通过 `GET /api/v1/recognition/faces/{image_id}/img` 与 x-api-key 授权读取，兼容 CompreFace 的 static 图片路由。旧 static URL 含服务密钥，网关禁用访问日志；在前置代理中也应避免记录含密钥的路径，优先使用 header 路由。

## 外部 S3 兼容对象存储

例如 AWS S3 的已有私有 bucket：

```dotenv
OSS_ENDPOINT=https://s3.eu-west-1.amazonaws.com
OSS_BUCKET=your-private-face-images
OSS_REGION=eu-west-1
OSS_ACCESS_KEY_ID=your-access-key-id
OSS_SECRET_ACCESS_KEY=your-secret-access-key
OSS_SESSION_TOKEN=
OSS_ADDRESSING_STYLE=virtual
OSS_AUTO_CREATE_BUCKET=false
OSS_PREFIX=faces
```

```sh
docker compose -f docker-compose.yml -f docker-compose.external-oss.yml up -d
```

这会关闭本地 RustFS。私有 S3 服务通常使用 `OSS_ADDRESSING_STYLE=path`；也支持 virtual 和 auto。Endpoint 应是该服务的 API endpoint。region 必须符合提供商签名要求。更换 endpoint/bucket/prefix 不会自动迁移旧对象或修改 journal；应先停止写入，迁移对象并验证关联，再切换配置。

外部 bucket 建议预先创建，授予网关该 bucket 的 HeadBucket 所需权限及指定 prefix 的 PutObject、GetObject、DeleteObject；启用自动建桶还需要 CreateBucket。测试工具额外需要 ListBucket。不要使用公开 bucket 或把存储凭据交给 SDK / 浏览器。支持临时凭据 OSS_SESSION_TOKEN，过期后需更新部署环境。

TLS 默认验证证书。自有 CA：将 CA 文件只读挂载到网关，并设置 OSS_CA_BUNDLE 的容器内绝对路径；没有关闭 TLS 验证的选项。内网 RustFS 默认通过 Docker / 集群内 HTTP 连接，外部 endpoint 应配置 HTTPS。对象与备份加密由存储提供商和部署环境配置。

## 写入、删除和恢复

上传先将原图保存至 OSS，失败返回 503，不注册后端人脸。后端明确拒绝注册时清理暂存对象。后端提交成功但网络响应丢失时，journal 保留上传意图；下次同服务的认证请求用上传前后的 image_id 恢复关联。客户端应查询人脸列表确认结果，避免直接重试非幂等注册。若同时有绕过网关的写入产生多个新增 image_id，恢复返回 503，须人工对账。

超时并不证明后台操作已结束。若尚未观察到新增 image_id，或未决删除的记录仍存在，网关保留原图和意图，允许查询、读图、识别和单图验证，后续写入返回 503。后台延迟提交后，下一次认证读取自动恢复；若后台最终没有提交，需要管理员核对后台、journal 和对象后手工解除未决意图，不能仅凭一次空列表清理原图。

超时的空集合删除没有可核对的 image_id，须管理员确认完成后解除意图。未决操作期间，旧数据库图片仍可读取，但暂停首次读取时的 OSS 迁移，避免为正在删除的旧图片创建孤立对象。

人工核对时先备份 journal，并停止写入、确认旧后台请求已终止（可在维护窗口重启后台后再核对）。按 journal 的 namespace、Subject 和 previous_ids 查询相应服务的当前记录。已确认未提交的上传可由管理员使用 Journal.discard_upload(operation_id) 转成持久化对象清理任务；已确认没有删除的操作使用 Journal.discard_delete(operation_id) 解除意图；已确认删除的 ID 使用 Journal.finish_delete(operation_id, deleted_ids) 排队清理。操作应在网关停止时通过其 Python 模块针对备份过的 SQLite 执行，恢复后由 outbox 清理对象。无法确定关联的上传应保留原图，先完成对账。

网关持久化待删除任务，再删除后端人脸。后端删除成功时立即撤销图片读取。若 OSS 删除失败，响应 header `x-facesdk-object-delete: pending` 表示待物理清理，后台每 5 秒重试，重启后继续；completed 表示当前服务没有待删除任务。后端删除响应丢失时，下一次同服务认证请求确认后台记录后恢复清理。没有保存服务 API Key 到 journal，因此此类未决操作需要调用者再次认证。

已有数据库原图在首次授权读取时复制到 OSS；不会自动清空旧数据库图片。读取已删除 image_id 或其他服务的图片返回 404。管理端删除整个应用/服务或直接修改数据库不经过图片删除队列，可能留下私有孤立对象，需单独对账。服务密钥轮换会改变存储 namespace，必须迁移对应 journal 映射；本版没有自动轮换迁移接口。

SQLite journal 和按服务的锁要求单进程、单副本，不支持多 worker 或横向扩容。生产扩容需共享事务数据库及分布式协调。网关默认限制请求体 10MiB（OSS_MAX_BODY_BYTES），CompreFace 自身也有文件限制；图像解码会验证格式及 Pillow 的像素限制。公开依赖健康同时检查数据库/Core、journal 与 OSS，独立 `/health/live` 不受存储停机影响。

## 备份和验证

必须同步保留 PostgreSQL、私有 bucket 的全部对象、SQLite journal。停止网关写入后备份数据库和对象；journal 用 SQLite backup API 或停止网关后复制整个数据卷（不能仅复制正在写入的 storage.sqlite3 而遗漏 WAL）。恢复三者并先核对授权图片读取与搜索，再恢复业务流量。遗失 journal 时，新图片不会从禁用图片保存的 PostgreSQL 恢复，必须恢复 journal 备份。

默认存储不依赖 MinIO。测试入口包含网关和标准 S3 请求测试；`--oss-live` 直接验证真实 RustFS 对象字节、私有访问、跨服务隔离、multipart/base64、拒绝上传及批量/Subject 删除，见 [测试步骤](../tests/README.md)。AWS 等外部厂商的生产账号未在本地测试，示例配置不等同于厂商认证。

本轮结果见 [OSS 测试报告](oss-report-2026-10-12.md) 与 [脱敏汇总](oss-test-summary-2026-10-12.json)。
