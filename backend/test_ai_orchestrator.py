"""
测试 AI Orchestrator 功能

验证不同AI功能使用不同的API
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.config.ai_function_config import AIFunctionType, get_function_config


def test_config():
    """测试配置是否正确加载"""
    print("=" * 60)
    print("测试 AI 功能配置")
    print("=" * 60)
    print()
    
    # 测试所有功能配置
    for function_type in AIFunctionType:
        config = get_function_config(function_type)
        if config:
            print(f"✅ {function_type.value}")
            print(f"   主模型: {config.primary.provider}/{config.primary.model}")
            print(f"   温度: {config.temperature}, 超时: {config.timeout}s")
            print(f"   必须成功: {config.required}")
            if config.fallbacks:
                print(f"   备用模型: {len(config.fallbacks)} 个")
                for idx, fb in enumerate(config.fallbacks, 1):
                    print(f"     {idx}. {fb.provider}/{fb.model}")
            print()
        else:
            print(f"❌ {function_type.value} - 未配置")
            print()


def check_env_vars():
    """检查环境变量"""
    print("=" * 60)
    print("检查环境变量")
    print("=" * 60)
    print()
    
    required_keys = [
        "SILICONFLOW_API_KEY",
        "GEMINI_API_KEY",
    ]
    
    optional_keys = [
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
    ]
    
    all_ok = True
    
    for key in required_keys:
        value = os.getenv(key)
        if value:
            print(f"✅ {key}: {value[:20]}...")
        else:
            print(f"❌ {key}: 未设置")
            all_ok = False
    
    print()
    print("可选环境变量:")
    for key in optional_keys:
        value = os.getenv(key)
        if value:
            print(f"✅ {key}: {value[:20]}...")
        else:
            print(f"⚠️  {key}: 未设置")
    
    print()
    return all_ok


async def test_orchestrator():
    """测试 Orchestrator 实际调用"""
    print("=" * 60)
    print("测试 AI Orchestrator 调用")
    print("=" * 60)
    print()
    
    # 这里需要数据库连接，暂时跳过
    print("⚠️  实际调用测试需要数据库连接，请在应用中测试")
    print()
    print("建议测试步骤:")
    print("1. 设置环境变量 SILICONFLOW_API_KEY 和 GEMINI_API_KEY")
    print("2. 启动应用")
    print("3. 触发卷名生成功能")
    print("4. 查看日志确认使用了 Gemini API")
    print()


def main():
    """主函数"""
    print()
    print("🚀 AI Orchestrator 测试工具")
    print()
    
    # 测试配置
    test_config()
    
    # 检查环境变量
    env_ok = check_env_vars()
    
    # 测试调用
    asyncio.run(test_orchestrator())
    
    # 总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    print()
    if env_ok:
        print("✅ 配置正确，可以开始使用")
        print()
        print("下一步:")
        print("1. 在 .env 文件中设置 API Keys")
        print("2. 重启应用")
        print("3. 测试不同功能是否使用了对应的 API")
    else:
        print("❌ 请先设置必需的环境变量")
        print()
        print("在 .env 文件中添加:")
        print("SILICONFLOW_API_KEY=your-key-here")
        print("GEMINI_API_KEY=your-key-here")
    print()


if __name__ == "__main__":
    main()

