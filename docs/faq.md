# FaceSDK 常见问题 (FAQ)

## 部署相关

### Q: 如何修改默认端口？

A: 编辑 `docker-compose/.env` 文件，修改以下配置：
```bash
COMPREFACE_PORT=8000        # API 端口
COMPREFACE_UI_PORT=8001     # UI 端口
POSTGRES_PORT=5432          # 数据库端口
REDIS_PORT=6379             # Redis 端口
```

### Q: 如何启用 GPU 加速？

A: 
1. 确保已安装 NVIDIA Docker 运行时
2. 编辑 `.env` 文件，取消 GPU 配置注释：
```bash
GPU_SUPPORT=resources: reservations: devices: - driver: nvidia count: 1 capabilities: [gpu]
```
3. 重启服务：
```bash
docker-compose down
docker-compose up -d
```

### Q: 如何备份和恢复数据？

A: 使用提供的备份脚本：
```bash
# 备份
cd docker-compose
./backup.sh

# 恢复
./restore.sh ./backups/20240101_120000
```

## API 使用相关

### Q: 相似度阈值如何设置？

A: 推荐阈值：
- **人脸比对（1:1）**: 0.8 - 0.9
- **人脸识别（1:N）**: 0.7 - 0.8
- **高安全场景**: 0.9+
- **宽松场景**: 0.6 - 0.7

### Q: 支持哪些图片格式？

A: 支持格式：
- JPEG/JPG
- PNG
- BMP
- WebP

建议：使用 JPEG 格式，大小不超过 5MB

### Q: 如何处理"未检测到人脸"错误？

A: 可能原因及解决方案：
1. **图片质量问题**：确保光线充足、人脸清晰
2. **人脸角度问题**：尽量使用正脸照片
3. **人脸大小问题**：人脸占图片比例建议在 20%-80%
4. **检测阈值问题**：降低 `det_prob_threshold` 参数

### Q: API 返回 429 错误怎么办？

A: 429 表示请求过于频繁。解决方案：
1. 降低请求频率
2. 实现客户端重试机制（指数退避）
3. 联系管理员调整限流配置

## SDK 使用相关

### Q: Java SDK 如何集成到 Spring Boot？

A: 参考以下配置：
```java
@Configuration
public class FaceSDKConfig {
    @Bean
    public FaceSDKClient faceSDKClient(
            @Value("${facesdk.api-url}") String apiUrl,
            @Value("${facesdk.api-key}") String apiKey) {
        FaceSDK sdk = FaceSDK.builder()
            .apiUrl(apiUrl)
            .apiKey(apiKey)
            .build();
        return sdk.getClient();
    }
}
```

### Q: Python SDK 支持异步吗？

A: 支持，使用 `AsyncFaceSDKClient`：
```python
from facesdk import AsyncFaceSDKClient

async with AsyncFaceSDKClient(api_url="...", api_key="...") as client:
    result = await client.detect("/path/to/image.jpg")
```

### Q: Go SDK 如何处理超时？

A: 使用 context 控制超时：
```go
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

result, err := client.Detect(ctx, "/path/to/image.jpg", nil)
```

## 性能相关

### Q: 预期的 QPS 是多少？

A: 参考性能指标（4 CPU, 8GB RAM）：
- **人脸检测**: 50-100 QPS
- **人脸比对**: 30-50 QPS
- **人脸识别**: 20-40 QPS

启用 GPU 可提升 5-10 倍性能。

### Q: 如何提高识别速度？

A: 优化建议：
1. **使用 Redis 缓存**：缓存热点人脸特征
2. **减小人脸库规模**：按业务分库
3. **降低图片分辨率**：建议 640x480 或更小
4. **使用 GPU 加速**：显著提升性能
5. **水平扩展**：部署多个 API 实例

### Q: 内存占用过高怎么办？

A: 优化措施：
1. 限制工作进程数：`WORKERS=2`
2. 降低并发连接数
3. 增加 Redis 缓存，减少数据库查询
4. 定期重启服务（可选）

## 安全相关

### Q: 如何保护 API Key？

A: 安全措施：
1. **环境变量存储**：不要硬编码在代码中
2. **定期轮换**：定期更换 API Key
3. **访问控制**：限制 API Key 的 IP 访问范围
4. **HTTPS 传输**：生产环境强制使用 HTTPS

### Q: 人脸数据如何加密？

A: 加密方案：
1. **传输加密**：使用 HTTPS/TLS
2. **存储加密**：数据库启用透明数据加密 (TDE)
3. **特征加密**：敏感字段 AES 加密
4. **备份加密**：备份文件加密存储

### Q: 如何符合 GDPR/个人信息保护法？

A: 合规建议：
1. **用户同意**：获取明确的用户授权
2. **数据最小化**：只存储必要的特征数据
3. **数据保留期限**：设置自动删除策略
4. **数据导出**：提供数据导出功能
5. **数据删除**：支持用户删除请求

## 故障排查

### Q: 服务启动失败怎么办？

A: 排查步骤：
1. 检查日志：`docker-compose logs compreface-api`
2. 检查端口冲突：`netstat -tlnp`
3. 检查磁盘空间：`df -h`
4. 检查内存：`free -h`
5. 检查数据库连接：`docker-compose exec postgres pg_isready`

### Q: 数据库连接失败怎么办？

A: 解决方案：
1. 检查数据库服务状态：`docker-compose ps postgres`
2. 检查网络连接：`docker-compose exec compreface-api ping postgres`
3. 检查密码配置：确认 `.env` 文件中的密码正确
4. 检查数据库日志：`docker-compose logs postgres`

### Q: 识别准确率下降怎么办？

A: 排查方法：
1. 检查图片质量：确保光线、清晰度
2. 检查人脸角度：尽量使用正脸
3. 检查阈值设置：调整相似度阈值
4. 更新人脸库：删除低质量人脸，重新采集
5. 检查模型版本：确保使用最新模型

## 升级相关

### Q: 如何升级到最新版本？

A: 升级步骤：
```bash
# 1. 备份数据
cd docker-compose
./backup.sh

# 2. 拉取新版本
docker-compose pull

# 3. 停止服务
docker-compose down

# 4. 启动新版本
docker-compose up -d

# 5. 验证升级
curl http://localhost:8000/api/v1/info
```

### Q: 版本兼容性如何？

A: 兼容性说明：
- **API 版本**: v1 版本保持向后兼容
- **SDK 版本**: 建议 SDK 版本 >= 服务端版本
- **数据库**: 自动迁移，无需手动操作
