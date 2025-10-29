"""超级分析服务 - 拆分为基础分析和增强分析（修订版）

解决问题：
- #1: 拆分超级分析为 2 次调用，降低失败率
- #8: 添加数据验证
- #10: 实现自动降级策略
- #13: 增加 timeout 到 600 秒
"""
import json
import logging
from typing import Optional, Tuple, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from .llm_service import LLMService
from ..utils.json_utils import remove_think_tags, unwrap_markdown_json

logger = logging.getLogger(__name__)


class SuperAnalysisService:
    """超级分析服务：拆分为基础分析和增强分析"""
    
    def __init__(self, db: AsyncSession, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service
    
    async def analyze_chapter(
        self,
        chapter_number: int,
        chapter_content: str,
        blueprint: dict,
        user_id: int
    ) -> Tuple[dict, Optional[dict]]:
        """
        超级分析：拆分为 2 次调用
        
        返回：(基础分析结果, 增强分析结果或None)
        """
        
        # 第一次调用：基础分析（必须成功）
        basic_result = await self._basic_analysis(
            chapter_number,
            chapter_content,
            user_id
        )
        
        # 第二次调用：增强分析（可选，失败不影响）
        enhanced_result = None
        try:
            enhanced_result = await self._enhanced_analysis(
                chapter_number,
                chapter_content,
                blueprint,
                user_id
            )
        except Exception as e:
            logger.warning(f"增强分析失败（不影响基础功能）：{e}")
        
        return basic_result, enhanced_result
    
    async def _basic_analysis(
        self,
        chapter_number: int,
        chapter_content: str,
        user_id: int
    ) -> dict:
        """
        基础分析：摘要 + 关键事件
        
        返回格式：
        {
            "summary": "章节摘要",
            "key_events": ["事件1", "事件2"]
        }
        """
        
        prompt = f"""请分析以下章节内容，提取摘要和关键事件。

**章节内容**：
{chapter_content}

**要求**：
1. 生成 100-200 字的章节摘要
2. 提取 3-5 个关键事件（每个事件用一句话描述）

**输出格式**（JSON）：
{{
  "summary": "章节摘要",
  "key_events": ["事件1", "事件2", "事件3"]
}}
"""
        
        try:
            response = await self.llm_service.get_llm_response(
                system_prompt="你是专业的小说分析专家。",
                conversation_history=[{"role": "user", "content": prompt}],
                temperature=0.3,
                user_id=user_id,
                timeout=180.0
            )
            
            result = self._parse_json_response(response)
            
            # 验证必需字段
            if not self._validate_basic_result(result):
                raise ValueError("基础分析结果格式错误")
            
            logger.info(f"基础分析完成：第 {chapter_number} 章")
            return result
            
        except Exception as e:
            logger.error(f"基础分析失败：{e}")
            # 返回默认值（确保不会卡住）
            return {
                "summary": f"第 {chapter_number} 章内容摘要生成失败",
                "key_events": []
            }
    
    async def _enhanced_analysis(
        self,
        chapter_number: int,
        chapter_content: str,
        blueprint: dict,
        user_id: int
    ) -> dict:
        """
        增强分析：角色追踪 + 新角色 + 世界观 + 伏笔
        
        返回格式：
        {
            "character_changes": [...],
            "new_characters": [...],
            "world_extensions": {...},
            "foreshadowings": [...]
        }
        """
        
        # 构建提示词（包含蓝图信息）
        prompt = self._build_enhanced_prompt(
            chapter_number,
            chapter_content,
            blueprint
        )
        
        response = await self.llm_service.get_llm_response(
            system_prompt="你是专业的小说分析专家，擅长角色追踪和世界观分析。",
            conversation_history=[{"role": "user", "content": prompt}],
            temperature=0.3,
            user_id=user_id,
            timeout=600.0  # ✅ 增加 timeout（解决问题 #13）
        )
        
        result = self._parse_json_response(response)
        
        # 验证格式（不抛出异常，只记录警告）
        if not self._validate_enhanced_result(result):
            logger.warning(f"增强分析结果格式不完整：{result.keys()}")
        
        logger.info(f"增强分析完成：第 {chapter_number} 章")
        return result
    
    def _parse_json_response(self, response: str) -> dict:
        """
        ✅ 增强的 JSON 解析（解决问题 #8）
        
        支持多种格式：
        1. 标准 JSON
        2. Markdown 代码块包裹的 JSON
        3. 包含 <think> 标签的 JSON
        """
        # 使用现有工具函数
        cleaned = remove_think_tags(response)
        normalized = unwrap_markdown_json(cleaned)
        
        try:
            return json.loads(normalized)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            logger.error(f"原始响应: {response[:500]}...")
            raise
    
    def _validate_basic_result(self, result: dict) -> bool:
        """✅ 验证基础分析结果（解决问题 #8）"""
        if not isinstance(result, dict):
            return False
        if "summary" not in result:
            return False
        if "key_events" not in result or not isinstance(result["key_events"], list):
            return False
        return True
    
    def _validate_enhanced_result(self, result: dict) -> bool:
        """✅ 验证增强分析结果（解决问题 #8）"""
        if not isinstance(result, dict):
            return False
        
        # 检查可选字段类型
        if "character_changes" in result and not isinstance(result["character_changes"], list):
            return False
        if "new_characters" in result and not isinstance(result["new_characters"], list):
            return False
        if "world_extensions" in result and not isinstance(result["world_extensions"], dict):
            return False
        if "foreshadowings" in result and not isinstance(result["foreshadowings"], list):
            return False
        
        return True
    
    def _build_enhanced_prompt(
        self,
        chapter_number: int,
        chapter_content: str,
        blueprint: dict
    ) -> str:
        """构建增强分析提示词"""
        
        characters_info = json.dumps(blueprint.get("characters", []), ensure_ascii=False, indent=2)
        world_setting = json.dumps(blueprint.get("world_setting", {}), ensure_ascii=False, indent=2)
        
        return f"""请分析第 {chapter_number} 章，识别角色变化、新角色、世界观扩展和伏笔。

**章节内容**：
{chapter_content}

**已知角色**：
{characters_info}

**已知世界观**：
{world_setting}

**要求**：
1. 识别角色状态变化（能力、性格、关系等）
2. 识别新出现的角色（只记录主要角色和配角，忽略龙套）
3. 识别新的世界观元素（地点、势力、物品、规则）
4. 识别伏笔（未解决的谜团、暗示的未来事件）

**输出格式**（JSON）：
{{
  "character_changes": [
    {{
      "name": "角色名",
      "changes": "变化描述",
      "growth_level": 5
    }}
  ],
  "new_characters": [
    {{
      "name": "新角色名",
      "importance": "main/supporting/minor",
      "description": "简要描述"
    }}
  ],
  "world_extensions": {{
    "locations": ["新地点1", "新地点2"],
    "factions": ["新势力1"],
    "items": ["新物品1"],
    "rules": ["新规则1"]
  }},
  "foreshadowings": [
    {{
      "content": "伏笔内容",
      "type": "mystery/prophecy/hint",
      "confidence": 0.8
    }}
  ]
}}
"""

