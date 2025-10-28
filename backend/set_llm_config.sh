#!/bin/bash

# 直接设置 LLM 配置

BASE_URL="http://localhost:8000"

# 从图片中看到的配置
API_URL="https://generativelanguage.googleapis.com/v1beta/openai"
API_KEY="AIzaSyAqko3NqGS-GtXhzm8LeiZ3xUEyo_XIqLo"
MODEL="gemini-2.5-pro-preview-06-05"

echo "=========================================="
echo "设置 LLM 配置"
echo "=========================================="
echo ""

# 1. 登录
echo "1. 登录..."
TOKEN=$(curl -s -X POST "${BASE_URL}/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin1234" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ 登录失败"
    exit 1
fi

echo "✅ 登录成功"
echo ""

# 2. 更新配置
echo "2. 更新 LLM 配置..."
echo "  API URL: $API_URL"
echo "  API Key: ${API_KEY:0:20}..."
echo "  Model: $MODEL"
echo ""

UPDATE_RESPONSE=$(curl -s -X PUT "${BASE_URL}/api/llm-config" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"llm_provider_url\": \"${API_URL}\",
    \"llm_provider_api_key\": \"${API_KEY}\",
    \"llm_provider_model\": \"${MODEL}\"
  }")

echo "更新响应:"
echo "$UPDATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPDATE_RESPONSE"
echo ""

# 3. 验证配置
echo "3. 验证配置..."
VERIFY_CONFIG=$(curl -s -X GET "${BASE_URL}/api/llm-config" \
  -H "Authorization: Bearer $TOKEN")

echo "$VERIFY_CONFIG" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, dict):
        print('✅ 配置已更新:')
        print(f'  API URL: {data.get(\"llm_provider_url\", \"未设置\")}')
        print(f'  Model: {data.get(\"llm_provider_model\", \"未设置\")}')
        api_key = data.get(\"llm_provider_api_key\", \"\")
        if api_key:
            print(f'  API Key: {api_key[:20]}...')
    else:
        print('⚠️  配置格式异常')
except Exception as e:
    print(f'错误: {e}')
"

echo ""
echo "✅ 配置完成！"
