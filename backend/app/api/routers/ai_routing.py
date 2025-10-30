"""
AI路由管理API

提供管理AI提供商和功能路由的接口
"""
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.deps import get_current_user, get_session
from ...models.user import User
from ...models.ai_routing import AIProvider, AIFunctionRoute, AIFunctionCallLog
from ...repositories.ai_routing_repository import (
    AIProviderRepository,
    AIFunctionRouteRepository,
    AIFunctionCallLogRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-routing", tags=["AI路由管理"])


# ==================== Schemas ====================

class AIProviderSchema(BaseModel):
    id: int
    name: str
    display_name: str
    base_url: str
    status: str
    priority: int
    cost_per_1k_tokens: Optional[float] = None

    class Config:
        from_attributes = True


class AIFunctionRouteSchema(BaseModel):
    id: int
    function_type: str
    display_name: str
    primary_provider_id: int
    primary_model: str
    temperature: float
    timeout_seconds: int
    max_retries: int
    enabled: bool

    class Config:
        from_attributes = True


class AICallLogSchema(BaseModel):
    id: int
    function_type: str
    provider_id: Optional[int]
    model: Optional[str]
    status: str
    is_fallback: bool
    duration_ms: Optional[int]
    error_type: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_calls: int
    success_rate: float
    avg_duration_ms: int
    total_cost_usd: float
    by_function: dict
    by_provider: dict


# ==================== API Endpoints ====================

@router.get("/providers", response_model=List[AIProviderSchema])
async def list_providers(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取所有AI提供商列表"""
    repo = AIProviderRepository(session)
    providers = await repo.get_all_active()
    return providers


@router.get("/routes", response_model=List[AIFunctionRouteSchema])
async def list_routes(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取所有功能路由配置"""
    repo = AIFunctionRouteRepository(session)
    routes = await repo.get_all_enabled()
    return routes


@router.get("/routes/{function_type}", response_model=AIFunctionRouteSchema)
async def get_route(
    function_type: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取指定功能的路由配置"""
    repo = AIFunctionRouteRepository(session)
    route = await repo.get_by_function_type(function_type)
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到功能 {function_type} 的路由配置"
        )
    
    return route


@router.get("/logs", response_model=List[AICallLogSchema])
async def list_logs(
    function_type: Optional[str] = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取AI调用日志"""
    repo = AIFunctionCallLogRepository(session)
    logs = await repo.get_recent_logs(function_type=function_type, limit=limit)
    
    return [
        AICallLogSchema(
            id=log.id,
            function_type=log.function_type,
            provider_id=log.provider_id,
            model=log.model,
            status=log.status,
            is_fallback=log.is_fallback,
            duration_ms=log.duration_ms,
            error_type=log.error_type,
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    function_type: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取统计信息"""
    repo = AIFunctionCallLogRepository(session)
    stats = await repo.get_stats(function_type=function_type)
    
    return StatsResponse(
        total_calls=stats.get("total_calls", 0),
        success_rate=stats.get("success_rate", 0.0),
        avg_duration_ms=stats.get("avg_duration_ms", 0),
        total_cost_usd=stats.get("total_cost_usd", 0.0),
        by_function=stats.get("by_function", {}),
        by_provider=stats.get("by_provider", {}),
    )


# ==================== 配置更新API ====================

class UpdateRouteRequest(BaseModel):
    primary_provider_id: Optional[int] = None
    primary_model: Optional[str] = None
    temperature: Optional[float] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    enabled: Optional[bool] = None


@router.patch("/routes/{function_type}")
async def update_route(
    function_type: str,
    request: UpdateRouteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    更新功能路由配置
    
    注意：需要管理员权限
    """
    # TODO: 添加管理员权限检查
    
    repo = AIFunctionRouteRepository(session)
    route = await repo.get_by_function_type(function_type)
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到功能 {function_type} 的路由配置"
        )
    
    # 更新字段
    if request.primary_provider_id is not None:
        route.primary_provider_id = request.primary_provider_id
    if request.primary_model is not None:
        route.primary_model = request.primary_model
    if request.temperature is not None:
        route.temperature = request.temperature
    if request.timeout_seconds is not None:
        route.timeout_seconds = request.timeout_seconds
    if request.max_retries is not None:
        route.max_retries = request.max_retries
    if request.enabled is not None:
        route.enabled = request.enabled
    
    # 增加版本号
    route.version += 1
    
    await repo.update(route)
    await session.commit()
    
    logger.info(
        f"用户 {current_user.id} 更新了功能 {function_type} 的路由配置，"
        f"版本号: {route.version}"
    )
    
    return {"message": "配置更新成功", "version": route.version}


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": "ai-routing",
        "version": "1.0.0"
    }

