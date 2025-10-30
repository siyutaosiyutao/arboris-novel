#!/bin/bash

# 验证AI功能路由配置

echo "=========================================="
echo "AI功能路由配置验证"
echo "=========================================="
echo ""

# 检查配置文件是否存在
echo "1. 检查配置文件..."
if [ -f "app/config/ai_function_config.py" ]; then
    echo "✅ ai_function_config.py 存在"
else
    echo "❌ ai_function_config.py 不存在"
    exit 1
fi

if [ -f "app/services/ai_orchestrator.py" ]; then
    echo "✅ ai_orchestrator.py 存在"
else
    echo "❌ ai_orchestrator.py 不存在"
    exit 1
fi

echo ""

# 检查环境变量
echo "2. 检查环境变量..."

if [ -f ".env" ]; then
    echo "✅ .env 文件存在"
    echo ""
    
    # 检查必需的API Keys
    if grep -q "SILICONFLOW_API_KEY=" .env; then
        KEY=$(grep "SILICONFLOW_API_KEY=" .env | cut -d'=' -f2)
        if [ -n "$KEY" ] && [ "$KEY" != "your-siliconflow-api-key-here" ]; then
            echo "✅ SILICONFLOW_API_KEY 已设置"
        else
            echo "⚠️  SILICONFLOW_API_KEY 未设置或使用默认值"
        fi
    else
        echo "❌ .env 中缺少 SILICONFLOW_API_KEY"
    fi
    
    if grep -q "GEMINI_API_KEY=" .env; then
        KEY=$(grep "GEMINI_API_KEY=" .env | cut -d'=' -f2)
        if [ -n "$KEY" ] && [ "$KEY" != "your-gemini-api-key-here" ]; then
            echo "✅ GEMINI_API_KEY 已设置"
        else
            echo "⚠️  GEMINI_API_KEY 未设置或使用默认值"
        fi
    else
        echo "❌ .env 中缺少 GEMINI_API_KEY"
    fi
else
    echo "❌ .env 文件不存在"
    echo "   请从 env.example 复制并配置"
fi

echo ""

# 检查代码集成
echo "3. 检查代码集成..."

if grep -q "AIOrchestrator" app/services/volume_split_service.py; then
    echo "✅ volume_split_service.py 已集成 AIOrchestrator"
else
    echo "⚠️  volume_split_service.py 未集成 AIOrchestrator"
fi

if grep -q "def invoke" app/services/llm_service.py; then
    echo "✅ llm_service.py 已添加 invoke() 方法"
else
    echo "❌ llm_service.py 缺少 invoke() 方法"
fi

echo ""

# 显示配置摘要
echo "4. 配置摘要..."
echo ""
echo "支持的Provider:"
echo "  - siliconflow (硅基流动)"
echo "  - gemini (Google Gemini)"
echo "  - openai (OpenAI)"
echo "  - deepseek (DeepSeek)"
echo ""
echo "已配置的AI功能:"
echo "  F01: 概念对话 -> Gemini Flash"
echo "  F02: 蓝图生成 -> DeepSeek-V3"
echo "  F03: 批量大纲 -> DeepSeek-V3"
echo "  F04: 章节正文 -> DeepSeek-V3"
echo "  F05: 章节摘要 -> Gemini Flash"
echo "  F06: 基础分析 -> Gemini Flash"
echo "  F07: 增强分析 -> DeepSeek-V3"
echo "  F08: 角色追踪 -> Gemini Flash"
echo "  F09: 世界观扩展 -> DeepSeek-V3"
echo "  F10: 卷名生成 -> Gemini Flash"
echo ""

# 总结
echo "=========================================="
echo "验证完成"
echo "=========================================="
echo ""
echo "下一步:"
echo "1. 在 .env 中设置 SILICONFLOW_API_KEY 和 GEMINI_API_KEY"
echo "2. 重启应用: pm2 restart all"
echo "3. 测试卷名生成功能"
echo "4. 查看日志确认使用了正确的API"
echo ""

