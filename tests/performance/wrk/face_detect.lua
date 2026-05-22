-- File: facesdk/tests/performance/wrk/face_detect.lua
-- Copyright (c) 2024 FaceSDK Contributors
-- MIT License
--
-- wrk Lua 脚本 - 人脸检测性能测试
--
-- 使用方法:
--   wrk -t4 -c10 -d30s -s face_detect.lua http://localhost:8000/api/v1/detection/detect
--
-- 环境变量:
--   FACE_SDK_API_KEY - API 密钥
--   TEST_IMAGE_PATH  - 测试图片路径

local api_key = os.getenv("FACE_SDK_API_KEY") or "test-api-key"
local test_image = os.getenv("TEST_IMAGE_PATH") or "test_face.jpg"

-- 读取测试图片
local file = io.open(test_image, "rb")
if not file then
    io.stderr:write("ERROR: Cannot open test image: " .. test_image .. "\n")
    os.exit(1)
end
local image_data = file:read("*a")
file.close()

-- 构建 multipart/form-data 请求体
local boundary = "----FaceSDKBoundary" .. math.random(100000, 999999)
local body = "--" .. boundary .. "\r\n"
    .. 'Content-Disposition: form-data; name="file"; filename="test_face.jpg"\r\n'
    .. "Content-Type: image/jpeg\r\n\r\n"
    .. image_data .. "\r\n"
    .. "--" .. boundary .. "--\r\n"

local content_type = "multipart/form-data; boundary=" .. boundary

-- 请求初始化
wrk.method = "POST"
wrk.headers["Content-Type"] = content_type
wrk.headers["x-api-key"] = api_key
wrk.body = body
wrk.headers["Content-Length"] = #body

-- 统计数据
local status_codes = {}
local total_latency = 0
local total_requests = 0

-- 请求回调
function response(status, headers, body)
    status_codes[status] = (status_codes[status] or 0) + 1
end

-- 数据统计回调
function done(summary, latency, requests)
    io.write("\n========== FaceSDK Performance Report ==========\n")
    io.write(string.format("Requests:  %d total, %.2f req/s\n", summary.requests, summary.requests / (summary.duration / 1e6)))
    io.write(string.format("Latency:   min=%.2fms, max=%.2fms, avg=%.2fms, stdev=%.2fms\n",
        latency.min / 1000, latency.max / 1000, latency.mean / 1000, latency.stdev / 1000))
    io.write(string.format("50th:      %.2fms\n", latency:percentile(50) / 1000))
    io.write(string.format("90th:      %.2fms\n", latency:percentile(90) / 1000))
    io.write(string.format("99th:      %.2fms\n", latency:percentile(99) / 1000))
    io.write("\nStatus Codes:\n")
    for code, count in pairs(status_codes) do
        io.write(string.format("  %s: %d (%.1f%%)\n", code, count, count / summary.requests * 100))
    end
    io.write("================================================\n")
end
