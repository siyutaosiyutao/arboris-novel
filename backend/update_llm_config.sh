#!/bin/bash

# 更新 LLM 配置脚本

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "更新 LLM 配置"
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

# 2. 获取当前配置
echo "2. 获取当前 LLM 配置..."
CURRENT_CONFIG=$(curl -s -X GET "${BASE_URL}/api/admin/llm-configs" \
  -H "Authorization: Bearer $TOKEN")

echo "当前配置:"
echo "$CURRENT_CONFIG" | python3 -m json.tool 2>/dev/null || echo "$CURRENT_CONFIG"
echo ""

# 3. 更新配置
echo "3. 更新 LLM 配置..."
echo "请输入以下信息："
echo ""

read -p "API URL (默认: https://generativelanguage.googleapis.com/v1beta/openai): " API_URL
API_URL=${API_URL:-"https://generativelanguage.googleapis.com/v1beta/openai"}

read -p "API Key: " API_KEY

read -p "Model (默认: gemini-2.5-pro-preview-06-05): " MODEL
MODEL=${MODEL:-"gemini-2.5-pro-preview-06-05"}

echo ""
echo "配置信息:"
echo "  API URL: $API_URL"
echo "  API Key: ${API_KEY:0:20}..."
echo "  Model: $MODEL"
echo ""

read -p "确认更新配置？(y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "取消更新"
    exit 0
fi

# 更新配置
UPDATE_RESPONSE=$(curl -s -X PUT "${BASE_URL}/api/admin/llm-configs/default" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"api_base_url\": \"${API_URL}\",
    \"api_key\": \"${API_KEY}\",
    \"model_name\": \"${MODEL}\"
  }")

echo ""
echo "更新响应:"
echo "$UPDATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPDATE_RESPONSE"
echo ""

# 4. 验证配置
echo "4. 验证配置..."
VERIFY_CONFIG=$(curl -s -X GET "${BASE_URL}/api/admin/llm-configs" \
  -H "Authorization: Bearer $TOKEN")

echo "更新后的配置:"
echo "$VERIFY_CONFIG" | python3 -m json.tool
echo ""

echo "✅ 配置更新完成！"
