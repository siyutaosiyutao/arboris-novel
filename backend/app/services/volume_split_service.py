"""
自动分卷服务

基于剧情指标自动判定分卷时机，并使用AI生成卷名
"""
import logging
import statistics
from typing import Optional, List, Dict
from datetime import datetime, timezone
from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.novel import Volume, Chapter, ChapterOutline
from ..models.story_metrics import ChapterStoryMetrics
from ..models.auto_generator import AutoGeneratorLog
from ..services.llm_service import LLMService
from ..services.ai_orchestrator import AIOrchestrator
from ..config.ai_function_config import AIFunctionType

logger = logging.getLogger(__name__)


class VolumeSplitService:
    """自动分卷服务"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "enabled": True,
        "min_chapters": 15,           # 最少章节数
        "max_chapters": 30,           # 最多章节数（强制分卷）
        "window_size": 5,             # 评分窗口大小
        "score_threshold": 60,        # 评分阈值
        "cooldown_chapters": 3,       # 冷却章节数
        "naming_model": "deepseek-chat",
        "naming_timeout": 30,
        "fallback_naming": True,      # AI失败时使用fallback
    }
    
    def __init__(self, db: AsyncSession, llm_service: Optional[LLMService] = None):
        self.db = db
        self.llm_service = llm_service
    
    async def evaluate_project(
        self,
        project_id: str,
        task_id: Optional[int] = None,
        config: Optional[dict] = None
    ) -> Optional[Volume]:
        """
        评估项目是否需要分卷
        
        参数:
            project_id: 项目ID
            task_id: 任务ID（用于日志）
            config: 配置（可选，覆盖默认配置）
        
        返回:
            如果创建了新卷，返回Volume对象；否则返回None
        """
        try:
            # 1. 加载配置
            cfg = {**self.DEFAULT_CONFIG, **(config or {})}
            
            if not cfg["enabled"]:
                logger.debug(f"项目 {project_id} 未启用自动分卷")
                return None
            
            # 2. 获取最后一卷
            last_volume = await self._get_last_volume(project_id)
            
            # 3. 计算自上次分卷以来的章节数
            chapters_since_last = await self._count_chapters_since_volume(
                project_id, 
                last_volume.volume_number if last_volume else 0
            )
            
            logger.info(
                f"项目 {project_id} 自上次分卷已生成 {chapters_since_last} 章 "
                f"(最小: {cfg['min_chapters']}, 最大: {cfg['max_chapters']})"
            )
            
            # 4. 检查是否满足最小章节数
            if chapters_since_last < cfg["min_chapters"]:
                return None
            
            # 5. 强制分卷（达到最大章节数）
            if chapters_since_last >= cfg["max_chapters"]:
                logger.info(f"达到最大章节数 {cfg['max_chapters']}，强制分卷")
                return await self._create_volume(
                    project_id=project_id,
                    task_id=task_id,
                    config=cfg,
                    reason="达到最大章节数"
                )
            
            # ✅ 修复4：只在上一卷存在时检查冷却期
            if last_volume and chapters_since_last < cfg["cooldown_chapters"]:
                logger.debug(f"仍在冷却期内（{cfg['cooldown_chapters']} 章）")
                return None
            
            # 7. 加载评分窗口
            metrics_window = await self._load_metrics_window(
                project_id=project_id,
                last_volume_number=last_volume.volume_number if last_volume else 0,
                window_size=cfg["window_size"]
            )
            
            if not metrics_window:
                logger.warning(f"项目 {project_id} 没有足够的剧情指标数据")
                return None
            
            # 8. 评分判定
            avg_score = statistics.mean(m.stage_score for m in metrics_window)
            has_major_event = any(m.major_event_flag for m in metrics_window)
            max_score = max(m.stage_score for m in metrics_window)
            
            logger.info(
                f"评分窗口: avg={avg_score:.1f}, max={max_score}, "
                f"major_event={has_major_event}, threshold={cfg['score_threshold']}"
            )
            
            # 9. 判定是否分卷
            should_split = (
                avg_score >= cfg["score_threshold"] or 
                has_major_event or
                max_score >= 80  # 单章高分也触发
            )
            
            if should_split:
                reason = []
                if avg_score >= cfg["score_threshold"]:
                    reason.append(f"平均评分{avg_score:.1f}")
                if has_major_event:
                    reason.append("重大事件")
                if max_score >= 80:
                    reason.append(f"高潮章节(评分{max_score})")
                
                return await self._create_volume(
                    project_id=project_id,
                    task_id=task_id,
                    config=cfg,
                    reason="、".join(reason),
                    metrics_window=metrics_window
                )
            
            return None
            
        except Exception as e:
            logger.error(f"评估分卷失败: {e}", exc_info=True)
            return None
    
    async def _get_last_volume(self, project_id: str) -> Optional[Volume]:
        """获取最后一卷"""
        stmt = (
            select(Volume)
            .where(Volume.project_id == project_id)
            .order_by(Volume.volume_number.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _count_chapters_since_volume(
        self, 
        project_id: str, 
        last_volume_number: int
    ) -> int:
        """计算自上次分卷以来的章节数"""
        # 获取上一卷的最大章节号
        if last_volume_number > 0:
            stmt = (
                select(func.max(Chapter.chapter_number))
                .where(
                    and_(
                        Chapter.project_id == project_id,
                        Chapter.volume_id == select(Volume.id)
                        .where(
                            and_(
                                Volume.project_id == project_id,
                                Volume.volume_number == last_volume_number
                            )
                        )
                        .scalar_subquery()
                    )
                )
            )
            result = await self.db.execute(stmt)
            last_chapter_in_volume = result.scalar() or 0
        else:
            last_chapter_in_volume = 0
        
        # 计算之后的章节数
        stmt = (
            select(func.count(Chapter.id))
            .where(
                and_(
                    Chapter.project_id == project_id,
                    Chapter.chapter_number > last_chapter_in_volume
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def _load_metrics_window(
        self,
        project_id: str,
        last_volume_number: int,
        window_size: int
    ) -> List[ChapterStoryMetrics]:
        """加载最近N章的剧情指标"""
        # 获取上一卷的最大章节号
        if last_volume_number > 0:
            stmt = (
                select(func.max(Chapter.chapter_number))
                .join(Volume, Chapter.volume_id == Volume.id)
                .where(
                    and_(
                        Chapter.project_id == project_id,
                        Volume.volume_number == last_volume_number
                    )
                )
            )
            result = await self.db.execute(stmt)
            start_chapter = (result.scalar() or 0) + 1
        else:
            start_chapter = 1
        
        # 加载指标
        stmt = (
            select(ChapterStoryMetrics)
            .where(
                and_(
                    ChapterStoryMetrics.project_id == project_id,
                    ChapterStoryMetrics.chapter_number >= start_chapter
                )
            )
            .order_by(ChapterStoryMetrics.chapter_number.desc())
            .limit(window_size)
        )
        result = await self.db.execute(stmt)
        metrics_window = list(result.scalars().all())

        # ✅ 修复6：反向排序，使其按章节号升序
        metrics_window.reverse()

        return metrics_window
    
    async def _create_volume(
        self,
        project_id: str,
        task_id: Optional[int],
        config: dict,
        reason: str,
        metrics_window: Optional[List[ChapterStoryMetrics]] = None
    ) -> Volume:
        """
        创建新卷
        
        流程:
        1. 生成卷名（AI或fallback）
        2. 创建Volume记录
        3. 更新Chapter和ChapterOutline的volume_id
        4. 记录日志
        """
        # 1. 确定章节范围
        last_volume = await self._get_last_volume(project_id)
        new_volume_number = (last_volume.volume_number if last_volume else 0) + 1
        
        # 获取起始章节号
        if last_volume:
            stmt = select(func.max(Chapter.chapter_number)).where(
                Chapter.volume_id == last_volume.id
            )
            result = await self.db.execute(stmt)
            start_chapter = (result.scalar() or 0) + 1
        else:
            start_chapter = 1
        
        # 获取结束章节号（当前最大章节号）
        stmt = select(func.max(Chapter.chapter_number)).where(
            Chapter.project_id == project_id
        )
        result = await self.db.execute(stmt)
        end_chapter = result.scalar() or start_chapter
        
        # 2. 生成卷名
        volume_title = await self._generate_volume_title(
            project_id=project_id,
            volume_number=new_volume_number,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            metrics_window=metrics_window,
            config=config
        )
        
        # 3. 创建Volume
        new_volume = Volume(
            project_id=project_id,
            volume_number=new_volume_number,
            title=volume_title,
            description=f"自动分卷：{reason}"
        )
        self.db.add(new_volume)
        await self.db.flush()  # 获取ID
        
        # 4. 更新Chapter的volume_id
        stmt = (
            update(Chapter)
            .where(
                and_(
                    Chapter.project_id == project_id,
                    Chapter.chapter_number >= start_chapter,
                    Chapter.chapter_number <= end_chapter
                )
            )
            .values(volume_id=new_volume.id)
        )
        await self.db.execute(stmt)
        
        # 5. 更新ChapterOutline的volume_id
        stmt = (
            update(ChapterOutline)
            .where(
                and_(
                    ChapterOutline.project_id == project_id,
                    ChapterOutline.chapter_number >= start_chapter,
                    ChapterOutline.chapter_number <= end_chapter
                )
            )
            .values(volume_id=new_volume.id)
        )
        await self.db.execute(stmt)
        
        await self.db.commit()
        
        # 6. 记录日志
        if task_id:
            log = AutoGeneratorLog(
                task_id=task_id,
                log_type="info",
                message=(
                    f"自动分卷：{volume_title}（第 {start_chapter}-{end_chapter} 章，"
                    f"原因：{reason}）"
                )
            )
            self.db.add(log)
            await self.db.commit()
        
        logger.info(
            f"已创建新卷: {volume_title} (第 {start_chapter}-{end_chapter} 章，原因：{reason})"
        )
        
        return new_volume
    
    async def _generate_volume_title(
        self,
        project_id: str,
        volume_number: int,
        start_chapter: int,
        end_chapter: int,
        metrics_window: Optional[List[ChapterStoryMetrics]],
        config: dict
    ) -> str:
        """
        生成卷名

        使用 AIOrchestrator 调用配置的模型
        """
        # Fallback卷名
        fallback_title = f"卷{self._to_chinese_number(volume_number)}·第{start_chapter}-{end_chapter}章"

        # 如果没有LLM服务或配置禁用AI命名
        if not self.llm_service or not config.get("use_ai_naming", True):
            return fallback_title

        try:
            # 构建提示词
            user_prompt = self._build_naming_prompt(
                volume_number=volume_number,
                start_chapter=start_chapter,
                end_chapter=end_chapter,
                metrics_window=metrics_window
            )

            system_prompt = "你是一位专业的小说编辑，擅长为小说卷章生成富有诗意和吸引力的标题。"

            # ✅ 使用 AIOrchestrator 调用
            orchestrator = AIOrchestrator(self.llm_service)
            response = await orchestrator.execute(
                function=AIFunctionType.VOLUME_NAMING,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=None,  # 卷名不需要JSON格式
            )

            # 提取卷名
            title = self._extract_title_from_response(response, volume_number)

            if title:
                logger.info(f"✅ AI生成卷名: {title}")
                return title
            else:
                logger.warning("AI返回的卷名为空，使用fallback")
                return fallback_title

        except Exception as e:
            logger.error(f"❌ AI生成卷名失败: {e}，使用fallback")
            return fallback_title
    
    def _build_naming_prompt(
        self,
        volume_number: int,
        start_chapter: int,
        end_chapter: int,
        metrics_window: Optional[List[ChapterStoryMetrics]]
    ) -> str:
        """构建卷名生成提示词"""
        # 提取重大事件
        highlights = []
        if metrics_window:
            for m in metrics_window:
                if m.major_event_flag:
                    highlights.append(f"第{m.chapter_number}章触发重大事件（评分{m.stage_score}）")
        
        highlights_text = "\n".join(highlights) if highlights else "无明显重大事件"
        
        return f"""请为小说的第{volume_number}卷生成一个富有诗意和吸引力的卷名。

**卷信息**:
- 卷号: 第{volume_number}卷
- 章节范围: 第{start_chapter}-{end_chapter}章
- 重大事件:
{highlights_text}

**要求**:
1. 卷名格式: "卷{self._to_chinese_number(volume_number)}·<副标题>"
2. 副标题应简洁有力，2-6个字
3. 体现本卷的核心剧情或主题
4. 富有诗意和想象力
5. 只返回卷名，不要其他解释

**示例**:
- 卷一·初入江湖
- 卷二·星陨之夜
- 卷三·破境之路
- 卷四·天劫降临

请生成卷名:"""
    
    def _extract_title_from_response(self, response: str, volume_number: int) -> Optional[str]:
        """从AI响应中提取卷名"""
        if not response:
            return None
        
        # 清理响应
        title = response.strip()
        
        # 移除可能的引号
        title = title.strip('"\'""''')
        
        # 验证格式
        if title.startswith(f"卷{self._to_chinese_number(volume_number)}·"):
            return title
        
        # 如果没有前缀，自动添加
        if "·" in title:
            return f"卷{self._to_chinese_number(volume_number)}·{title.split('·')[-1]}"
        
        return f"卷{self._to_chinese_number(volume_number)}·{title}"
    
    @staticmethod
    def _to_chinese_number(num: int) -> str:
        """阿拉伯数字转中文数字（1-99）"""
        chinese_nums = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
        
        if num < 10:
            return chinese_nums[num]
        elif num < 20:
            return "十" + (chinese_nums[num - 10] if num > 10 else "")
        else:
            tens = num // 10
            ones = num % 10
            return chinese_nums[tens] + "十" + (chinese_nums[ones] if ones > 0 else "")

