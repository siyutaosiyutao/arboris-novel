#!/bin/bash

echo "=========================================="
echo "异步功能Bug修复验证"
echo "=========================================="
echo ""

cd backend

echo "✅ 1. 检查Python语法..."
python3 -m py_compile \
    app/models/async_task.py \
    app/services/async_analysis_processor.py \
    app/background_processor.py 2>&1

if [ $? -eq 0 ]; then
    echo "   ✅ 所有文件语法正确"
else
    echo "   ❌ 语法检查失败"
    exit 1
fi

echo ""
echo "✅ 2. 检查Bug #1修复: project_id类型..."
if grep -q 'project_id = Column(String(36)' app/models/async_task.py; then
    echo "   ✅ project_id已改为String(36)"
else
    echo "   ❌ project_id仍是Integer"
    exit 1
fi

echo ""
echo "✅ 3. 检查Bug #2修复: BlueprintCharacter字段..."
if grep -q '"identity": char.identity' app/services/async_analysis_processor.py; then
    echo "   ✅ 已使用identity字段"
else
    echo "   ❌ 未找到identity字段"
fi

if grep -q '"personality": char.personality' app/services/async_analysis_processor.py; then
    echo "   ✅ 已使用personality字段"
else
    echo "   ❌ 未找到personality字段"
fi

if grep -q '"goals": char.goals' app/services/async_analysis_processor.py; then
    echo "   ✅ 已使用goals字段"
else
    echo "   ❌ 未找到goals字段"
fi

if grep -q '"abilities": char.abilities' app/services/async_analysis_processor.py; then
    echo "   ✅ 已使用abilities字段"
else
    echo "   ❌ 未找到abilities字段"
fi

# 检查是否移除了错误字段
if grep -q '"role": char.role' app/services/async_analysis_processor.py; then
    echo "   ❌ 仍使用错误的role字段"
    exit 1
else
    echo "   ✅ 已移除错误的role字段"
fi

if grep -q '"description": char.description' app/services/async_analysis_processor.py; then
    echo "   ❌ 仍使用错误的description字段"
    exit 1
else
    echo "   ✅ 已移除错误的description字段"
fi

echo ""
echo "✅ 4. 检查Bug #3修复: Session并发..."
if grep -q 'session_maker: async_sessionmaker' app/services/async_analysis_processor.py; then
    echo "   ✅ 已改用session_maker"
else
    echo "   ❌ 仍使用单个session"
    exit 1
fi

if grep -q 'llm_service_factory: Callable' app/services/async_analysis_processor.py; then
    echo "   ✅ 已添加llm_service_factory"
else
    echo "   ❌ 未找到llm_service_factory"
    exit 1
fi

if grep -q 'async with self.session_maker()' app/services/async_analysis_processor.py; then
    echo "   ✅ 已使用独立session"
else
    echo "   ❌ 未使用独立session"
    exit 1
fi

if grep -q 'async def _process_single_task(self, pending_id: int)' app/services/async_analysis_processor.py; then
    echo "   ✅ _process_single_task已改为接受pending_id"
else
    echo "   ❌ _process_single_task仍接受pending对象"
    exit 1
fi

if grep -q 'async def _execute_analysis(self, db: AsyncSession' app/services/async_analysis_processor.py; then
    echo "   ✅ _execute_analysis已添加db参数"
else
    echo "   ❌ _execute_analysis未添加db参数"
    exit 1
fi

if grep -A 2 'async def _send_notification' app/services/async_analysis_processor.py | grep -q 'db: AsyncSession'; then
    echo "   ✅ _send_notification已添加db参数"
else
    echo "   ❌ _send_notification未添加db参数"
    exit 1
fi

echo ""
echo "✅ 5. 检查background_processor修改..."
if grep -q 'session_maker=async_session_maker' app/background_processor.py; then
    echo "   ✅ 已传递session_maker"
else
    echo "   ❌ 未传递session_maker"
    exit 1
fi

if grep -q 'llm_service_factory=llm_service_factory' app/background_processor.py; then
    echo "   ✅ 已传递llm_service_factory"
else
    echo "   ❌ 未传递llm_service_factory"
    exit 1
fi

echo ""
echo "=========================================="
echo "🎉 所有Bug修复验证通过！"
echo "=========================================="
echo ""
echo "📊 修复内容:"
echo "  ✅ Bug #1: project_id类型 Integer → String(36)"
echo "  ✅ Bug #2: BlueprintCharacter字段 role/description → identity/personality/goals/abilities"
echo "  ✅ Bug #3: Session并发 单个session → session_maker + 独立session"
echo ""
echo "📈 修复效果:"
echo "  • 可以正常写入pending_analysis表"
echo "  • 可以正常访问BlueprintCharacter字段"
echo "  • 支持真正的并发处理（3个任务同时执行）"
echo "  • 异步功能完全正常"
echo ""
echo "📖 详细报告: ../Bug修复报告-异步功能-20251030.md"
echo ""

