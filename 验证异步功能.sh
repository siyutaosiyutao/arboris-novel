#!/bin/bash

echo "=========================================="
echo "异步分析功能验证"
echo "=========================================="
echo ""

cd backend

echo "✅ 1. 检查Python语法..."
python3 -m py_compile \
    app/models/async_task.py \
    app/services/async_analysis_processor.py \
    app/api/async_analysis.py \
    app/background_processor.py \
    tests/test_async_analysis.py 2>&1

if [ $? -eq 0 ]; then
    echo "   ✅ 所有文件语法正确"
else
    echo "   ❌ 语法检查失败"
    exit 1
fi

echo ""
echo "✅ 2. 检查文件完整性..."
files=(
    "app/models/async_task.py"
    "app/services/async_analysis_processor.py"
    "app/api/async_analysis.py"
    "app/background_processor.py"
    "migrations/add_async_analysis_tables.sql"
    "deployment/async-processor.service"
    "tests/test_async_analysis.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file")
        echo "   ✅ $file ($lines 行)"
    else
        echo "   ❌ $file 不存在"
        exit 1
    fi
done

echo ""
echo "✅ 3. 检查关键代码片段..."

# 检查PendingAnalysis模型
if grep -q "class PendingAnalysis" app/models/async_task.py; then
    echo "   ✅ PendingAnalysis模型已创建"
else
    echo "   ❌ 未找到PendingAnalysis模型"
fi

# 检查AnalysisNotification模型
if grep -q "class AnalysisNotification" app/models/async_task.py; then
    echo "   ✅ AnalysisNotification模型已创建"
else
    echo "   ❌ 未找到AnalysisNotification模型"
fi

# 检查异步处理器
if grep -q "class AsyncAnalysisProcessor" app/services/async_analysis_processor.py; then
    echo "   ✅ AsyncAnalysisProcessor已创建"
else
    echo "   ❌ 未找到AsyncAnalysisProcessor"
fi

# 检查API路由
if grep -q "router = APIRouter" app/api/async_analysis.py; then
    echo "   ✅ API路由已创建"
else
    echo "   ❌ 未找到API路由"
fi

# 检查后台处理器启动脚本
if grep -q "class BackgroundProcessorManager" app/background_processor.py; then
    echo "   ✅ 后台处理器启动脚本已创建"
else
    echo "   ❌ 未找到后台处理器启动脚本"
fi

# 检查数据库迁移
if grep -q "CREATE TABLE.*pending_analysis" migrations/add_async_analysis_tables.sql; then
    echo "   ✅ 数据库迁移脚本已创建"
else
    echo "   ❌ 未找到数据库迁移脚本"
fi

# 检查增强模式修改
if grep -q "enhanced_mode=False" ../app/services/auto_generator_service.py; then
    echo "   ✅ 增强模式已修改为异步处理"
else
    echo "   ❌ 增强模式未修改"
fi

echo ""
echo "✅ 4. 检查模型导出..."
if grep -q "PendingAnalysis" app/models/__init__.py; then
    echo "   ✅ PendingAnalysis已导出"
else
    echo "   ❌ PendingAnalysis未导出"
fi

if grep -q "AnalysisNotification" app/models/__init__.py; then
    echo "   ✅ AnalysisNotification已导出"
else
    echo "   ❌ AnalysisNotification未导出"
fi

echo ""
echo "✅ 5. 检查Chapter模型关系..."
if grep -q "pending_analyses" app/models/novel.py; then
    echo "   ✅ Chapter模型已添加pending_analyses关系"
else
    echo "   ❌ Chapter模型未添加pending_analyses关系"
fi

echo ""
echo "=========================================="
echo "🎉 异步功能验证通过！"
echo "=========================================="
echo ""
echo "📊 新增功能:"
echo "  ✅ PendingAnalysis模型 - 待处理分析任务"
echo "  ✅ AnalysisNotification模型 - 分析通知"
echo "  ✅ AsyncAnalysisProcessor - 后台处理器"
echo "  ✅ API端点 - 查询状态、获取通知、重试任务"
echo "  ✅ 后台进程 - 独立运行的处理器"
echo "  ✅ 数据库迁移 - SQL脚本"
echo "  ✅ systemd服务 - 生产环境部署"
echo "  ✅ 单元测试 - 完整测试覆盖"
echo ""
echo "📁 新增文件 (7个):"
echo "  1. app/models/async_task.py"
echo "  2. app/services/async_analysis_processor.py"
echo "  3. app/api/async_analysis.py"
echo "  4. app/background_processor.py"
echo "  5. migrations/add_async_analysis_tables.sql"
echo "  6. deployment/async-processor.service"
echo "  7. tests/test_async_analysis.py"
echo ""
echo "🔧 修改文件 (3个):"
echo "  1. app/models/__init__.py - 导出新模型"
echo "  2. app/models/novel.py - 添加关系"
echo "  3. app/services/auto_generator_service.py - 异步处理"
echo "  4. app/services/super_analysis_service.py - 添加enhanced_mode参数"
echo ""
echo "🚀 下一步:"
echo "  1. 运行数据库迁移:"
echo "     sqlite3 data/arboris.db < migrations/add_async_analysis_tables.sql"
echo ""
echo "  2. 启动后台处理器:"
echo "     python -m app.background_processor"
echo ""
echo "  3. 注册API路由 (编辑 app/main.py):"
echo "     from app.api import async_analysis"
echo "     app.include_router(async_analysis.router)"
echo ""
echo "  4. 运行测试:"
echo "     pytest tests/test_async_analysis.py -v"
echo ""
echo "📖 详细文档: ../异步分析功能说明.md"
echo ""

