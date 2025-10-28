#!/bin/bash

# 测试连续生成多个章节

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "测试连续生成多章节"
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

# 2. 创建新项目
echo "2. 创建新项目..."
CREATE_PROJECT=$(curl -s -X POST "${BASE_URL}/api/novels" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "多章节测试-'$(date +%s)'",
    "initial_prompt": "写一个关于时间旅行者的科幻短篇小说"
  }')

PROJECT_ID=$(echo $CREATE_PROJECT | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
echo "✅ 项目ID: $PROJECT_ID"
echo ""

# 3. 保存蓝图（包含3章大纲）
echo "3. 保存蓝图（3章）..."
SAVE_BLUEPRINT=$(curl -s -X POST "${BASE_URL}/api/novels/${PROJECT_ID}/blueprint/save" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "时间旅行者",
    "target_audience": "科幻爱好者",
    "genre": "科幻",
    "style": "紧凑悬疑",
    "tone": "第三人称",
    "one_sentence_summary": "一个物理学家意外发现时间旅行的秘密",
    "full_synopsis": "物理学家李博士在实验室中意外发现了时间旅行的方法，但每次穿越都会带来意想不到的后果。",
    "world_setting": {
      "time": "2025年",
      "location": "物理实验室"
    },
    "characters": [
      {
        "name": "李博士",
        "role": "主角",
        "personality": "聪明、谨慎、好奇",
        "background": "量子物理学家"
      }
    ],
    "relationships": [],
    "chapter_outline": [
      {
        "chapter_number": 1,
        "title": "意外的发现",
        "summary": "李博士在实验中意外发现了时间异常现象",
        "key_events": ["实验失败", "发现异常", "初步验证"],
        "word_count_target": 1500
      },
      {
        "chapter_number": 2,
        "title": "第一次穿越",
        "summary": "李博士尝试第一次时间旅行，回到了一小时前",
        "key_events": ["准备穿越", "成功穿越", "发现问题"],
        "word_count_target": 1500
      },
      {
        "chapter_number": 3,
        "title": "时间悖论",
        "summary": "李博士发现时间旅行会产生悖论，必须找到解决方法",
        "key_events": ["遇到自己", "理解悖论", "寻找答案"],
        "word_count_target": 1500
      }
    ]
  }')

echo "✅ 蓝图已保存"
echo ""

# 4. 创建自动生成器任务
echo "4. 创建自动生成器任务（目标：3章）..."
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

echo "✅ 任务已启动"
echo ""
echo "开始监控任务进度（最多3分钟）..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 6. 监控任务进度
START_TIME=$(date +%s)
MAX_DURATION=180  # 3分钟

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    if [ $ELAPSED -gt $MAX_DURATION ]; then
        echo ""
        echo "⏱️  超时（3分钟），停止监控"
        break
    fi
    
    # 获取任务状态
    TASK_STATUS=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}" \
      -H "Authorization: Bearer $TOKEN")
    
    STATUS=$(echo $TASK_STATUS | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    CHAPTERS_GENERATED=$(echo $TASK_STATUS | grep -o '"chapters_generated":[0-9]*' | cut -d':' -f2)
    ERROR_COUNT=$(echo $TASK_STATUS | grep -o '"error_count":[0-9]*' | cut -d':' -f2)
    
    # 显示进度
    echo -ne "\r[${ELAPSED}s] 状态:$STATUS | 已生成:${CHAPTERS_GENERATED}/3章 | 错误:${ERROR_COUNT}次"
    
    # 检查是否完成
    if [ "$CHAPTERS_GENERATED" -ge 3 ]; then
        echo ""
        echo ""
        echo "🎉 成功生成 3 章！"
        break
    fi
    
    # 检查是否有错误
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo ""
        echo ""
        echo "❌ 发生错误，查看日志..."
        
        curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/logs?limit=5" \
          -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
logs = json.load(sys.stdin)
for log in logs:
    if log['log_type'] == 'error':
        print(f\"错误: {log['message'][:200]}...\")
" 2>/dev/null
        break
    fi
    
    # 检查任务状态
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "stopped" ] || [ "$STATUS" = "error" ]; then
        echo ""
        echo ""
        echo "任务已结束: $STATUS"
        break
    fi
    
    sleep 5
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 7. 获取最终状态
echo "7. 获取最终状态..."
FINAL_STATUS=$(curl -s -X GET "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}" \
  -H "Authorization: Bearer $TOKEN")

echo "$FINAL_STATUS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'任务状态: {data[\"status\"]}')
    print(f'已生成章节: {data[\"chapters_generated\"]}/3')
    print(f'错误次数: {data[\"error_count\"]}')
    if data.get('last_error'):
        print(f'最后错误: {data[\"last_error\"][:100]}...')
except Exception as e:
    print(f'解析错误: {e}')
"
echo ""

# 8. 检查生成的章节
echo "8. 检查生成的章节内容..."
PROJECT_DETAIL=$(curl -s -X GET "${BASE_URL}/api/novels/${PROJECT_ID}" \
  -H "Authorization: Bearer $TOKEN")

CHAPTER_COUNT=$(echo $PROJECT_DETAIL | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data.get('chapters', [])))
except:
    print(0)
" 2>/dev/null)

echo "项目总章节数: $CHAPTER_COUNT"
echo ""

if [ "$CHAPTER_COUNT" -gt 0 ]; then
    echo "章节详情:"
    for i in $(seq 1 $CHAPTER_COUNT); do
        echo ""
        echo "━━━ 第 $i 章 ━━━"
        
        CHAPTER=$(curl -s -X GET "${BASE_URL}/api/novels/${PROJECT_ID}/chapters/$i" \
          -H "Authorization: Bearer $TOKEN")
        
        echo "$CHAPTER" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'标题: {data.get(\"title\", \"无\")}')
    content = data.get('content', '')
    if content:
        print(f'内容长度: {len(content)} 字符')
        print(f'内容预览: {content[:150]}...')
    else:
        print('内容: (空)')
except Exception as e:
    print(f'错误: {e}')
" 2>/dev/null
    done
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 9. 停止任务
echo ""
echo "9. 停止任务..."
curl -s -X POST "${BASE_URL}/api/auto-generator/tasks/${TASK_ID}/stop" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo "✅ 任务已停止"
echo ""

# 10. 总结
echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo "项目ID: $PROJECT_ID"
echo "任务ID: $TASK_ID"
echo "生成章节数: $CHAPTER_COUNT/3"
echo ""

if [ "$CHAPTER_COUNT" -eq 3 ]; then
    echo "🎉 测试成功！成功生成 3 章内容！"
elif [ "$CHAPTER_COUNT" -gt 0 ]; then
    echo "⚠️  部分成功，生成了 $CHAPTER_COUNT 章"
else
    echo "❌ 测试失败，未生成任何章节"
fi
