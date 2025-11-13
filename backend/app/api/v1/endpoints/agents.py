"""
AI Agent API端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from app.core.database import get_async_db
from app.services.agent_service import AgentService
from app.tasks.travel_plan_tasks import (
    generate_travel_plans_task as celery_generate_travel_plans_task,
    refine_travel_plan_task as celery_refine_travel_plan_task,
)

router = APIRouter()


@router.post("/generate-plan/{plan_id}")
async def generate_travel_plan(
    plan_id: int,
    preferences: Optional[Dict[str, Any]] = None,
    requirements: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """生成旅行方案（Celery异步）"""
    # 直接触发Celery任务
    async_result = celery_generate_travel_plans_task.delay(
        plan_id,
        preferences,
        requirements,
    )
    return {
        "message": "旅行方案生成任务已启动",
        "plan_id": plan_id,
        "status": "generating",
        "task_id": async_result.id,
    }


@router.post("/refine-plan/{plan_id}")
async def refine_travel_plan(
    plan_id: int,
    plan_index: int,
    refinements: Dict[str, Any],
    db: AsyncSession = Depends(get_async_db)
):
    """细化旅行方案（Celery异步）"""
    async_result = celery_refine_travel_plan_task.delay(plan_id, plan_index, refinements)
    return {"message": "方案细化任务已启动", "plan_id": plan_id, "task_id": async_result.id}


@router.get("/recommendations/{plan_id}")
async def get_plan_recommendations(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """获取方案推荐"""
    agent_service = AgentService(db)
    
    recommendations = await agent_service.get_plan_recommendations(plan_id)
    
    return {
        "plan_id": plan_id,
        "recommendations": recommendations
    }
