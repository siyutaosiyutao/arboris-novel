import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, BadRequestError, InternalServerError

from ..core.config import settings
from ..config.ai_function_config import get_provider_base_url, get_provider_env_key
from ..repositories.llm_config_repository import LLMConfigRepository
from ..repositories.system_config_repository import SystemConfigRepository
from ..repositories.user_repository import UserRepository
from ..services.admin_setting_service import AdminSettingService
from ..services.prompt_service import PromptService
from ..services.usage_service import UsageService
from ..utils.llm_tool import ChatMessage, LLMClient

logger = logging.getLogger(__name__)

try:  # pragma: no cover - 运行环境未安装时兼容
    from ollama import AsyncClient as OllamaAsyncClient
except ImportError:  # pragma: no cover - Ollama 为可选依赖
    OllamaAsyncClient = None


class LLMService:
    """封装与大模型交互的所有逻辑，包括配额控制与配置选择。"""

    def __init__(self, session):
        self.session = session
        self.llm_repo = LLMConfigRepository(session)
        self.system_config_repo = SystemConfigRepository(session)
        self.user_repo = UserRepository(session)
        self.admin_setting_service = AdminSettingService(session)
        self.usage_service = UsageService(session)
        self._embedding_dimensions: Dict[str, int] = {}
        self._fallback_endpoints: Optional[List[Dict[str, str]]] = None

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
        messages = [{"role": "system", "content": system_prompt}, *conversation_history]
        return await self._stream_and_collect(
            messages,
            temperature=temperature,
            user_id=user_id,
            timeout=timeout,
            response_format=response_format,
        )

    async def invoke(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.7,
        timeout: float = 300.0,
        response_format: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> str:
        """
        统一的LLM调用接口，支持指定provider和model

        Args:
            provider: API提供商 ("siliconflow" / "gemini" / "openai" / "deepseek")
            model: 模型名称
            messages: 消息列表
            temperature: 温度参数
            timeout: 超时时间
            response_format: 响应格式
            user_id: 用户ID（用于配额控制）

        Returns:
            LLM响应文本
        """
        # 获取provider配置
        base_url = get_provider_base_url(provider)
        env_key = get_provider_env_key(provider)

        # ✅ 统一从环境变量获取API Key
        api_key = os.getenv(env_key)

        # ✅ 如果环境变量没有，尝试从数据库配置获取（统一处理所有provider）
        if not api_key and self.db_session:
            try:
                from ..repositories.ai_routing_repository import AIProviderRepository
                provider_repo = AIProviderRepository(self.db_session)
                provider_obj = await provider_repo.get_by_name(provider)
                if provider_obj and provider_obj.metadata:
                    import json
                    metadata = json.loads(provider_obj.metadata)
                    api_key = metadata.get("api_key")
            except Exception as e:
                logger.warning(f"从数据库获取API Key失败: {e}")

        if not api_key:
            raise HTTPException(
                status_code=500,
                detail=f"未配置 {provider} 的 API Key，请设置环境变量 {env_key}"
            )

        # 构建端点配置
        endpoint_config = {
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
        }

        logger.info(
            f"调用 {provider} API: model={model}, base_url={base_url}, messages={len(messages)}"
        )

        # 使用现有的调用逻辑
        chat_messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in messages]

        try:
            client = LLMClient(
                api_key=endpoint_config["api_key"],
                base_url=endpoint_config.get("base_url")
            )

            full_response = ""
            finish_reason = None

            # ✅ 修复：安全累积chunk内容，容错处理不同类型的chunk
            async for chunk in client.stream_chat(
                messages=chat_messages,
                model=endpoint_config["model"],
                temperature=temperature,
                timeout=timeout,
                response_format=response_format,
            ):
                # 处理不同类型的chunk
                if isinstance(chunk, str):
                    # Legacy string chunks
                    full_response += chunk
                elif isinstance(chunk, dict):
                    # Structured chunks with metadata
                    content = chunk.get("content", "")
                    if content:
                        full_response += content
                    # 记录finish reason（如果有）
                    if "finish_reason" in chunk:
                        finish_reason = chunk["finish_reason"]
                else:
                    # 其他类型，尝试转换为字符串
                    full_response += str(chunk)

            # 记录使用量
            if user_id:
                await self.usage_service.increment_usage(user_id)

            logger.info(
                f"{provider} API 调用成功，响应长度: {len(full_response)}, "
                f"finish_reason: {finish_reason or 'N/A'}"
            )
            return full_response

        except Exception as e:
            logger.error(f"{provider} API 调用失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"{provider} API 调用失败: {str(e)}"
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
        if not system_prompt:
            prompt_service = PromptService(self.session)
            system_prompt = await prompt_service.get_prompt("extraction")
        if not system_prompt:
            logger.error("未配置名为 'extraction' 的摘要提示词，无法生成章节摘要")
            raise HTTPException(status_code=500, detail="未配置摘要提示词，请联系管理员配置 'extraction' 提示词")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": chapter_content},
        ]
        return await self._stream_and_collect(messages, temperature=temperature, user_id=user_id, timeout=timeout)

    async def _stream_and_collect(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float,
        user_id: Optional[int],
        timeout: float,
        response_format: Optional[str] = None,
    ) -> str:
        # 获取用户配置的端点列表（可能包含多个 API Key）
        user_endpoints = await self._resolve_llm_config(user_id)

        # 构建端点列表：用户端点 + 备用端点
        endpoints = user_endpoints
        fallback_endpoints = self._parse_fallback_endpoints()
        endpoints.extend(fallback_endpoints)

        chat_messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in messages]

        last_error = None

        # 尝试每个端点
        for idx, endpoint_config in enumerate(endpoints):
            is_fallback = idx > 0
            endpoint_label = f"备用端点{idx}" if is_fallback else "主端点"

            logger.info(
                "尝试 %s: model=%s base_url=%s user_id=%s messages=%d",
                endpoint_label,
                endpoint_config.get("model"),
                endpoint_config.get("base_url"),
                user_id,
                len(messages),
            )

            try:
                client = LLMClient(
                    api_key=endpoint_config["api_key"],
                    base_url=endpoint_config.get("base_url")
                )

                full_response = ""
                finish_reason = None

                async for part in client.stream_chat(
                    messages=chat_messages,
                    model=endpoint_config.get("model"),
                    temperature=temperature,
                    timeout=int(timeout),
                    response_format=response_format,
                ):
                    if part.get("content"):
                        full_response += part["content"]
                    if part.get("finish_reason"):
                        finish_reason = part["finish_reason"]

                # 成功获取响应
                if is_fallback:
                    logger.info(f"✅ {endpoint_label} 调用成功，已切换到备用端点")
                return full_response

            except BadRequestError as exc:
                detail = "请求参数错误或 API key 无效"
                response = getattr(exc, "response", None)
                if response is not None:
                    try:
                        payload = response.json()
                        error_data = payload.get("error", {}) if isinstance(payload, dict) else {}
                        detail = error_data.get("message_zh") or error_data.get("message") or detail
                    except Exception:
                        detail = str(exc) or detail
                else:
                    detail = str(exc) or detail

                logger.warning(
                    "%s 调用失败 (BadRequestError): model=%s detail=%s",
                    endpoint_label,
                    endpoint_config.get("model"),
                    detail,
                )
                last_error = exc

                # 如果还有备用端点，继续尝试
                if idx < len(endpoints) - 1:
                    logger.info(f"切换到下一个端点...")
                    continue

            except InternalServerError as exc:
                detail = "AI 服务内部错误"
                response = getattr(exc, "response", None)
                if response is not None:
                    try:
                        payload = response.json()
                        error_data = payload.get("error", {}) if isinstance(payload, dict) else {}
                        detail = error_data.get("message_zh") or error_data.get("message") or detail
                    except Exception:
                        detail = str(exc) or detail
                else:
                    detail = str(exc) or detail

                logger.warning(
                    "%s 调用失败 (InternalServerError): model=%s detail=%s",
                    endpoint_label,
                    endpoint_config.get("model"),
                    detail,
                )
                last_error = exc

                # 如果还有备用端点，继续尝试
                if idx < len(endpoints) - 1:
                    logger.info(f"切换到下一个端点...")
                    continue

            except (httpx.RemoteProtocolError, httpx.ReadTimeout, APIConnectionError, APITimeoutError) as exc:
                if isinstance(exc, httpx.RemoteProtocolError):
                    detail = "连接被意外中断"
                elif isinstance(exc, (httpx.ReadTimeout, APITimeoutError)):
                    detail = "响应超时"
                else:
                    detail = "无法连接到服务"

                logger.warning(
                    "%s 调用失败 (%s): model=%s detail=%s",
                    endpoint_label,
                    type(exc).__name__,
                    endpoint_config.get("model"),
                    detail,
                )
                last_error = exc

                # 如果还有备用端点，继续尝试
                if idx < len(endpoints) - 1:
                    logger.info(f"切换到下一个端点...")
                    continue

        # 所有端点都失败了
        logger.error("所有 LLM 端点均调用失败，共尝试 %d 个端点", len(endpoints))
        raise HTTPException(
            status_code=503,
            detail=f"所有 AI 服务端点均不可用，请稍后重试。最后错误: {str(last_error)}"
        ) from last_error

        logger.debug(
            "LLM response collected: model=%s user_id=%s finish_reason=%s preview=%s",
            config.get("model"),
            user_id,
            finish_reason,
            full_response[:500],
        )

        if finish_reason == "length":
            logger.warning(
                "LLM response truncated: model=%s user_id=%s response_length=%d",
                config.get("model"),
                user_id,
                len(full_response),
            )
            raise HTTPException(
                status_code=500,
                detail=f"AI 响应因长度限制被截断（已生成 {len(full_response)} 字符），请缩短输入内容或调整模型参数"
            )

        if not full_response:
            logger.error(
                "LLM returned empty response: model=%s user_id=%s finish_reason=%s",
                config.get("model"),
                user_id,
                finish_reason,
            )
            raise HTTPException(
                status_code=500,
                detail=f"AI 未返回有效内容（结束原因: {finish_reason or '未知'}），请稍后重试或联系管理员"
            )

        await self.usage_service.increment("api_request_count")
        logger.info(
            "LLM response success: model=%s user_id=%s chars=%d",
            config.get("model"),
            user_id,
            len(full_response),
        )
        return full_response

    async def _resolve_llm_config(self, user_id: Optional[int]) -> List[Dict[str, Optional[str]]]:
        """解析 LLM 配置，返回端点列表

        如果用户配置了多个 API Key（逗号分隔），则返回多个端点配置
        """
        endpoints = []

        if user_id:
            config = await self.llm_repo.get_by_user(user_id)
            if config and config.llm_provider_api_key:
                # 解析多个 API Key（逗号分隔）
                api_keys = [key.strip() for key in config.llm_provider_api_key.split(",") if key.strip()]

                for api_key in api_keys:
                    endpoints.append({
                        "api_key": api_key,
                        "base_url": config.llm_provider_url,
                        "model": config.llm_provider_model,
                    })

                if endpoints:
                    logger.info(f"用户 {user_id} 配置了 {len(endpoints)} 个 API Key")
                    return endpoints

        # 检查每日使用次数限制
        if user_id:
            await self._enforce_daily_limit(user_id)

        api_key = await self._get_config_value("llm.api_key")
        base_url = await self._get_config_value("llm.base_url")
        model = await self._get_config_value("llm.model")

        if not api_key:
            logger.error("未配置默认 LLM API Key，且用户 %s 未设置自定义 API Key", user_id)
            raise HTTPException(
                status_code=500,
                detail="未配置默认 LLM API Key，请联系管理员配置系统默认 API Key 或在个人设置中配置自定义 API Key"
            )

        return [{"api_key": api_key, "base_url": base_url, "model": model}]

    async def get_embedding(
        self,
        text: str,
        *,
        user_id: Optional[int] = None,
        model: Optional[str] = None,
    ) -> List[float]:
        """生成文本向量，用于章节 RAG 检索，支持 openai 与 ollama 双提供方。"""
        provider = await self._get_config_value("embedding.provider") or "openai"
        default_model = (
            await self._get_config_value("ollama.embedding_model") or "nomic-embed-text:latest"
            if provider == "ollama"
            else await self._get_config_value("embedding.model") or "text-embedding-3-large"
        )
        target_model = model or default_model

        if provider == "ollama":
            if OllamaAsyncClient is None:
                logger.error("未安装 ollama 依赖，无法调用本地嵌入模型。")
                raise HTTPException(status_code=500, detail="缺少 Ollama 依赖，请先安装 ollama 包。")

            base_url = (
                await self._get_config_value("ollama.embedding_base_url")
                or await self._get_config_value("embedding.base_url")
            )
            client = OllamaAsyncClient(host=base_url)
            try:
                response = await client.embeddings(model=target_model, prompt=text)
            except Exception as exc:  # pragma: no cover - 本地服务调用失败
                logger.error(
                    "Ollama 嵌入请求失败: model=%s base_url=%s error=%s",
                    target_model,
                    base_url,
                    exc,
                    exc_info=True,
                )
                return []
            embedding: Optional[List[float]]
            if isinstance(response, dict):
                embedding = response.get("embedding")
            else:
                embedding = getattr(response, "embedding", None)
            if not embedding:
                logger.warning("Ollama 返回空向量: model=%s", target_model)
                return []
            if not isinstance(embedding, list):
                embedding = list(embedding)
        else:
            config = await self._resolve_llm_config(user_id)
            api_key = await self._get_config_value("embedding.api_key") or config["api_key"]
            base_url = await self._get_config_value("embedding.base_url") or config.get("base_url")
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            try:
                response = await client.embeddings.create(
                    input=text,
                    model=target_model,
                )
            except Exception as exc:  # pragma: no cover - 网络或鉴权失败
                logger.error(
                    "OpenAI 嵌入请求失败: model=%s base_url=%s user_id=%s error=%s",
                    target_model,
                    base_url,
                    user_id,
                    exc,
                    exc_info=True,
                )
                return []
            if not response.data:
                logger.warning("OpenAI 嵌入请求返回空数据: model=%s user_id=%s", target_model, user_id)
                return []
            embedding = response.data[0].embedding

        if not isinstance(embedding, list):
            embedding = list(embedding)

        dimension = len(embedding)
        if not dimension:
            vector_size_str = await self._get_config_value("embedding.model_vector_size")
            if vector_size_str:
                dimension = int(vector_size_str)
        if dimension:
            self._embedding_dimensions[target_model] = dimension
        return embedding

    async def get_embedding_dimension(self, model: Optional[str] = None) -> Optional[int]:
        """获取嵌入向量维度，优先返回缓存结果，其次读取配置。"""
        provider = await self._get_config_value("embedding.provider") or "openai"
        default_model = (
            await self._get_config_value("ollama.embedding_model") or "nomic-embed-text:latest"
            if provider == "ollama"
            else await self._get_config_value("embedding.model") or "text-embedding-3-large"
        )
        target_model = model or default_model
        if target_model in self._embedding_dimensions:
            return self._embedding_dimensions[target_model]
        vector_size_str = await self._get_config_value("embedding.model_vector_size")
        return int(vector_size_str) if vector_size_str else None

    async def _enforce_daily_limit(self, user_id: int) -> None:
        limit_str = await self.admin_setting_service.get("daily_request_limit", "100")
        limit = int(limit_str or 10)
        used = await self.user_repo.get_daily_request(user_id)
        if used >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="今日请求次数已达上限，请明日再试或设置自定义 API Key。",
            )
        await self.user_repo.increment_daily_request(user_id)
        await self.session.commit()

    async def _get_config_value(self, key: str) -> Optional[str]:
        record = await self.system_config_repo.get_by_key(key)
        if record:
            return record.value
        # 兼容环境变量，首次迁移时无需立即写入数据库
        env_key = key.upper().replace(".", "_")
        return os.getenv(env_key)

    def _parse_fallback_endpoints(self) -> List[Dict[str, str]]:
        """解析备用端点配置

        格式：url1|key1|model1,url2|key2|model2
        返回：[{"base_url": "url1", "api_key": "key1", "model": "model1"}, ...]
        """
        if self._fallback_endpoints is not None:
            return self._fallback_endpoints

        endpoints_str = settings.llm_fallback_endpoints
        if not endpoints_str:
            self._fallback_endpoints = []
            logger.info("未配置备用 LLM 端点")
            return self._fallback_endpoints

        endpoints = []
        for endpoint_config in endpoints_str.split(","):
            parts = endpoint_config.strip().split("|")
            if len(parts) == 3:
                endpoints.append({
                    "base_url": parts[0].strip(),
                    "api_key": parts[1].strip(),
                    "model": parts[2].strip()
                })

        self._fallback_endpoints = endpoints
        logger.info(f"已加载 {len(endpoints)} 个备用 LLM 端点")
        return endpoints
