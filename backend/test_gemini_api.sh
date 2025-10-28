#!/bin/bash

# 测试 Gemini API 是否可用

API_KEY="AIzaSyAqko3NqGS-GtXhzm8LeiZ3xUEyo_XIqLo"
API_URL="https://generativelanguage.googleapis.com/v1beta/openai"

echo "=========================================="
echo "测试 Gemini API"
echo "=========================================="
echo ""
echo "API Key: ${API_KEY:0:20}..."
echo "API URL: $API_URL"
echo ""

# 测试 1: 简单的文本生成
echo "1. 测试简单文本生成..."
RESPONSE=$(curl -s -X POST "${API_URL}/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{
    "model": "gemini-2.5-pro-preview-06-05",
    "messages": [
      {
        "role": "user",
        "content": "请用一句话介绍人工智能。"
      }
    ],
    "max_tokens": 100
  }')

echo "响应:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# 检查是否成功
if echo "$RESPONSE" | grep -q '"choices"'; then
    echo "✅ API 调用成功！"
    echo ""
    echo "生成的内容:"
    echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'choices' in data and len(data['choices']) > 0:
        content = data['choices'][0]['message']['content']
        print(content)
    else:
        print('未找到生成内容')
except Exception as e:
    print(f'解析错误: {e}')
"
elif echo "$RESPONSE" | grep -q '"error"'; then
    echo "❌ API 调用失败"
    echo ""
    echo "错误信息:"
    echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'error' in data:
        error = data['error']
        print(f\"错误代码: {error.get('code', 'N/A')}\")
        print(f\"错误消息: {error.get('message', 'N/A')}\")
        print(f\"状态: {error.get('status', 'N/A')}\")
except Exception as e:
    print(f'解析错误: {e}')
"
else
    echo "⚠️  未知响应格式"
fi

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
