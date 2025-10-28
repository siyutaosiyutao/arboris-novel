"""自动生成器 Schemas"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CreateAutoGeneratorTaskRequest(BaseModel):
    """创建自动生成任务请求"""
    project_id: str
    target_chapters: Optional[int] = None
    chapters_per_batch: int = 1
    interval_seconds: int = 60
    auto_select_version: bool = True
    generation_config: Optional[dict] = None


class AutoGeneratorTaskResponse(BaseModel):
    """自动生成任务响应"""
    id: int
    project_id: str
    user_id: int
    status: str
    target_chapters: Optional[int]
    chapters_per_batch: int
    interval_seconds: int
    auto_select_version: bool
    generation_config: Optional[dict] = None
    chapters_generated: int
    total_tokens_used: int
    error_count: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_generation_at: Optional[datetime]

    class Config:
        from_attributes = True


class AutoGeneratorLogResponse(BaseModel):
    """自动生成日志响应"""
    id: int
    task_id: int
    chapter_number: Optional[int]
    log_type: str
    message: str
    details: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True
