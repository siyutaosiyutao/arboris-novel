"""
AI Orchestrator 辅助函数

提供便捷的方法来使用Orchestrator，简化现有代码的集成
"""
import logging
from typing import Optional, List, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from ..config.ai_function_config import AIFunctionType
from ..services.ai_orchestrator import AIOrchestrator
from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)


async def call_ai_function(
    db_session: AsyncSession,
    function: AIFunctionType,
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: Optional[float] = None,
    timeout: Optional[float] = None,
    user_id: Optional[int] = None,
    response_format: Optional[str] = "json_object",
) -> str:
    """
    便捷方法：调用AI功能
    
    使用示例:
        response = await call_ai_function(
            db_session=db,
            function=AIFunctionType.CHAPTER_CONTENT_WRITING,
            system_prompt="你是专业的小说作家...",
            user_prompt="请生成第1章...",
            user_id=user_id,
        )
    """
    llm_service = LLMService(db_session)
    orchestrator = AIOrchestrator(llm_service, db_session)
    
    return await orchestrator.execute(
        function=function,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        timeout=timeout,
        user_id=user_id,
        response_format=response_format,
    )


async def generate_chapter_content(
    db_session: AsyncSession,
    system_prompt: str,
    user_prompt: str,
    user_id: int,
    temperature: float = 0.9,
    timeout: float = 600.0,
) -> str:
    """
    生成章节正文
    
    替代原来的:
        response = await llm_service.get_llm_response(
            system_prompt=writer_prompt,
            conversation_history=[{"role": "user", "content": prompt_input}],
            temperature=0.9,
            user_id=user_id,
            timeout=600.0,
        )
    
    改为:
        response = await generate_chapter_content(
            db_session=db,
            system_prompt=writer_prompt,
            user_prompt=prompt_input,
            user_id=user_id,
        )
    """
    return await call_ai_function(
        db_session=db_session,
        function=AIFunctionType.CHAPTER_CONTENT_WRITING,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        timeout=timeout,
        user_id=user_id,
        response_format="json_object",
    )


async def generate_outline(
    db_session: AsyncSession,
    system_prompt: str,
    user_prompt: str,
    user_id: int,
    temperature: float = 0.7,
    timeout: float = 360.0,
) -> str:
    """生成大纲"""
    return await call_ai_function(
        db_session=db_session,
        function=AIFunctionType.OUTLINE_GENERATION,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        timeout=timeout,
        user_id=user_id,
        response_format="json_object",
    )


async def generate_summary(
    db_session: AsyncSession,
    chapter_content: str,
    user_id: int,
    system_prompt: Optional[str] = None,
    temperature: float = 0.15,
    timeout: float = 180.0,
) -> str:
    """
    生成章节摘要
    
    替代原来的:
        summary = await llm_service.get_summary(
            chapter_content=content,
            temperature=0.2,
            user_id=user_id,
            timeout=180.0
        )
    
    改为:
        summary = await generate_summary(
            db_session=db,
            chapter_content=content,
            user_id=user_id,
        )
    """
    if not system_prompt:
        from ..services.prompt_service import PromptService
        prompt_service = PromptService(db_session)
        system_prompt = await prompt_service.get_prompt("extraction")
        if not system_prompt:
            raise ValueError("未配置摘要提示词")
    
    return await call_ai_function(
        db_session=db_session,
        function=AIFunctionType.SUMMARY_EXTRACTION,
        system_prompt=system_prompt,
        user_prompt=chapter_content,
        temperature=temperature,
        timeout=timeout,
        user_id=user_id,
        response_format=None,  # 摘要不需要JSON格式
    )


async def evaluate_chapter(
    db_session: AsyncSession,
    system_prompt: str,
    evaluation_payload: Dict,
    user_id: int,
    temperature: float = 0.3,
    timeout: float = 360.0,
) -> str:
    """评估章节版本"""
    import json
    
    return await call_ai_function(
        db_session=db_session,
        function=AIFunctionType.BASIC_ANALYSIS,  # 使用基础分析功能
        system_prompt=system_prompt,
        user_prompt=json.dumps(evaluation_payload, ensure_ascii=False),
        temperature=temperature,
        timeout=timeout,
        user_id=user_id,
        response_format="json_object",
    )


async def concept_dialogue(
    db_session: AsyncSession,
    system_prompt: str,
    user_message: str,
    user_id: int,
    temperature: float = 0.8,
    timeout: float = 240.0,
) -> str:
    """概念对话"""
    return await call_ai_function(
        db_session=db_session,
        function=AIFunctionType.CONCEPT_DIALOGUE,
        system_prompt=system_prompt,
        user_prompt=user_message,
        temperature=temperature,
        timeout=timeout,
        user_id=user_id,
        response_format="json_object",
    )


# 向后兼容：提供一个包装器，让现有代码可以逐步迁移
class OrchestratorWrapper:
    """
    包装器类，提供与LLMService相同的接口
    
    使用方法:
        # 原来的代码
        llm_service = LLMService(db)
        
        # 改为
        llm_service = OrchestratorWrapper(db)
        
        # 其他代码不变
        response = await llm_service.get_llm_response(...)
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.llm_service = LLMService(db_session)
        self.orchestrator = AIOrchestrator(self.llm_service, db_session)
    
    async def get_llm_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        *,
        temperature: float = 0.7,
        user_id: Optional[int] = None,
        timeout: float = 300.0,
        response_format: Optional[str] = "json_object",
    ) -> str:
        """
        兼容原有的get_llm_response接口
        自动根据上下文选择合适的AI功能
        """
        # 简单的启发式：根据temperature和timeout推断功能类型
        if timeout >= 600:
            function = AIFunctionType.CHAPTER_CONTENT_WRITING
        elif timeout >= 360:
            function = AIFunctionType.OUTLINE_GENERATION
        elif timeout >= 180:
            function = AIFunctionType.BASIC_ANALYSIS
        else:
            function = AIFunctionType.SUMMARY_EXTRACTION
        
        # 提取用户消息
        user_prompt = ""
        for msg in conversation_history:
            if msg["role"] == "user":
                user_prompt = msg["content"]
                break
        
        return await self.orchestrator.execute(
            function=function,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            timeout=timeout,
            user_id=user_id,
            response_format=response_format,
        )
    
    async def get_summary(
        self,
        chapter_content: str,
        *,
        temperature: float = 0.2,
        user_id: Optional[int] = None,
        timeout: float = 180.0,
        system_prompt: Optional[str] = None,
    ) -> str:
        """兼容原有的get_summary接口"""
        return await generate_summary(
            db_session=self.db_session,
            chapter_content=chapter_content,
            user_id=user_id,
            system_prompt=system_prompt,
            temperature=temperature,
            timeout=timeout,
        )
    
    # 其他方法直接委托给原始LLMService
    async def get_embedding(self, *args, **kwargs):
        return await self.llm_service.get_embedding(*args, **kwargs)
    
    async def get_embedding_dimension(self, *args, **kwargs):
        return await self.llm_service.get_embedding_dimension(*args, **kwargs)

