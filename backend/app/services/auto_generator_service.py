"""自动生成器服务 - 完整实现版本"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.auto_generator import AutoGeneratorLog, AutoGeneratorTask
from ..models.novel import Chapter, ChapterOutline, NovelProject
from ..schemas.novel import GenerateChapterRequest
from .novel_service import NovelService

logger = logging.getLogger(__name__)


class AutoGeneratorService:
    """自动生成器服务"""
    
    # 存储运行中的任务
    _running_tasks: dict[int, asyncio.Task] = {}
    
    @classmethod
    async def create_task(
        cls,
        db: AsyncSession,
        project_id: str,
        user_id: int,
        target_chapters: Optional[int] = None,
        chapters_per_batch: int = 1,
        interval_seconds: int = 60,
        auto_select_version: bool = True,
        generation_config: Optional[dict] = None,
    ) -> AutoGeneratorTask:
        """创建自动生成任务"""
        
        # 检查项目是否存在
        result = await db.execute(
            select(NovelProject).where(NovelProject.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # 检查是否已有运行中的任务
        result = await db.execute(
            select(AutoGeneratorTask).where(
                AutoGeneratorTask.project_id == project_id,
                AutoGeneratorTask.status.in_(["pending", "running"])
            )
        )
        existing_task = result.scalar_one_or_none()
        if existing_task:
            raise ValueError(f"Project {project_id} already has a running task")
        
        # 创建任务
        task = AutoGeneratorTask(
            project_id=project_id,
            user_id=user_id,
            target_chapters=target_chapters,
            chapters_per_batch=chapters_per_batch,
            interval_seconds=interval_seconds,
            auto_select_version=auto_select_version,
            generation_config=generation_config or {},
            status="pending"
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        await cls._log(db, task.id, "info", f"自动生成任务已创建，目标章节数: {target_chapters or '无限'}")
        
        return task
    
    @classmethod
    async def start_task(cls, db: AsyncSession, task_id: int) -> AutoGeneratorTask:
        """启动自动生成任务"""
        
        result = await db.execute(
            select(AutoGeneratorTask).where(AutoGeneratorTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if task.status not in ["pending", "paused"]:
            raise ValueError(f"Task {task_id} cannot be started (status: {task.status})")
        
        # 更新状态
        await db.execute(
            update(AutoGeneratorTask)
            .where(AutoGeneratorTask.id == task_id)
            .values(
                status="running",
                started_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()
        
        await cls._log(db, task_id, "info", "自动生成任务已启动")
        
        # 启动后台任务
        asyncio_task = asyncio.create_task(cls._run_generator(task_id))
        cls._running_tasks[task_id] = asyncio_task
        
        await db.refresh(task)
        return task
    
    @classmethod
    async def pause_task(cls, db: AsyncSession, task_id: int) -> AutoGeneratorTask:
        """暂停任务"""
        
        result = await db.execute(
            select(AutoGeneratorTask).where(AutoGeneratorTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if task.status != "running":
            raise ValueError(f"Task {task_id} is not running")
        
        await db.execute(
            update(AutoGeneratorTask)
            .where(AutoGeneratorTask.id == task_id)
            .values(status="paused", updated_at=datetime.now(timezone.utc))
        )
        await db.commit()
        
        await cls._log(db, task_id, "info", "自动生成任务已暂停")
        
        await db.refresh(task)
        return task
    
    @classmethod
    async def stop_task(cls, db: AsyncSession, task_id: int) -> AutoGeneratorTask:
        """停止任务"""
        
        result = await db.execute(
            select(AutoGeneratorTask).where(AutoGeneratorTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        await db.execute(
            update(AutoGeneratorTask)
            .where(AutoGeneratorTask.id == task_id)
            .values(
                status="stopped",
                completed_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()
        
        await cls._log(db, task_id, "info", "自动生成任务已停止")
        
        # 取消后台任务
        if task_id in cls._running_tasks:
            cls._running_tasks[task_id].cancel()
            del cls._running_tasks[task_id]
        
        await db.refresh(task)
        return task
    
    @classmethod
    async def get_task(cls, db: AsyncSession, task_id: int) -> Optional[AutoGeneratorTask]:
        """获取任务信息"""
        result = await db.execute(
            select(AutoGeneratorTask).where(AutoGeneratorTask.id == task_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_project_tasks(
        cls,
        db: AsyncSession,
        project_id: str,
        user_id: int
    ) -> list[AutoGeneratorTask]:
        """获取项目的所有任务"""
        result = await db.execute(
            select(AutoGeneratorTask)
            .where(
                AutoGeneratorTask.project_id == project_id,
                AutoGeneratorTask.user_id == user_id
            )
            .order_by(AutoGeneratorTask.created_at.desc())
        )
        return list(result.scalars().all())
    
    @classmethod
    async def get_task_logs(
        cls, 
        db: AsyncSession, 
        task_id: int, 
        limit: int = 100
    ) -> list[AutoGeneratorLog]:
        """获取任务日志"""
        result = await db.execute(
            select(AutoGeneratorLog)
            .where(AutoGeneratorLog.task_id == task_id)
            .order_by(AutoGeneratorLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @classmethod
    async def _run_generator(cls, task_id: int):
        """后台生成任务"""
        from ..db.session import AsyncSessionLocal

        logger.info(f"[AutoGen] Starting task {task_id}")

        try:
            while True:
                try:
                    async with AsyncSessionLocal() as db:
                        # 获取任务状态
                        task = await cls.get_task(db, task_id)
                        if not task:
                            logger.error(f"Task {task_id} not found")
                            break

                        # 检查状态
                        if task.status == "stopped":
                            logger.info(f"Task {task_id} stopped")
                            break

                        if task.status == "paused":
                            logger.info(f"Task {task_id} paused, waiting...")
                            await asyncio.sleep(10)
                            continue

                        # 检查是否达到目标
                        if task.target_chapters and task.chapters_generated >= task.target_chapters:
                            await db.execute(
                                update(AutoGeneratorTask)
                                .where(AutoGeneratorTask.id == task_id)
                                .values(
                                    status="completed",
                                    completed_at=datetime.now(timezone.utc)
                                )
                            )
                            await db.commit()
                            await cls._log(db, task_id, "success", f"已完成目标章节数: {task.target_chapters}")
                            break

                        # 生成章节
                        try:
                            await cls._generate_next_chapters(db, task)
                        except Exception as e:
                            logger.error(f"Error generating chapters for task {task_id}: {e}")
                            await cls._handle_error(db, task_id, str(e))
                            # 检查是否因错误次数过多而停止
                            task = await cls.get_task(db, task_id)
                            if task and task.status == "error":
                                break

                        # 等待间隔
                        await asyncio.sleep(task.interval_seconds)

                except asyncio.CancelledError:
                    logger.info(f"Task {task_id} cancelled")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error in task {task_id}: {e}")
                    await asyncio.sleep(60)  # 出错后等待1分钟再重试
        finally:
            # 确保清理资源
            if task_id in cls._running_tasks:
                del cls._running_tasks[task_id]

            logger.info(f"Auto-generator for task {task_id} finished")
    
    @classmethod
    async def _generate_next_chapters(cls, db: AsyncSession, task: AutoGeneratorTask):
        """生成下一批章节"""
        
        # 获取当前最大章节号
        result = await db.execute(
            select(Chapter.chapter_number)
            .where(Chapter.project_id == task.project_id)
            .order_by(Chapter.chapter_number.desc())
            .limit(1)
        )
        last_chapter = result.scalar_one_or_none()
        next_chapter_number = (last_chapter or 0) + 1
        
        # 获取大纲
        result = await db.execute(
            select(ChapterOutline)
            .where(
                ChapterOutline.project_id == task.project_id,
                ChapterOutline.chapter_number == next_chapter_number
            )
        )
        outline = result.scalar_one_or_none()

        if not outline:
            await cls._log(
                db,
                task.id,
                "info",
                f"第 {next_chapter_number} 章大纲不存在，自动生成新的大纲（10章）"
            )

            # 自动生成10章大纲
            try:
                await cls._auto_generate_outlines(db, task, next_chapter_number, num_chapters=10)

                # 重新查询大纲
                result = await db.execute(
                    select(ChapterOutline)
                    .where(
                        ChapterOutline.project_id == task.project_id,
                        ChapterOutline.chapter_number == next_chapter_number
                    )
                )
                outline = result.scalar_one_or_none()

                if not outline:
                    await cls._log(
                        db,
                        task.id,
                        "error",
                        f"自动生成大纲失败，第 {next_chapter_number} 章大纲仍不存在"
                    )
                    raise ValueError(f"自动生成大纲失败")

                await cls._log(
                    db,
                    task.id,
                    "success",
                    f"成功自动生成第 {next_chapter_number}-{next_chapter_number + 9} 章大纲"
                )
            except Exception as e:
                await cls._log(
                    db,
                    task.id,
                    "error",
                    f"自动生成大纲失败: {str(e)}"
                )
                raise
        
        await cls._log(
            db,
            task.id,
            "info",
            f"开始生成第 {next_chapter_number} 章: {outline.title}"
        )
        
        # 调用生成服务
        novel_service = NovelService(db)
        
        # 构建生成请求
        request = GenerateChapterRequest(
            chapter_number=next_chapter_number,
            version_count=task.generation_config.get("version_count", 3),
            writing_notes=task.generation_config.get("writing_notes")
        )
        
        try:
            # 导入必要的服务和工具
            from .prompt_service import PromptService
            from .llm_service import LLMService
            from .chapter_context_service import ChapterContextService
            from .vector_store_service import VectorStoreService
            from ..core.config import settings
            from ..utils.json_utils import remove_think_tags, unwrap_markdown_json
            from ..repositories.system_config_repository import SystemConfigRepository
            import json
            import os
            
            prompt_service = PromptService(db)
            llm_service = LLMService(db)
            
            # 获取项目（预加载所有关系以避免 greenlet_spawn 错误）
            from sqlalchemy.orm import selectinload, joinedload

            result = await db.execute(
                select(NovelProject)
                .where(NovelProject.id == task.project_id)
                .options(
                    selectinload(NovelProject.chapters).selectinload(Chapter.versions),
                    selectinload(NovelProject.chapters).selectinload(Chapter.selected_version),
                    selectinload(NovelProject.chapters).selectinload(Chapter.evaluations),
                    selectinload(NovelProject.outlines),
                    selectinload(NovelProject.conversations),
                    joinedload(NovelProject.blueprint),  # 使用 joinedload 确保 blueprint 被加载
                    selectinload(NovelProject.characters),
                    selectinload(NovelProject.relationships_)
                )
            )
            project = result.scalar_one_or_none()
            if not project:
                raise ValueError(f"Project {task.project_id} not found")

            # 确保所有关系都已加载到内存中，避免后续懒加载
            # 这会触发所有关系的加载，确保它们在异步上下文中可用
            _ = project.chapters
            _ = project.outlines
            _ = project.conversations
            _ = project.blueprint
            _ = project.characters
            _ = project.relationships_
            for ch in project.chapters:
                _ = ch.versions
                _ = ch.selected_version
                _ = ch.evaluations
            
            # 准备章节
            chapter = await novel_service.get_or_create_chapter(task.project_id, next_chapter_number)
            chapter.real_summary = None
            chapter.selected_version_id = None
            chapter.status = "generating"
            await db.commit()
            
            # 收集前情摘要
            outlines_map = {item.chapter_number: item for item in project.outlines}
            completed_chapters = []
            previous_summary_text = ""
            previous_tail_excerpt = ""
            
            for existing in project.chapters:
                if existing.chapter_number >= next_chapter_number:
                    continue
                if existing.selected_version is None or not existing.selected_version.content:
                    continue
                if not existing.real_summary:
                    summary = await llm_service.get_summary(
                        existing.selected_version.content,
                        temperature=0.15,
                        user_id=task.user_id,
                        timeout=180.0,
                    )
                    existing.real_summary = remove_think_tags(summary)
                    await db.commit()
                completed_chapters.append({
                    "chapter_number": existing.chapter_number,
                    "title": outlines_map.get(existing.chapter_number).title if outlines_map.get(existing.chapter_number) else f"第{existing.chapter_number}章",
                    "summary": existing.real_summary,
                })
                previous_summary_text = existing.real_summary or ""
                # 提取结尾
                content = existing.selected_version.content
                lines = content.split('\n')
                previous_tail_excerpt = '\n'.join(lines[-10:]) if len(lines) > 10 else content
            
            # 构建蓝图
            project_schema = await novel_service._serialize_project(project)
            blueprint_dict = project_schema.blueprint.model_dump()
            
            # 清理蓝图
            banned_keys = {"chapter_outline", "chapter_summaries", "chapter_details", "chapter_dialogues", "chapter_events", "conversation_history", "character_timelines"}
            for key in banned_keys:
                blueprint_dict.pop(key, None)
            
            # 获取写作提示词
            writer_prompt = await prompt_service.get_prompt("writing")
            if not writer_prompt:
                raise ValueError("缺少写作提示词")
            
            # RAG 检索
            vector_store = None
            if settings.vector_store_enabled:
                try:
                    vector_store = VectorStoreService()
                except:
                    pass
            
            context_service = ChapterContextService(llm_service=llm_service, vector_store=vector_store)
            rag_context = await context_service.retrieve_for_generation(
                project_id=task.project_id,
                query_text=f"{outline.title}\n{outline.summary}",
                user_id=task.user_id,
            )
            
            # 构建提示词
            blueprint_text = json.dumps(blueprint_dict, ensure_ascii=False, indent=2)
            rag_chunks_text = "\n\n".join(rag_context.chunk_texts()) if rag_context and rag_context.chunks else "未检索到章节片段"
            rag_summaries_text = "\n".join(rag_context.summary_lines()) if rag_context and rag_context.summaries else "未检索到章节摘要"
            
            prompt_sections = [
                ("[世界蓝图](JSON)", blueprint_text),
                ("[上一章摘要]", previous_summary_text or "暂无"),
                ("[上一章结尾]", previous_tail_excerpt or "暂无"),
                ("[检索到的剧情上下文](Markdown)", rag_chunks_text),
                ("[检索到的章节摘要]", rag_summaries_text),
                ("[当前章节目标]", f"标题：{outline.title}\n摘要：{outline.summary}"),
            ]
            prompt_input = "\n\n".join(f"{title}\n{content}" for title, content in prompt_sections if content)
            
            # 生成版本
            version_count = task.generation_config.get("version_count", 2)
            raw_versions = []
            
            for idx in range(version_count):
                response = await llm_service.get_llm_response(
                    system_prompt=writer_prompt,
                    conversation_history=[{"role": "user", "content": prompt_input}],
                    temperature=0.9,
                    user_id=task.user_id,
                    timeout=600.0,
                )
                cleaned = remove_think_tags(response)
                normalized = unwrap_markdown_json(cleaned)
                try:
                    raw_versions.append(json.loads(normalized))
                except:
                    raw_versions.append({"content": normalized})
            
            # 提取内容
            contents = []
            metadata = []
            for variant in raw_versions:
                if isinstance(variant, dict):
                    if "content" in variant:
                        contents.append(variant["content"])
                    elif "chapter_content" in variant:
                        contents.append(str(variant["chapter_content"]))
                    else:
                        contents.append(json.dumps(variant, ensure_ascii=False))
                    metadata.append(variant)
                else:
                    contents.append(str(variant))
                    metadata.append({"raw": variant})
            
            # 保存版本
            await novel_service.replace_chapter_versions(chapter, contents, metadata)
            
            # 如果启用自动选择，选择第一个版本
            if task.auto_select_version:
                # 重新查询 chapter 并预加载 versions 关系
                result = await db.execute(
                    select(Chapter)
                    .where(
                        Chapter.project_id == task.project_id,
                        Chapter.chapter_number == next_chapter_number
                    )
                    .options(selectinload(Chapter.versions))
                )
                chapter_obj = result.scalar_one_or_none()

                if chapter_obj and chapter_obj.versions:
                    # 选择第一个版本（索引为 0）
                    await novel_service.select_chapter_version(chapter_obj, 0)
                    
                    await cls._log(
                        db,
                        task.id,
                        "success",
                        f"第 {next_chapter_number} 章生成完成并已自动选择版本"
                    )
                    
                    # 触发创意功能分析
                    await cls._run_creative_analysis(db, task, chapter_obj.id)
            else:
                await cls._log(
                    db,
                    task.id,
                    "success",
                    f"第 {next_chapter_number} 章生成完成，等待手动选择版本"
                )
                
                # 即使未自动选择版本，也触发创意功能分析
                result = await db.execute(
                    select(Chapter)
                    .where(
                        Chapter.project_id == task.project_id,
                        Chapter.chapter_number == next_chapter_number
                    )
                    .options(selectinload(Chapter.versions))
                )
                chapter_obj = result.scalar_one_or_none()
                if chapter_obj:
                    await cls._run_creative_analysis(db, task, chapter_obj.id)
            
            # 更新统计
            await db.execute(
                update(AutoGeneratorTask)
                .where(AutoGeneratorTask.id == task.id)
                .values(
                    chapters_generated=task.chapters_generated + 1,
                    last_generation_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await db.commit()
            
        except Exception as e:
            await cls._log(
                db,
                task.id,
                "error",
                f"第 {next_chapter_number} 章生成失败: {str(e)}"
            )
            raise
    
    @classmethod
    async def _handle_error(cls, db: AsyncSession, task_id: int, error_msg: str):
        """处理错误"""
        
        result = await db.execute(
            select(AutoGeneratorTask).where(AutoGeneratorTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return
        
        error_count = task.error_count + 1
        
        # 如果错误次数过多，停止任务
        if error_count >= 5:
            await db.execute(
                update(AutoGeneratorTask)
                .where(AutoGeneratorTask.id == task_id)
                .values(
                    status="error",
                    error_count=error_count,
                    last_error=error_msg,
                    completed_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await cls._log(db, task_id, "error", f"任务因错误次数过多而停止: {error_msg}")
        else:
            await db.execute(
                update(AutoGeneratorTask)
                .where(AutoGeneratorTask.id == task_id)
                .values(
                    error_count=error_count,
                    last_error=error_msg,
                    updated_at=datetime.now(timezone.utc)
                )
            )
        
        await db.commit()
    
    @classmethod
    async def _log(
        cls,
        db: AsyncSession,
        task_id: int,
        log_type: str,
        message: str,
        chapter_number: Optional[int] = None,
        details: Optional[dict] = None
    ):
        """记录日志"""
        log = AutoGeneratorLog(
            task_id=task_id,
            chapter_number=chapter_number,
            log_type=log_type,
            message=message,
            details=details
        )
        db.add(log)
        await db.commit()
        
        logger.info(f"[Task {task_id}] {log_type.upper()}: {message}")

    
    @classmethod
    async def _run_creative_analysis(
        cls, 
        db: AsyncSession, 
        task: AutoGeneratorTask, 
        chapter_id: str
    ):
        """运行创意功能分析"""
        config = task.generation_config or {}
        
        # 异步执行分析任务，不阻塞主流程
        analysis_tasks = []
        
        # 1. 张力分析
        if config.get("enable_tension_analysis", False):
            analysis_tasks.append(
                cls._analyze_tension(db, chapter_id, task.id)
            )
        
        # 2. 角色一致性检查
        if config.get("enable_character_consistency", False):
            analysis_tasks.append(
                cls._check_character_consistency(db, chapter_id, task.id)
            )
        
        # 3. 伏笔识别
        if config.get("enable_foreshadowing", False):
            analysis_tasks.append(
                cls._detect_foreshadowing(db, chapter_id, task.id)
            )
        
        # 并发执行所有分析任务
        if analysis_tasks:
            try:
                results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
                # 检查是否有错误
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Creative analysis error: {result}")
            except Exception as e:
                await cls._log(
                    db, task.id, "warning", 
                    f"创意功能分析出错: {str(e)}"
                )
    
    @classmethod
    async def _analyze_tension(cls, db: AsyncSession, chapter_id: str, task_id: int):
        """执行张力分析"""
        try:
            try:
                from ..services.creative_features_service_v2 import TensionAnalysisService
            except ImportError:
                logger.warning("creative_features_service_v2 not found, skipping tension analysis")
                await cls._log(
                    db, task_id, "info",
                    "⚠️ 张力分析功能未安装，已跳过"
                )
                return

            from ..services.llm_service import LLMService

            llm_service = LLMService(db)
            tension_service = TensionAnalysisService(db, llm_service)

            analysis = await tension_service.analyze_chapter(chapter_id)

            await cls._log(
                db, task_id, "info",
                f"✓ 张力分析完成: 分数 {analysis.tension_score:.1f}"
            )
        except Exception as e:
            logger.error(f"Tension analysis failed: {e}")
            await cls._log(
                db, task_id, "warning",
                f"张力分析失败: {str(e)}"
            )
    
    @classmethod
    async def _check_character_consistency(
        cls, db: AsyncSession, chapter_id: str, task_id: int
    ):
        """执行角色一致性检查"""
        try:
            try:
                from ..services.creative_features_service_v2 import CharacterConsistencyService
            except ImportError:
                logger.warning("creative_features_service_v2 not found, skipping character consistency check")
                await cls._log(
                    db, task_id, "info",
                    "⚠️ 角色一致性检查功能未安装，已跳过"
                )
                return

            from ..services.llm_service import LLMService

            llm_service = LLMService(db)
            character_service = CharacterConsistencyService(db, llm_service)

            checks = await character_service.check_chapter(chapter_id)

            if checks:
                avg_score = sum(c.consistency_score for c in checks) / len(checks)
                await cls._log(
                    db, task_id, "info",
                    f"✓ 角色一致性检查完成: 平均分数 {avg_score:.1f}"
                )
            else:
                await cls._log(
                    db, task_id, "info",
                    "✓ 角色一致性检查完成: 无角色出现"
                )
        except Exception as e:
            logger.error(f"Character consistency check failed: {e}")
            await cls._log(
                db, task_id, "warning",
                f"角色一致性检查失败: {str(e)}"
            )
    
    @classmethod
    async def _detect_foreshadowing(
        cls, db: AsyncSession, chapter_id: str, task_id: int
    ):
        """执行伏笔识别"""
        try:
            try:
                from ..services.creative_features_service_v2 import ForeshadowingService
            except ImportError:
                logger.warning("creative_features_service_v2 not found, skipping foreshadowing detection")
                await cls._log(
                    db, task_id, "info",
                    "⚠️ 伏笔识别功能未安装，已跳过"
                )
                return

            from ..services.llm_service import LLMService

            llm_service = LLMService(db)
            foreshadowing_service = ForeshadowingService(db, llm_service)

            foreshadowings = await foreshadowing_service.detect_foreshadowing(chapter_id)

            await cls._log(
                db, task_id, "info",
                f"✓ 伏笔识别完成: 发现 {len(foreshadowings)} 个伏笔"
            )
        except Exception as e:
            logger.error(f"Foreshadowing detection failed: {e}")
            await cls._log(
                db, task_id, "warning",
                f"伏笔识别失败: {str(e)}"
            )

    @classmethod
    async def _auto_generate_outlines(
        cls,
        db: AsyncSession,
        task: AutoGeneratorTask,
        start_chapter: int,
        num_chapters: int = 10
    ):
        """自动生成章节大纲

        Args:
            db: 数据库会话
            task: 自动生成任务
            start_chapter: 起始章节号
            num_chapters: 生成章节数量（默认10章）
        """
        from .prompt_service import PromptService
        from .llm_service import LLMService
        from ..utils.text_utils import remove_think_tags, unwrap_markdown_json

        await cls._log(
            db,
            task.id,
            "info",
            f"开始自动生成第 {start_chapter}-{start_chapter + num_chapters - 1} 章大纲..."
        )

        # 获取项目信息
        novel_service = NovelService(db)

        # 获取用户ID（从任务中）
        user_id = task.user_id

        # 获取项目schema
        project_schema = await novel_service.get_project_schema(task.project_id, user_id)
        blueprint_dict = project_schema.blueprint.model_dump()

        # 获取大纲提示词
        prompt_service = PromptService(db)
        outline_prompt = await prompt_service.get_prompt("outline")
        if not outline_prompt:
            raise ValueError("缺少大纲提示词，请联系管理员配置 'outline' 提示词")

        # 构建请求payload
        payload = {
            "novel_blueprint": blueprint_dict,
            "wait_to_generate": {
                "start_chapter": start_chapter,
                "num_chapters": num_chapters,
            },
        }

        # 调用LLM生成大纲
        llm_service = LLMService(db)
        response = await llm_service.get_llm_response(
            system_prompt=outline_prompt,
            conversation_history=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            temperature=0.7,
            user_id=user_id,
            timeout=360.0,
        )

        # 解析响应
        normalized = unwrap_markdown_json(remove_think_tags(response))
        try:
            data = json.loads(normalized)
        except json.JSONDecodeError as exc:
            logger.error(
                "自动生成大纲 JSON 解析失败: %s, 原始内容预览: %s",
                exc,
                normalized[:500],
            )
            raise ValueError(f"自动生成大纲失败，AI 返回的内容格式不正确: {str(exc)}") from exc

        # 保存大纲到数据库
        new_outlines = data.get("chapters", [])
        if not new_outlines:
            raise ValueError("AI 未返回任何章节大纲")

        for item in new_outlines:
            stmt = (
                select(ChapterOutline)
                .where(
                    ChapterOutline.project_id == task.project_id,
                    ChapterOutline.chapter_number == item.get("chapter_number"),
                )
            )
            result = await db.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                # 更新现有大纲
                record.title = item.get("title", record.title)
                record.summary = item.get("summary", record.summary)
            else:
                # 创建新大纲
                db.add(
                    ChapterOutline(
                        project_id=task.project_id,
                        chapter_number=item.get("chapter_number"),
                        title=item.get("title", ""),
                        summary=item.get("summary"),
                    )
                )

        await db.commit()

        await cls._log(
            db,
            task.id,
            "success",
            f"成功生成 {len(new_outlines)} 章大纲"
        )
