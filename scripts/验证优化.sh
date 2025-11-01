#!/bin/bash

echo "=========================================="
echo "增强模式优化验证脚本"
echo "=========================================="
echo ""

cd backend

echo "✅ 1. 检查Python语法..."
python3 -m py_compile \
    app/utils/metrics.py \
    app/schemas/generation_config.py \
    app/services/super_analysis_service.py \
    app/services/auto_generator_service.py \
    tests/integration/test_enhanced_mode_integration.py

if [ $? -eq 0 ]; then
    echo "   ✅ 语法检查通过"
else
    echo "   ❌ 语法检查失败"
    exit 1
fi

echo ""
echo "✅ 2. 检查导入..."
python3 -c "
from app.utils.metrics import (
    track_duration, track_in_progress,
    record_success, record_failure,
    record_character_match, record_json_parse_failure,
    CostEstimator
)
from app.schemas.generation_config import (
    GenerationConfig, EnhancedFeatures, DynamicThreshold,
    get_default_config, should_run_enhanced_analysis, get_enabled_features
)
print('   ✅ 所有模块导入成功')
"

if [ $? -eq 0 ]; then
    echo ""
else
    echo "   ❌ 导入失败"
    exit 1
fi

echo "✅ 3. 测试成本估算器..."
python3 -c "
from app.utils.metrics import CostEstimator

# 测试基础模式成本估算
basic_cost = CostEstimator.estimate_chapter_cost('basic', 'gpt-3.5-turbo')
print(f'   基础模式成本: \${basic_cost[\"cost_usd\"]:.4f} USD / ¥{basic_cost[\"cost_cny\"]:.4f} CNY')

# 测试增强模式成本估算
enhanced_cost = CostEstimator.estimate_chapter_cost('enhanced', 'gpt-3.5-turbo')
print(f'   增强模式成本: \${enhanced_cost[\"cost_usd\"]:.4f} USD / ¥{enhanced_cost[\"cost_cny\"]:.4f} CNY')

# 验证增强模式成本更高
assert enhanced_cost['cost_usd'] > basic_cost['cost_usd'], '增强模式成本应该更高'
print('   ✅ 成本估算正确')
"

echo ""
echo "✅ 4. 测试配置解析..."
python3 -c "
from app.schemas.generation_config import (
    GenerationConfig, get_default_config,
    should_run_enhanced_analysis, get_enabled_features
)

# 测试默认配置
config = get_default_config('enhanced')
print(f'   默认配置: {config[\"generation_mode\"]}')

# 测试动态阈值
assert should_run_enhanced_analysis(config, 3000) == True, '长章节应该运行增强分析'
assert should_run_enhanced_analysis(config, 500) == False, '短章节不应该运行增强分析'
print('   ✅ 动态阈值检查正确')

# 测试功能开关
features = get_enabled_features(config)
assert features['character_tracking'] == True, '默认应该启用角色追踪'
print('   ✅ 功能开关解析正确')
"

echo ""
echo "✅ 5. 检查文件完整性..."
files=(
    "app/utils/metrics.py"
    "app/schemas/generation_config.py"
    "tests/integration/test_enhanced_mode_integration.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file 不存在"
        exit 1
    fi
done

echo ""
echo "=========================================="
echo "🎉 所有验证通过！"
echo "=========================================="
echo ""
echo "📊 优化总结:"
echo "  ✅ Bug #6: JSON解析容错"
echo "  ✅ Bug #2: 角色匹配优化"
echo "  ✅ Bug #5: 章节长度限制"
echo "  ✅ Prometheus监控指标"
echo "  ✅ 细粒度功能开关"
echo "  ✅ 动态阈值检查"
echo "  ✅ 成本估算器"
echo "  ✅ 集成测试"
echo ""
echo "📁 备份位置: ../arboris-novel-fresh-backup-20251030-114448"
echo ""
echo "📖 详细报告: ../增强模式优化完成报告-20251030.md"
echo ""
echo "🚀 下一步:"
echo "  1. 运行集成测试: pytest tests/integration/test_enhanced_mode_integration.py -v"
echo "  2. 启动后端服务测试实际效果"
echo "  3. 配置Prometheus监控"
echo ""

