"""
OpenAI配置相关API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import asyncio

from app.models.user import User
from app.core.database import get_async_db
from app.tools.openai_client import openai_client
from app.core.config import settings
from app.core.security import get_current_user, is_admin


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    system_prompt: Optional[str] = None

router = APIRouter()


@router.get("/config")
async def get_openai_config():
    """获取OpenAI配置信息"""
    try:
        config = openai_client.get_client_info()
        return {
            "status": "success",
            "config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/test")
async def test_openai_connection():
    """测试OpenAI连接"""
    try:
        # 测试简单的文本生成
        response = await openai_client.generate_text(
            prompt="请简单介绍一下你自己",
            max_tokens=100
        )
        
        return {
            "status": "success",
            "message": "OpenAI连接测试成功",
            "response": response,
            "config": openai_client.get_client_info()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"OpenAI连接测试失败: {str(e)}",
            "config": openai_client.get_client_info()
        }


@router.post("/generate-plan")
async def generate_ai_plan(
    destination: str,
    duration_days: int,
    budget: float,
    preferences: list,
    requirements: str = ""
):
    """使用AI生成旅行计划"""
    try:
        plan = await openai_client.generate_travel_plan(
            destination=destination,
            duration_days=duration_days,
            budget=budget,
            preferences=preferences,
            requirements=requirements
        )
        
        return {
            "status": "success",
            "plan": plan
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成计划失败: {str(e)}")


@router.post("/analyze-data")
async def analyze_travel_data(
    data: Dict[str, Any],
    analysis_type: str = "comprehensive"
):
    """分析旅行数据"""
    try:
        analysis = await openai_client.analyze_travel_data(
            data=data,
            analysis_type=analysis_type
        )
        
        return {
            "status": "success",
            "analysis": analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据分析失败: {str(e)}")


@router.post("/optimize-plan")
async def optimize_travel_plan(
    current_plan: Dict[str, Any],
    optimization_goals: list
):
    """优化旅行计划"""
    try:
        optimized_plan = await openai_client.optimize_travel_plan(
            current_plan=current_plan,
            optimization_goals=optimization_goals
        )
        
        return {
            "status": "success",
            "optimized_plan": optimized_plan
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计划优化失败: {str(e)}")


@router.post("/chat")
async def chat_with_ai(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    通用AI对话接口，支持上下文记忆
    
    Args:
        request: 聊天请求，包含message、conversation_history和system_prompt
    """
    try:
        # 默认系统提示词（合法合规内容输出限制）
        default_system_prompt = """你是一个专业的AI助手，专门帮助用户解答关于旅行规划、目的地信息、旅行方案等相关问题。

请遵循以下原则：
1. 提供准确、有用的信息和建议
2. 遵守法律法规，不提供任何违法、违规内容
3. 不涉及政治敏感话题
4. 不传播虚假信息
5. 尊重用户隐私，不泄露用户信息
6. 对于不确定的信息，明确告知用户
7. 保持友好、专业的沟通态度

如果用户的问题超出你的能力范围或涉及不当内容，请礼貌地告知用户。"""

        # 构建消息列表
        messages = []
        
        # 添加系统提示词
        messages.append({
            "role": "system",
            "content": request.system_prompt or default_system_prompt
        })
        
        # 添加对话历史（如果存在）
        if request.conversation_history:
            # 确保历史记录格式正确
            for item in request.conversation_history:
                if isinstance(item, dict) and "role" in item and "content" in item:
                    messages.append({
                        "role": item["role"],
                        "content": item["content"]
                    })
        
        # 添加当前用户消息
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # 调用OpenAI API
        response = await openai_client._call_api(
            messages=messages,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE
        )
        
        assistant_message = response.choices[0].message.content
        
        return {
            "status": "success",
            "message": assistant_message,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if hasattr(response.usage, 'prompt_tokens') else 0,
                "completion_tokens": response.usage.completion_tokens if hasattr(response.usage, 'completion_tokens') else 0,
                "total_tokens": response.usage.total_tokens if hasattr(response.usage, 'total_tokens') else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI对话失败: {str(e)}")