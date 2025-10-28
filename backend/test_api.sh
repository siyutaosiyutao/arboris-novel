#!/bin/bash

# 自动生成器 API 测试脚本

BASE_URL="http://localhost:8000"
TOKEN=""

echo "=========================================="
echo "自动生成器 API 功能测试"
echo "=========================================="
echo ""

# 1. 登录获取 token
echo "1. 测试登录..."
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123")

echo "登录响应: $LOGIN_RESPONSE"
TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ 登录失败，无法获取 token"
    exit 1
fi

echo "✅ 登录成功"
echo "Token: ${TOKEN:0:50}..."
echo ""

# 2. 获取自动生成器任务列表
echo "2. 测试获取任务列表..."
TASKS_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks" \
  -H "Authorization: Bearer $TOKEN")

echo "任务列表响应: $TASKS_RESPONSE"
echo ""

# 3. 创建新的自动生成器任务
echo "3. 测试创建新任务..."
CREATE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试任务-'$(date +%s)'",
    "description": "这是一个API测试任务",
    "schedule_type": "daily",
    "schedule_time": "09:00",
    "novel_count": 3,
    "auto_publish": false,
    "config": {
      "genre": "都市",
      "style": "轻松",
      "length": "短篇"
    }
  }')

echo "创建任务响应: $CREATE_RESPONSE"
TASK_ID=$(echo $CREATE_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

if [ -z "$TASK_ID" ]; then
    echo "❌ 创建任务失败"
else
    echo "✅ 任务创建成功，ID: $TASK_ID"
fi
echo ""

# 4. 获取任务详情
if [ ! -z "$TASK_ID" ]; then
    echo "4. 测试获取任务详情..."
    TASK_DETAIL=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "任务详情: $TASK_DETAIL"
    echo ""
fi

# 5. 更新任务
if [ ! -z "$TASK_ID" ]; then
    echo "5. 测试更新任务..."
    UPDATE_RESPONSE=$(curl -s -X PUT "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "更新后的测试任务",
        "description": "任务已更新",
        "schedule_type": "weekly",
        "schedule_time": "10:00",
        "novel_count": 5,
        "auto_publish": true
      }')
    
    echo "更新响应: $UPDATE_RESPONSE"
    echo ""
fi

# 6. 手动触发任务
if [ ! -z "$TASK_ID" ]; then
    echo "6. 测试手动触发任务..."
    TRIGGER_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/trigger" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "触发响应: $TRIGGER_RESPONSE"
    echo ""
fi

# 7. 获取任务日志
if [ ! -z "$TASK_ID" ]; then
    echo "7. 测试获取任务日志..."
    sleep 2  # 等待任务执行
    LOGS_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/logs" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "日志响应: $LOGS_RESPONSE"
    echo ""
fi

# 8. 获取任务统计
echo "8. 测试获取任务统计..."
STATS_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/auto-generator/stats" \
  -H "Authorization: Bearer $TOKEN")

echo "统计响应: $STATS_RESPONSE"
echo ""

# 9. 停止任务
if [ ! -z "$TASK_ID" ]; then
    echo "9. 测试停止任务..."
    STOP_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/stop" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "停止响应: $STOP_RESPONSE"
    echo ""
fi

# 10. 删除任务
if [ ! -z "$TASK_ID" ]; then
    echo "10. 测试删除任务..."
    DELETE_RESPONSE=$(curl -s -X DELETE "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "删除响应: $DELETE_RESPONSE"
    echo ""
fi

# 11. 验证任务已删除
echo "11. 验证任务已删除..."
FINAL_TASKS=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks" \
  -H "Authorization: Bearer $TOKEN")

echo "最终任务列表: $FINAL_TASKS"
echo ""

echo "=========================================="
echo "测试完成！"
echo "=========================================="
