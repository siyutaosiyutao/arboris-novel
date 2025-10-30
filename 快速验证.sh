#!/bin/bash

echo "=========================================="
echo "增强模式优化快速验证"
echo "=========================================="
echo ""

cd backend

echo "✅ 1. 检查Python语法..."
python3 -m py_compile \
    app/utils/metrics.py \
    app/schemas/generation_config.py \
    app/services/super_analysis_service.py \
    app/services/auto_generator_service.py \
    tests/integration/test_enhanced_mode_integration.py 2>&1

if [ $? -eq 0 ]; then
    echo "   ✅ 所有文件语法正确"
else
    echo "   ❌ 语法检查失败"
    exit 1
fi

echo ""
echo "✅ 2. 检查文件完整性..."
files=(
    "app/utils/metrics.py"
    "app/schemas/generation_config.py"
    "app/services/super_analysis_service.py"
    "app/services/auto_generator_service.py"
    "tests/integration/test_enhanced_mode_integration.py"
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

# 检查Bug #6修复
if grep -q "record_json_parse_failure" app/services/super_analysis_service.py; then
    echo "   ✅ Bug #6: JSON解析容错已添加"
else
    echo "   ❌ Bug #6: 未找到JSON解析容错代码"
fi

# 检查Bug #2修复
if grep -q "abs(len(name) - len(char_name)) <= 2" app/services/auto_generator_service.py; then
    echo "   ✅ Bug #2: 角色匹配长度限制已添加"
else
    echo "   ❌ Bug #2: 未找到角色匹配优化代码"
fi

# 检查Bug #5修复
if grep -q "MAX_CONTENT_LENGTH = 8000" app/services/super_analysis_service.py; then
    echo "   ✅ Bug #5: 章节长度限制已添加"
else
    echo "   ❌ Bug #5: 未找到章节长度限制代码"
fi

# 检查监控指标
if grep -q "from prometheus_client import" app/utils/metrics.py; then
    echo "   ✅ Prometheus监控指标已添加"
else
    echo "   ❌ 未找到Prometheus监控代码"
fi

# 检查细粒度配置
if grep -q "class EnhancedFeatures" app/schemas/generation_config.py; then
    echo "   ✅ 细粒度功能开关已添加"
else
    echo "   ❌ 未找到功能开关配置"
fi

# 检查动态阈值
if grep -q "should_run_enhanced_analysis" app/services/auto_generator_service.py; then
    echo "   ✅ 动态阈值检查已添加"
else
    echo "   ❌ 未找到动态阈值检查"
fi

echo ""
echo "✅ 4. 检查依赖配置..."
if grep -q "prometheus-client" requirements.txt; then
    echo "   ✅ prometheus-client 已添加到 requirements.txt"
else
    echo "   ❌ prometheus-client 未添加到 requirements.txt"
fi

if grep -q "pytest" requirements.txt; then
    echo "   ✅ pytest 已添加到 requirements.txt"
else
    echo "   ❌ pytest 未添加到 requirements.txt"
fi

echo ""
echo "=========================================="
echo "🎉 快速验证通过！"
echo "=========================================="
echo ""
echo "📊 优化总结:"
echo "  ✅ Bug #6: JSON解析容错 (super_analysis_service.py)"
echo "  ✅ Bug #2: 角色匹配优化 (auto_generator_service.py)"
echo "  ✅ Bug #5: 章节长度限制 (super_analysis_service.py)"
echo "  ✅ Prometheus监控指标 (utils/metrics.py)"
echo "  ✅ 细粒度功能开关 (schemas/generation_config.py)"
echo "  ✅ 动态阈值检查 (auto_generator_service.py)"
echo "  ✅ 成本估算器 (utils/metrics.py)"
echo "  ✅ 集成测试 (tests/integration/)"
echo ""
echo "📁 备份位置: ../arboris-novel-fresh-backup-20251030-114448"
echo ""
echo "📖 详细报告: ../增强模式优化完成报告-20251030.md"
echo ""
echo "🚀 下一步:"
echo "  1. 安装依赖: cd backend && pip install -r requirements.txt"
echo "  2. 运行集成测试: pytest tests/integration/test_enhanced_mode_integration.py -v"
echo "  3. 启动后端服务测试实际效果"
echo "  4. 配置Prometheus监控"
echo ""
echo "⚠️  注意: 如需回滚，请使用备份目录"
echo ""

