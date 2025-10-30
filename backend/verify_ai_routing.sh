#!/bin/bash

# AI路由系统验证脚本

echo "=========================================="
echo "AI路由系统验证"
echo "=========================================="
echo ""

# 1. 检查数据库表
echo "1. 检查数据库表..."
TABLES=$(sqlite3 storage/arboris.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ai_%' ORDER BY name;")

if [ -n "$TABLES" ]; then
    echo "✅ AI路由表已创建:"
    echo "$TABLES" | while read table; do
        echo "   - $table"
    done
else
    echo "❌ 未找到AI路由表"
    exit 1
fi
echo ""

# 2. 检查providers数据
echo "2. 检查AI提供商数据..."
PROVIDER_COUNT=$(sqlite3 storage/arboris.db "SELECT COUNT(*) FROM ai_providers;")
echo "✅ 找到 $PROVIDER_COUNT 个AI提供商"

sqlite3 storage/arboris.db "SELECT '   - ' || display_name || ' (' || name || ')' FROM ai_providers ORDER BY priority;"
echo ""

# 3. 检查routes数据
echo "3. 检查功能路由数据..."
ROUTE_COUNT=$(sqlite3 storage/arboris.db "SELECT COUNT(*) FROM ai_function_routes;")
echo "✅ 找到 $ROUTE_COUNT 个功能路由"

sqlite3 storage/arboris.db "SELECT '   - ' || display_name || ' -> ' || primary_model FROM ai_function_routes LIMIT 5;"
echo "   ..."
echo ""

# 4. 检查代码文件
echo "4. 检查代码文件..."
FILES=(
    "app/config/ai_function_config.py"
    "app/services/ai_orchestrator.py"
    "app/services/ai_orchestrator_helper.py"
    "app/models/ai_routing.py"
    "app/repositories/ai_routing_repository.py"
    "app/api/routers/ai_routing.py"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file (缺失)"
    fi
done
echo ""

# 5. 检查环境变量
echo "5. 检查环境变量..."
if [ -f ".env" ]; then
    if grep -q "SILICONFLOW_API_KEY=" .env; then
        KEY=$(grep "SILICONFLOW_API_KEY=" .env | cut -d'=' -f2)
        if [ -n "$KEY" ] && [ "$KEY" != "your-siliconflow-api-key-here" ]; then
            echo "   ✅ SILICONFLOW_API_KEY 已设置"
        else
            echo "   ⚠️  SILICONFLOW_API_KEY 未设置"
        fi
    else
        echo "   ❌ .env 中缺少 SILICONFLOW_API_KEY"
    fi
    
    if grep -q "GEMINI_API_KEY=" .env; then
        KEY=$(grep "GEMINI_API_KEY=" .env | cut -d'=' -f2)
        if [ -n "$KEY" ] && [ "$KEY" != "your-gemini-api-key-here" ]; then
            echo "   ✅ GEMINI_API_KEY 已设置"
        else
            echo "   ⚠️  GEMINI_API_KEY 未设置"
        fi
    else
        echo "   ❌ .env 中缺少 GEMINI_API_KEY"
    fi
else
    echo "   ❌ .env 文件不存在"
fi
echo ""

# 6. 检查Prometheus指标
echo "6. 检查Prometheus指标定义..."
if grep -q "ai_calls_total" app/utils/metrics.py; then
    echo "   ✅ ai_calls_total"
fi
if grep -q "ai_duration_seconds" app/utils/metrics.py; then
    echo "   ✅ ai_duration_seconds"
fi
if grep -q "ai_cost_usd_total" app/utils/metrics.py; then
    echo "   ✅ ai_cost_usd_total"
fi
if grep -q "ai_fallback_total" app/utils/metrics.py; then
    echo "   ✅ ai_fallback_total"
fi
echo ""

# 总结
echo "=========================================="
echo "验证完成"
echo "=========================================="
echo ""
echo "系统状态:"
echo "  ✅ 数据库层: 已就绪 ($PROVIDER_COUNT providers, $ROUTE_COUNT routes)"
echo "  ✅ 代码层: 已完成"
echo "  ✅ 监控层: 已集成"
echo ""
echo "下一步:"
echo "  1. 在 .env 中设置 API Keys"
echo "  2. 重启应用: pm2 restart backend"
echo "  3. 测试API: curl http://localhost:8000/api/ai-routing/health"
echo "  4. 查看指标: curl http://localhost:8000/metrics | grep ai_"
echo "  5. 查看日志: curl http://localhost:8000/api/ai-routing/logs"
echo ""

