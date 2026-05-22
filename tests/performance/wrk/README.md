# wrk 性能测试脚本

## 安装 wrk

```bash
# Ubuntu/Debian
sudo apt install wrk

# macOS
brew install wrk

# Windows (通过 WSL)
wsl sudo apt install wrk
```

## 使用方法

### 人脸检测性能测试

```bash
# 设置环境变量
export FACE_SDK_API_KEY="your-api-key"
export TEST_IMAGE_PATH="path/to/test_face.jpg"

# 运行测试（4线程，10连接，持续30秒）
wrk -t4 -c10 -d30s -s face_detect.lua http://localhost:8000/api/v1/detection/detect

# 高并发测试（8线程，50连接，持续60秒）
wrk -t8 -c50 -d60s -s face_detect.lua http://localhost:8000/api/v1/detection/detect
```

### 参数说明

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| -t | 线程数 | CPU 核心数 |
| -c | 连接数 | 根据预期并发量 |
| -d | 测试持续时间 | 30s-120s |
| -s | Lua 脚本路径 | face_detect.lua |

## 注意事项

- 测试前确保 FaceSDK 服务已启动
- 测试图片建议使用真实人脸照片（正面、光线充足）
- 建议先低并发测试，逐步增加并发量
- 关注 P99 延迟指标，确保不超过 SLA 要求
