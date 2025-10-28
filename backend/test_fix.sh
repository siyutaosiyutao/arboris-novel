#!/bin/bash

# 测试修复后的自动生成器

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "测试修复后的自动生成器"
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

# 2. 获取现有项目
echo "2. 获取现有项目..."
PROJECTS=$(curl -s -X GET "${BASE_URL}/api/novels" \
  -H "Authorization: Bearer $TOKEN")

PROJECT_ID=$(echo $PROJECTS | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

if [ -z "$PROJECT_ID" ]; then
    echo "没有现有项目，创建新项目..."
    
    # 创建项目
    CREATE_PROJECT=$(curl -s -X POST "${BASE_URL}/api/novels" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "title": "测试修复",
        "initial_prompt": "写一个简短的科幻故事"
      }')
    
    PROJECT_ID=$(echo $CREATE_PROJECT | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
    
    if [ -z "$PROJECT_ID" ]; then
        echo "❌ 创建项目失败"
        exit 1
    fi
    
    # 保存简单的蓝图
    SAVE_BLUEPRINT=$(curl -s -X POST "${BASE_URL}/api/novels/${PROJECT_ID}/blueprint/save" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "title": "测试修复",
        "target_audience": "测试",
        "genre": "科幻",
        "style": "简洁",
        "tone": "第三人称",
        "one_sentence_summary": "测试故事",
        "full_synopsis": "这是一个测试故事",
        "world_setting": {},
        "characters": [],
        "relationships": [],
        "chapter_outline": [
          {
            "chapter_number": 1,
            "title": "开始",
            "summary": "故事开始",
            "key_events": ["事件1"],
            "word_count_target": 1000
          }
        ]
      }')
    
    echo "✅ 项目创建并配置完成"
else
    echo "✅ 使用现有项目: $PROJECT_ID"
fi
echo ""

# 3. 创建自动生成器任务
echo "3. 创建自动生成器任务..."
CREATE_TASK=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"${PROJECT_ID}\",
    \"target_chapters\": 1,
    \"chapters_per_batch\": 1,
    \"interval_seconds\": 5,
    \"auto_select_version\": true,
    \"generation_config\": {}
  }")

TASK_ID=$(echo $CREATE_TASK | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

if [ -z "$TASK_ID" ]; then
    echo "❌ 创建任务失败"
    echo "响应: $CREATE_TASK"
    exit 1
fi

echo "✅ 任务创建成功，ID: $TASK_ID"
echo ""

# 4. 启动任务
echo "4. 启动任务..."
START_TASK=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/start" \
  -H "Authorization: Bearer $TOKEN")

echo "✅ 任务已启动"
echo ""

# 5. 监控任务（30秒）
echo "5. 监控任务进度（每5秒检查一次，共6次）..."
for i in {1..6}; do
    echo "--- 检查 $i/6 ($(date +%H:%M:%S)) ---"
    
    TASK_STATUS=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}" \
      -H "Authorization: Bearer $TOKEN")
    
    STATUS=$(echo $TASK_STATUS | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    CHAPTERS_GENERATED=$(echo $TASK_STATUS | grep -o '"chapters_generated":[0-9]*' | cut -d':' -f2)
    ERROR_COUNT=$(echo $TASK_STATUS | grep -o '"error_count":[0-9]*' | cut -d':' -f2)
    LAST_ERROR=$(echo $TASK_STATUS | grep -o '"last_error":"[^"]*' | cut -d'"' -f4)
    
    echo "  状态: $STATUS"
    echo "  已生成: $CHAPTERS_GENERATED 章"
    echo "  错误数: $ERROR_COUNT"
    
    if [ ! -z "$LAST_ERROR" ] && [ "$LAST_ERROR" != "null" ]; then
        echo "  最后错误: $LAST_ERROR"
    fi
    
    # 获取最新日志
    LOGS=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/logs?limit=2" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "  最新日志:"
    echo "$LOGS" | python3 -c "import sys, json; logs=json.load(sys.stdin); [print(f'    - {log[\"log_type\"]}: {log[\"message\"]}') for log in logs[:2]]" 2>/dev/null || echo "    (无法解析日志)"
    echo ""
    
    # 检查是否有 greenlet 错误
    if echo "$LAST_ERROR" | grep -q "greenlet"; then
        echo "❌ 仍然存在 greenlet 错误！"
        echo ""
        echo "完整错误信息:"
        echo "$LAST_ERROR"
        break
    fi
    
    # 如果成功生成了章节，检查内容
    if [ "$CHAPTERS_GENERATED" -gt 0 ]; then
        echo "✅ 成功生成章节！检查内容..."
        
        CHAPTER=$(curl -s -X GET "${BASE_URL}/api/novels/${PROJECT_ID}/chapters/1" \
          -H "Authorization: Bearer $TOKEN")
        
        CONTENT_LENGTH=$(echo $CHAPTER | grep -o '"content":"[^"]*' | wc -c)
        
        if [ $CONTENT_LENGTH -gt 100 ]; then
            echo "✅ 章节内容正常（长度: $CONTENT_LENGTH 字符）"
            echo ""
            echo "修复成功！自动生成器可以正常工作了。"
        else
            echo "⚠️  章节内容较短（长度: $CONTENT_LENGTH 字符）"
        fi
        
        break
    fi
    
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "stopped" ] || [ "$STATUS" = "error" ]; then
        echo "任务已结束，状态: $STATUS"
        break
    fi
    
    if [ $i -lt 6 ]; then
        sleep 5
    fi
done

# 6. 停止任务
echo ""
echo "6. 停止任务..."
STOP_TASK=$(curl -s -X POST "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/stop" \
  -H "Authorization: Bearer $TOKEN")

echo "✅ 任务已停止"
echo ""

# 7. 最终统计
echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo "最终状态:"
FINAL_STATUS=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}" \
  -H "Authorization: Bearer $TOKEN")

echo "$FINAL_STATUS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  任务ID: {data[\"id\"]}')
    print(f'  项目ID: {data[\"project_id\"]}')
    print(f'  状态: {data[\"status\"]}')
    print(f'  已生成章节: {data[\"chapters_generated\"]}')
    print(f'  错误次数: {data[\"error_count\"]}')
    if data.get('last_error'):
        print(f'  最后错误: {data[\"last_error\"][:100]}...')
except:
    print('  (无法解析状态)')
"

echo ""
if [ "$ERROR_COUNT" -eq 0 ] && [ "$CHAPTERS_GENERATED" -gt 0 ]; then
    echo "🎉 测试通过！修复成功！"
elif echo "$LAST_ERROR" | grep -q "greenlet"; then
    echo "❌ 测试失败：greenlet 错误仍然存在"
else
    echo "⚠️  测试结果不确定，请检查日志"
fi
