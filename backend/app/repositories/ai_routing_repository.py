"""
AI路由系统Repository
"""
import json
import logging
from typing import List, Optional, Dict
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.ai_routing import AIProvider, AIFunctionRoute, AIFunctionCallLog

logger = logging.getLogger(__name__)


class AIProviderRepository:
    """AI提供商Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, provider_id: int) -> Optional[AIProvider]:
        """根据ID获取provider"""
        result = await self.session.execute(
            select(AIProvider).where(AIProvider.id == provider_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[AIProvider]:
        """根据名称获取provider"""
        result = await self.session.execute(
            select(AIProvider).where(AIProvider.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all_active(self) -> List[AIProvider]:
        """获取所有活跃的providers"""
        result = await self.session.execute(
            select(AIProvider)
            .where(AIProvider.status == "active")
            .order_by(AIProvider.priority)
        )
        return list(result.scalars().all())

    async def create(self, provider: AIProvider) -> AIProvider:
        """创建provider"""
        self.session.add(provider)
        await self.session.flush()
        return provider

    async def update(self, provider: AIProvider) -> AIProvider:
        """更新provider"""
        await self.session.flush()
        return provider


class AIFunctionRouteRepository:
    """AI功能路由Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_function_type(self, function_type: str) -> Optional[AIFunctionRoute]:
        """根据功能类型获取路由配置"""
        result = await self.session.execute(
            select(AIFunctionRoute).where(
                and_(
                    AIFunctionRoute.function_type == function_type,
                    AIFunctionRoute.enabled == True
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_all_enabled(self) -> List[AIFunctionRoute]:
        """获取所有启用的路由配置"""
        result = await self.session.execute(
            select(AIFunctionRoute)
            .where(AIFunctionRoute.enabled == True)
            .order_by(AIFunctionRoute.function_type)
        )
        return list(result.scalars().all())

    async def create(self, route: AIFunctionRoute) -> AIFunctionRoute:
        """创建路由配置"""
        self.session.add(route)
        await self.session.flush()
        return route

    async def update(self, route: AIFunctionRoute) -> AIFunctionRoute:
        """更新路由配置"""
        await self.session.flush()
        return route

    async def parse_fallback_configs(self, route: AIFunctionRoute) -> List[Dict]:
        """解析fallback配置"""
        if not route.fallback_configs:
            return []
        try:
            return json.loads(route.fallback_configs)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse fallback_configs for {route.function_type}")
            return []


class AIFunctionCallLogRepository:
    """AI调用日志Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, log: AIFunctionCallLog) -> AIFunctionCallLog:
        """创建调用日志"""
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_recent_logs(
        self,
        function_type: Optional[str] = None,
        limit: int = 100
    ) -> List[AIFunctionCallLog]:
        """获取最近的调用日志"""
        query = select(AIFunctionCallLog).order_by(AIFunctionCallLog.created_at.desc())
        
        if function_type:
            query = query.where(AIFunctionCallLog.function_type == function_type)
        
        query = query.limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_stats(
        self,
        function_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """获取统计信息"""
        # TODO: 实现统计查询
        return {
            "total_calls": 0,
            "success_rate": 0.0,
            "avg_duration_ms": 0,
            "total_cost_usd": 0.0
        }

