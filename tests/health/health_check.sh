#!/bin/bash
# File: facesdk/tests/health/health_check.sh
# Copyright (c) 2024 FaceSDK Contributors
# MIT License
#
# FaceSDK Health Check Script

set -e

# 配置
API_URL="${FACESDK_API_URL:-http://localhost:8000}"
API_KEY="${FACESDK_API_KEY:-your-api-key}"
TIMEOUT=10

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 HTTP 服务
check_http() {
    local url=$1
    local name=$2
    
    log_info "Checking $name..."
    
    if curl -sf --max-time $TIMEOUT "$url" > /dev/null 2>&1; then
        log_info "$name is healthy"
        return 0
    else
        log_error "$name is not responding"
        return 1
    fi
}

# 检查 API 健康状态
check_api_health() {
    log_info "Checking FaceSDK API health..."
    
    response=$(curl -sf --max-time $TIMEOUT \
        -H "x-api-key: $API_KEY" \
        "$API_URL/health" 2>/dev/null || echo "")
    
    if [ -z "$response" ]; then
        log_error "API health check failed - no response"
        return 1
    fi
    
    if echo "$response" | grep -q '"status".*"UP"'; then
        log_info "API is healthy"
        return 0
    else
        log_error "API is not healthy: $response"
        return 1
    fi
}

# 检查 API 版本
check_api_version() {
    log_info "Checking FaceSDK API version..."
    
    response=$(curl -sf --max-time $TIMEOUT \
        -H "x-api-key: $API_KEY" \
        "$API_URL/api/v1/info" 2>/dev/null || echo "")
    
    if [ -n "$response" ]; then
        log_info "API Info: $response"
        return 0
    else
        log_warn "Could not retrieve API version"
        return 1
    fi
}

# 检查数据库连接
check_database() {
    log_info "Checking database connection..."
    
    # 尝试列出现有 subjects 来验证数据库连接
    response=$(curl -sf --max-time $TIMEOUT \
        -H "x-api-key: $API_KEY" \
        "$API_URL/api/v1/recognition/subjects" 2>/dev/null || echo "")
    
    if [ -n "$response" ]; then
        log_info "Database connection is healthy"
        return 0
    else
        log_error "Database connection failed"
        return 1
    fi
}

# 主函数
main() {
    log_info "Starting FaceSDK health check..."
    log_info "API URL: $API_URL"
    
    local exit_code=0
    
    # 检查基本连通性
    if ! check_http "$API_URL" "FaceSDK API"; then
        exit_code=1
    fi
    
    # 检查健康端点
    if ! check_api_health; then
        exit_code=1
    fi
    
    # 检查 API 版本
    check_api_version || true
    
    # 检查数据库
    if ! check_database; then
        exit_code=1
    fi
    
    if [ $exit_code -eq 0 ]; then
        log_info "All health checks passed!"
    else
        log_error "Some health checks failed!"
    fi
    
    exit $exit_code
}

# 运行主函数
main "$@"
