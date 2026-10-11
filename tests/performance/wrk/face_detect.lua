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
--   FACESDK_DETECTION_API_KEY - API 密钥
--   TEST_IMAGE_PATH  - 测试图片路径

local api_key = os.getenv("FACESDK_DETECTION_API_KEY")
local test_image = os.getenv("TEST_IMAGE_PATH") or "test_face.jpg"

if not api_key or api_key == "" then error("Set FACESDK_DETECTION_API_KEY") end

-- 读取测试图片
local file = io.open(test_image, "rb")
if not file then
    io.stderr:write("ERROR: Cannot open test image: " .. test_image .. "\n")
    os.exit(1)
end
local image_data = file:read("*a")
file:close()

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
local threads = {}
local tracked_codes = {200, 201, 204, 400, 401, 403, 413, 429, 500, 502, 503, 504}
for _, code in ipairs(tracked_codes) do _G["responses_" .. code] = 0 end
responses_other = 0

function setup(thread)
    table.insert(threads, thread)
end

-- 请求回调
function response(status, headers, body)
    local name = "responses_" .. status
    if _G[name] ~= nil then _G[name] = _G[name] + 1
    else responses_other = responses_other + 1 end
end

-- 数据统计回调
function done(summary, latency, requests)
    local status_codes = {}
    local other = 0
    for _, thread in ipairs(threads) do
        for _, code in ipairs(tracked_codes) do
            status_codes[code] = (status_codes[code] or 0) + (thread:get("responses_" .. code) or 0)
        end
        other = other + (thread:get("responses_other") or 0)
    end
    io.write("\n========== FaceSDK Performance Report ==========\n")
    io.write(string.format("Requests:  %d total, %.2f req/s\n", summary.requests, summary.requests / (summary.duration / 1e6)))
    io.write(string.format("Latency:   min=%.2fms, max=%.2fms, avg=%.2fms, stdev=%.2fms\n",
        latency.min / 1000, latency.max / 1000, latency.mean / 1000, latency.stdev / 1000))
    io.write(string.format("50th:      %.2fms\n", latency:percentile(50) / 1000))
    io.write(string.format("90th:      %.2fms\n", latency:percentile(90) / 1000))
    io.write(string.format("99th:      %.2fms\n", latency:percentile(99) / 1000))
    io.write("\nStatus Codes:\n")
    for code, count in pairs(status_codes) do
        if count > 0 then
            io.write(string.format("  %s: %d (%.1f%%)\n", code, count, count / math.max(summary.requests, 1) * 100))
        end
    end
    if other > 0 then io.write(string.format("  other: %d\n", other)) end
    io.write("================================================\n")
    local errors = summary.errors.connect + summary.errors.read + summary.errors.write + summary.errors.timeout
    local successes = (status_codes[200] or 0) + (status_codes[201] or 0) + (status_codes[204] or 0)
    if errors > 0 or summary.requests == 0 or successes ~= summary.requests then os.exit(1) end
end
