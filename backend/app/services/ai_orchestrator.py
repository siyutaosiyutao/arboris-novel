"""
AI Orchestrator - AI功能路由和调度层

根据功能类型自动选择对应的API提供商和模型
支持fallback和重试机制
"""

import logging
from typing import Dict, List, Optional

from ..config.ai_function_config import (
    AIFunctionType,
    FunctionRouteConfig,
    ProviderConfig,
    get_function_config,
)
from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """AI功能调度器，负责根据功能类型路由到对应的模型"""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def execute(
        self,
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
        执行AI功能调用
        
        Args:
            function: AI功能类型
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数（可选，默认使用配置中的值）
            timeout: 超时时间（可选，默认使用配置中的值）
            user_id: 用户ID
            response_format: 响应格式
            
        Returns:
            LLM响应文本
            
        Raises:
            ValueError: 如果功能类型未配置
            HTTPException: 如果所有尝试都失败
        """
        # 获取功能配置
        config = get_function_config(function)
        if not config:
            raise ValueError(f"未找到功能 {function} 的配置")

        # 使用配置中的参数，如果调用时未指定
        final_temperature = temperature if temperature is not None else config.temperature
        final_timeout = timeout if timeout is not None else config.timeout

        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        logger.info(
            f"执行AI功能: {function.value}, 主模型: {config.primary.provider}/{config.primary.model}"
        )

        # 构建尝试列表：主模型 + 备用模型
        attempts = [config.primary] + config.fallbacks

        last_error = None

        # 依次尝试每个模型
        for idx, provider_config in enumerate(attempts):
            is_fallback = idx > 0
            attempt_label = f"备用模型{idx}" if is_fallback else "主模型"

            logger.info(
                f"尝试 {attempt_label}: {provider_config.provider}/{provider_config.model}"
            )

            try:
                # 调用LLMService.invoke
                response = await self.llm_service.invoke(
                    provider=provider_config.provider,
                    model=provider_config.model,
                    messages=messages,
                    temperature=final_temperature,
                    timeout=final_timeout,
                    response_format=response_format,
                    user_id=user_id,
                )

                logger.info(
                    f"✅ {attempt_label} 调用成功: {provider_config.provider}/{provider_config.model}"
                )
                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    f"❌ {attempt_label} 调用失败: {provider_config.provider}/{provider_config.model}, "
                    f"错误: {str(e)}"
                )

                # 如果还有备用模型，继续尝试
                if idx < len(attempts) - 1:
                    logger.info(f"切换到下一个模型...")
                    continue
                else:
                    # 所有模型都失败了
                    if config.required:
                        # 必须成功的功能，抛出错误
                        logger.error(
                            f"所有模型都失败了，功能 {function.value} 无法完成"
                        )
                        raise last_error
                    else:
                        # 可选功能，返回默认值
                        logger.warning(
                            f"所有模型都失败了，功能 {function.value} 返回默认值"
                        )
                        return self._get_default_response(function)

        # 理论上不会到这里
        raise last_error

    def _get_default_response(self, function: AIFunctionType) -> str:
        """
        为可选功能返回默认响应
        """
        defaults = {
            AIFunctionType.VOLUME_NAMING: '{"title": "未命名卷"}',
            AIFunctionType.ENHANCED_ANALYSIS: "{}",
            AIFunctionType.CHARACTER_TRACKING: "{}",
            AIFunctionType.WORLDVIEW_EXPANSION: "{}",
        }
        return defaults.get(function, "{}")

    async def execute_batch(
        self,
        function: AIFunctionType,
        prompts: List[Dict[str, str]],
        *,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
        user_id: Optional[int] = None,
        response_format: Optional[str] = "json_object",
    ) -> List[str]:
        """
        批量执行AI功能调用
        
        Args:
            function: AI功能类型
            prompts: 提示词列表，每个元素包含 system_prompt 和 user_prompt
            其他参数同 execute()
            
        Returns:
            响应列表
        """
        results = []
        for prompt in prompts:
            try:
                result = await self.execute(
                    function=function,
                    system_prompt=prompt["system_prompt"],
                    user_prompt=prompt["user_prompt"],
                    temperature=temperature,
                    timeout=timeout,
                    user_id=user_id,
                    response_format=response_format,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"批量调用失败: {str(e)}")
                # 根据配置决定是否继续
                config = get_function_config(function)
                if config and not config.required:
                    results.append(self._get_default_response(function))
                else:
                    raise

        return results

