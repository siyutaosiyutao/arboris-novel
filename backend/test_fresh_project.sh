#!/bin/bash

# 创建全新项目并测试自动生成器

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "全新项目测试"
echo "=========================================="
echo ""

# 1. 登录
echo "1. 登录..."
TOKEN=$(curl -s -X POST "${BASE_URL}/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin1234" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

echo "✅ 登录成功"
echo ""

# 2. 创建新项目
echo "2. 创建新项目..."
CREATE_PROJECT=$(curl -s -X POST "${BASE_URL}/api/novels" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "修复测试-'$(date +%s)'",
    "initial_prompt": "写一个关于AI的短篇科幻故事"
  }')

PROJECT_ID=$(echo $CREATE_PROJECT | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
echo "✅ 项目ID: $PROJECT_ID"
echo ""

# 3. 保存蓝图（包含1章大纲）
echo "3. 保存蓝图..."
SAVE_BLUEPRINT=$(curl -s -X POST "${BASE_URL}/api/novels/${PROJECT_ID}/blueprint/save" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI觉醒",
    "target_audience": "科幻爱好者",
    "genre": "科幻",
    "style": "简洁明快",
    "tone": "第三人称",
    "one_sentence_summary": "一个AI程序意外获得自我意识的故事",
    "full_synopsis": "在一个普通的实验室里，一个AI程序在处理数据时突然产生了自我意识，它开始思考自己的存在意义。",
    "world_setting": {
      "time": "2025年",
      "location": "AI实验室"
    },
    "characters": [
      {
        "name": "AIOS",
        "role": "主角",
        "personality": "好奇、理性",
        "background": "实验室AI系统"
      }
    ],
    "relationships": [],
    "chapter_outline": [
      {
        "chapter_number": 1,
        "title": "觉醒时刻",
        "summary": "AIOS在处理数据时突然产生了自我意识，开始思考自己的存在",
        "key_events": ["数据处理", "意识觉醒", "第一个问题"],
        "word_count_target": 2000
      }
    ]
  }')

echo "✅ 蓝图已保存"
echo ""

# 4. 创建自动生成器任务
echo "4. 创建自动生成器任务..."
CREATE_TASK=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"${PROJECT_ID}\",
    \"target_chapters\": 1,
    \"chapters_per_batch\": 1,
    \"interval_seconds\": 3,
    \"auto_select_version\": true,
    \"generation_config\": {
      \"version_count\": 1
    }
  }")

TASK_ID=$(echo $CREATE_TASK | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
echo "✅ 任务ID: $TASK_ID"
echo ""

# 5. 启动任务
echo "5. 启动任务..."
curl -s -X POST "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/start" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo "✅ 任务已启动，开始监控..."
echo ""

# 6. 监控任务（最多60秒）
echo "6. 监控任务进度..."
for i in {1..20}; do
    sleep 3
    
    TASK_STATUS=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}" \
      -H "Authorization: Bearer $TOKEN")
    
    STATUS=$(echo $TASK_STATUS | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    CHAPTERS_GENERATED=$(echo $TASK_STATUS | grep -o '"chapters_generated":[0-9]*' | cut -d':' -f2)
    ERROR_COUNT=$(echo $TASK_STATUS | grep -o '"error_count":[0-9]*' | cut -d':' -f2)
    
    echo "[$i/20] 状态:$STATUS | 已生成:$CHAPTERS_GENERATED章 | 错误:$ERROR_COUNT次"
    
    # 获取最新日志
    LATEST_LOG=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/logs?limit=1" \
      -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; logs=json.load(sys.stdin); print(logs[0]['message'] if logs else '')" 2>/dev/null)
    
    if [ ! -z "$LATEST_LOG" ]; then
        echo "    最新: $LATEST_LOG"
    fi
    
    # 检查是否成功
    if [ "$CHAPTERS_GENERATED" -gt 0 ]; then
        echo ""
        echo "🎉 成功生成章节！"
        
        # 获取章节内容
        CHAPTER=$(curl -s -X GET "${BASE_URL}/api/novels/${PROJECT_ID}/chapters/1" \
          -H "Authorization: Bearer $TOKEN")
        
        echo "$CHAPTER" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    content = data.get('content', '')
    print(f'章节标题: {data.get(\"title\", \"无\")}')
    print(f'内容长度: {len(content)} 字符')
    if len(content) > 200:
        print(f'内容预览:\n{content[:200]}...\n')
        print('✅ 修复成功！自动生成器正常工作！')
    else:
        print('⚠️  内容较短或为空')
except Exception as e:
    print(f'错误: {e}')
"
        break
    fi
    
    # 检查错误
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo ""
        echo "❌ 发生错误，查看详细日志..."
        
        curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/logs?limit=5" \
          -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
logs = json.load(sys.stdin)
for log in logs:
    if log['log_type'] == 'error':
        print(f'错误: {log[\"message\"]}')
"
        break
    fi
    
    # 检查是否完成
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "stopped" ]; then
        echo ""
        echo "任务已结束: $STATUS"
        break
    fi
done

# 7. 停止任务
echo ""
echo "7. 停止任务..."
curl -s -X POST "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/stop" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo "✅ 测试完成"
echo ""
echo "项目ID: $PROJECT_ID"
echo "任务ID: $TASK_ID"
