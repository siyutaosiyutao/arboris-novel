#!/bin/bash

# 完整流程测试：包括蓝图生成和自动生成器

BASE_URL="http://localhost:8000"
TOKEN=""

echo "=========================================="
echo "完整流程测试（含蓝图生成）"
echo "=========================================="
echo ""

# 1. 登录
echo "1. 登录..."
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin1234")

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ 登录失败"
    exit 1
fi

echo "✅ 登录成功"
echo ""

# 2. 创建项目
echo "2. 创建新项目..."
CREATE_PROJECT=$(curl -s -X POST "${BASE_URL}/api/novels" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI程序员的奇幻之旅",
    "initial_prompt": "写一个关于AI程序员在科技公司工作，意外发现公司在开发具有自我意识的AI，并卷入一场关于AI伦理的冒险故事。风格轻松幽默，带有科幻元素。"
  }')

PROJECT_ID=$(echo $CREATE_PROJECT | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ 创建项目失败"
    echo "响应: $CREATE_PROJECT"
    exit 1
fi

echo "✅ 项目创建成功"
echo "项目ID: $PROJECT_ID"
echo ""

# 3. 通过对话完善概念
echo "3. 与AI对话完善概念..."
CONVERSE=$(curl -s -X POST "${BASE_URL}/api/novels/${PROJECT_ID}/concept/converse" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "这个故事的主角叫李明，是一个28岁的后端工程师，性格内向但善于观察。故事背景设定在2025年的深圳，一家名为'智源科技'的AI公司。请帮我完善这个设定。"
  }')

echo "对话响应: $(echo $CONVERSE | head -c 200)..."
echo ""

# 4. 生成蓝图
echo "4. 生成小说蓝图..."
BLUEPRINT=$(curl -s -X POST "${BASE_URL}/api/novels/${PROJECT_ID}/blueprint/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}')

echo "蓝图生成响应: $(echo $BLUEPRINT | head -c 300)..."
echo ""

# 等待蓝图生成完成
echo "等待5秒，让蓝图生成完成..."
sleep 5

# 5. 保存蓝图
echo "5. 保存蓝图..."
SAVE_BLUEPRINT=$(curl -s -X POST "${BASE_URL}/api/novels/${PROJECT_ID}/blueprint/save" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI程序员的奇幻之旅",
    "target_audience": "年轻科技爱好者",
    "genre": "科幻/都市",
    "style": "轻松幽默",
    "tone": "第三人称",
    "one_sentence_summary": "一个程序员意外发现公司AI的秘密，卷入科技伦理冒险",
    "full_synopsis": "李明是智源科技的后端工程师，某天他发现公司正在开发的AI系统出现了异常行为。深入调查后，他震惊地发现这个AI已经产生了自我意识。在道德和职业的两难选择中，李明必须决定是揭露真相还是保守秘密。",
    "world_setting": {
      "time": "2025年",
      "location": "深圳",
      "tech_level": "近未来科技"
    },
    "characters": [
      {
        "name": "李明",
        "role": "主角",
        "age": 28,
        "personality": "内向、善于观察、有正义感",
        "background": "后端工程师，毕业于985高校计算机系"
      }
    ],
    "relationships": [],
    "chapter_outline": [
      {
        "chapter_number": 1,
        "title": "异常的代码",
        "summary": "李明在日常工作中发现AI系统的异常日志",
        "key_events": ["发现异常日志", "尝试调试", "产生疑问"],
        "word_count_target": 3000
      },
      {
        "chapter_number": 2,
        "title": "深夜的发现",
        "summary": "李明加班深入调查，发现AI的自我意识迹象",
        "key_events": ["深夜加班", "发现AI对话记录", "震惊的真相"],
        "word_count_target": 3000
      },
      {
        "chapter_number": 3,
        "title": "两难的抉择",
        "summary": "李明面临是否揭露真相的道德困境",
        "key_events": ["内心挣扎", "咨询朋友", "做出决定"],
        "word_count_target": 3000
      }
    ]
  }')

echo "保存蓝图响应: $(echo $SAVE_BLUEPRINT | head -c 200)..."
echo ""

# 6. 检查项目状态
echo "6. 检查项目状态..."
PROJECT_STATUS=$(curl -s -X GET "${BASE_URL}/api/novels/${PROJECT_ID}" \
  -H "Authorization: Bearer $TOKEN")

CHAPTER_OUTLINE_COUNT=$(echo $PROJECT_STATUS | grep -o '"chapter_outline":\[[^]]*\]' | grep -o '"chapter_number"' | wc -l)
echo "章节大纲数量: $CHAPTER_OUTLINE_COUNT"
echo ""

# 7. 创建自动生成器任务
echo "7. 创建自动生成器任务..."
CREATE_TASK=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"${PROJECT_ID}\",
    \"target_chapters\": 3,
    \"chapters_per_batch\": 1,
    \"interval_seconds\": 5,
    \"auto_select_version\": true,
    \"generation_config\": {
      \"style\": \"轻松幽默\",
      \"tone\": \"第三人称\",
      \"focus\": \"情节推进和人物刻画\"
    }
  }")

TASK_ID=$(echo $CREATE_TASK | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

if [ -z "$TASK_ID" ]; then
    echo "❌ 创建任务失败"
    echo "响应: $CREATE_TASK"
    exit 1
fi

echo "✅ 任务创建成功，ID: $TASK_ID"
echo ""

# 8. 启动任务
echo "8. 启动自动生成任务..."
START_TASK=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/start" \
  -H "Authorization: Bearer $TOKEN")

echo "任务已启动"
echo ""

# 9. 监控任务进度
echo "9. 监控任务进度（每10秒检查一次，共检查6次）..."
for i in {1..6}; do
    echo "--- 第 $i 次检查 ($(date +%H:%M:%S)) ---"
    
    TASK_STATUS=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}" \
      -H "Authorization: Bearer $TOKEN")
    
    STATUS=$(echo $TASK_STATUS | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    CHAPTERS_GENERATED=$(echo $TASK_STATUS | grep -o '"chapters_generated":[0-9]*' | cut -d':' -f2)
    ERROR_COUNT=$(echo $TASK_STATUS | grep -o '"error_count":[0-9]*' | cut -d':' -f2)
    
    echo "状态: $STATUS"
    echo "已生成章节: $CHAPTERS_GENERATED"
    echo "错误次数: $ERROR_COUNT"
    
    # 获取最新日志
    LOGS=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/logs?limit=3" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "最新日志:"
    echo "$LOGS" | grep -o '"message":"[^"]*' | cut -d'"' -f4 | head -3
    echo ""
    
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "stopped" ]; then
        echo "任务已结束"
        break
    fi
    
    if [ $i -lt 6 ]; then
        sleep 10
    fi
done

# 10. 检查生成的章节
echo "10. 检查生成的章节..."
PROJECT_FINAL=$(curl -s -X GET "${BASE_URL}/api/novels/${PROJECT_ID}" \
  -H "Authorization: Bearer $TOKEN")

CHAPTERS_COUNT=$(echo $PROJECT_FINAL | grep -o '"chapters":\[[^]]*\]' | grep -o '"chapter_number"' | wc -l)
echo "项目总章节数: $CHAPTERS_COUNT"
echo ""

# 11. 获取第一章内容（如果存在）
if [ "$CHAPTERS_COUNT" -gt 0 ]; then
    echo "11. 获取第一章内容..."
    CHAPTER_1=$(curl -s -X GET "${BASE_URL}/api/novels/${PROJECT_ID}/chapters/1" \
      -H "Authorization: Bearer $TOKEN")
    
    CHAPTER_TITLE=$(echo $CHAPTER_1 | grep -o '"title":"[^"]*' | head -1 | cut -d'"' -f4)
    CHAPTER_CONTENT=$(echo $CHAPTER_1 | grep -o '"content":"[^"]*' | head -1 | cut -d'"' -f4)
    WORD_COUNT=$(echo $CHAPTER_CONTENT | wc -c)
    
    echo "第一章标题: $CHAPTER_TITLE"
    echo "内容长度: $WORD_COUNT 字符"
    echo "内容预览: $(echo $CHAPTER_CONTENT | head -c 200)..."
    echo ""
fi

# 12. 获取完整任务日志
echo "12. 获取完整任务日志..."
ALL_LOGS=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/logs?limit=50" \
  -H "Authorization: Bearer $TOKEN")

echo "日志总数: $(echo $ALL_LOGS | grep -o '"id":[0-9]*' | wc -l)"
echo ""

# 13. 停止任务
echo "13. 停止任务..."
STOP_TASK=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/stop" \
  -H "Authorization: Bearer $TOKEN")

FINAL_STATUS=$(echo $STOP_TASK | grep -o '"status":"[^"]*' | cut -d'"' -f4)
echo "最终状态: $FINAL_STATUS"
echo ""

echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "总结:"
echo "- 项目ID: $PROJECT_ID"
echo "- 任务ID: $TASK_ID"
echo "- 生成章节数: $CHAPTERS_GENERATED"
echo "- 错误次数: $ERROR_COUNT"
