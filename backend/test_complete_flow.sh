#!/bin/bash

# 完整功能测试脚本

BASE_URL="http://localhost:8000"
TOKEN=""

echo "=========================================="
echo "完整功能测试"
echo "=========================================="
echo ""

# 1. 登录
echo "1. 登录..."
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123")

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ 登录失败"
    exit 1
fi

echo "✅ 登录成功"
echo ""

# 2. 获取现有项目列表
echo "2. 获取项目列表..."
PROJECTS=$(curl -s -X GET "${BASE_URL}/api/novels" \
  -H "Authorization: Bearer $TOKEN")

echo "项目列表: $PROJECTS"
echo ""

# 提取第一个项目ID（如果存在）
PROJECT_ID=$(echo $PROJECTS | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

# 3. 如果没有项目，创建一个
if [ -z "$PROJECT_ID" ]; then
    echo "3. 创建新项目..."
    CREATE_PROJECT=$(curl -s -X POST "${BASE_URL}/api/novels" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"title": "测试小说项目", "initial_prompt": "写一个关于程序员的都市轻喜剧小说"}')
    
    echo "创建项目响应: $CREATE_PROJECT"
    PROJECT_ID=$(echo $CREATE_PROJECT | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
    
    if [ -z "$PROJECT_ID" ]; then
        echo "❌ 创建项目失败"
        exit 1
    fi
    echo "✅ 项目创建成功，ID: $PROJECT_ID"
else
    echo "3. 使用现有项目，ID: $PROJECT_ID"
fi
echo ""

# 4. 获取项目详情
echo "4. 获取项目详情..."
PROJECT_DETAIL=$(curl -s -X GET "${BASE_URL}/api/novels/${PROJECT_ID}" \
  -H "Authorization: Bearer $TOKEN")

echo "项目详情: $PROJECT_DETAIL"
echo ""

# 5. 创建自动生成器任务
echo "5. 创建自动生成器任务..."
CREATE_TASK=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"${PROJECT_ID}\",
    \"target_chapters\": 5,
    \"chapters_per_batch\": 1,
    \"interval_seconds\": 10,
    \"auto_select_version\": true,
    \"generation_config\": {
      \"style\": \"轻松幽默\",
      \"tone\": \"第三人称\"
    }
  }")

echo "创建任务响应: $CREATE_TASK"
TASK_ID=$(echo $CREATE_TASK | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

if [ -z "$TASK_ID" ]; then
    echo "❌ 创建任务失败"
else
    echo "✅ 任务创建成功，ID: $TASK_ID"
fi
echo ""

# 6. 获取任务详情
if [ ! -z "$TASK_ID" ]; then
    echo "6. 获取任务详情..."
    TASK_DETAIL=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "任务详情: $TASK_DETAIL"
    echo ""
fi

# 7. 启动任务
if [ ! -z "$TASK_ID" ]; then
    echo "7. 启动任务..."
    START_TASK=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/start" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "启动响应: $START_TASK"
    echo ""
fi

# 8. 等待一段时间，查看任务进度
if [ ! -z "$TASK_ID" ]; then
    echo "8. 等待15秒，查看任务进度..."
    sleep 15
    
    TASK_STATUS=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "任务状态: $TASK_STATUS"
    echo ""
fi

# 9. 获取任务日志
if [ ! -z "$TASK_ID" ]; then
    echo "9. 获取任务日志..."
    LOGS=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/logs" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "任务日志: $LOGS"
    echo ""
fi

# 10. 暂停任务
if [ ! -z "$TASK_ID" ]; then
    echo "10. 暂停任务..."
    PAUSE_TASK=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/pause" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "暂停响应: $PAUSE_TASK"
    echo ""
fi

# 11. 停止任务
if [ ! -z "$TASK_ID" ]; then
    echo "11. 停止任务..."
    STOP_TASK=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/stop" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "停止响应: $STOP_TASK"
    echo ""
fi

# 12. 检查项目章节
echo "12. 检查项目章节..."
PROJECT_FINAL=$(curl -s -X GET "${BASE_URL}/api/novels/${PROJECT_ID}" \
  -H "Authorization: Bearer $TOKEN")

CHAPTER_COUNT=$(echo $PROJECT_FINAL | grep -o '"chapter_count":[0-9]*' | cut -d':' -f2)
echo "项目最终状态 - 章节数: $CHAPTER_COUNT"
echo ""

echo "=========================================="
echo "测试完成！"
echo "=========================================="
