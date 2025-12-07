"""
OpenAI配置相关API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel
import asyncio
import json

from app.models.user import User
from app.core.database import get_async_db
from app.tools.openai_client import openai_client
from app.core.config import settings
from app.core.security import get_current_user, is_admin
from loguru import logger


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    system_prompt: Optional[str] = None

router = APIRouter()


def get_max_input_tokens() -> int:
    """获取最大输入 token 数（从配置读取）"""
    return settings.OPENAI_MAX_INPUT_TOKENS or 12000


def get_estimated_chars_per_token() -> float:
    """获取 token 估算比例（从配置读取）"""
    return settings.OPENAI_ESTIMATED_CHARS_PER_TOKEN


def get_max_context_chars() -> int:
    """获取最大上下文字符数"""
    max_tokens = get_max_input_tokens()
    chars_per_token = get_estimated_chars_per_token()
    return int(max_tokens * chars_per_token)


def get_max_recent_messages() -> int:
    """获取最多保留的对话轮数（从配置读取）"""
    return settings.OPENAI_MAX_RECENT_MESSAGES


def estimate_tokens(text: str) -> int:
    """估算文本的 token 数量（粗略估算）"""
    chars_per_token = get_estimated_chars_per_token()
    return int((len(text) + chars_per_token - 1) / chars_per_token)


def truncate_conversation_history(
    conversation_history: Optional[List[Dict[str, str]]]
) -> List[Dict[str, str]]:
    """
    智能截断对话历史，确保不超过 token 限制
    
    策略：
    1. 优先保留最近的对话（最多 MAX_RECENT_MESSAGES 轮）
    2. 如果还有空间，保留初始上下文的核心部分
    3. 如果初始上下文太长，截断但保留开头和关键信息
    """
    if not conversation_history:
        return []
    
    if len(conversation_history) == 0:
        return []
    
    # 分离初始上下文（第一个 assistant 消息，通常是长文本）和后续对话
    initial_context = conversation_history[0] if (
        conversation_history[0].get("role") == "assistant"
    ) else None
    conversation_messages = conversation_history[1:] if initial_context else conversation_history
    
    # 保留最近的对话（最多 MAX_RECENT_MESSAGES 轮，即 MAX_RECENT_MESSAGES * 2 条消息）
    max_recent = get_max_recent_messages()
    recent_messages = conversation_messages[-max_recent * 2:] if len(conversation_messages) > max_recent * 2 else conversation_messages
    
    # 计算已使用的 token 数
    used_tokens = sum(estimate_tokens(msg.get("content", "")) for msg in recent_messages)
    
    # 如果有初始上下文，尝试添加它（可能需要截断）
    if initial_context:
        initial_content = initial_context.get("content", "")
        initial_tokens = estimate_tokens(initial_content)
        max_input_tokens = get_max_input_tokens()
        remaining_tokens = max_input_tokens - used_tokens - 1000  # 留出 1000 tokens 缓冲
        
        if initial_tokens <= remaining_tokens:
            # 初始上下文可以完整保留
            return [initial_context] + recent_messages
        elif remaining_tokens > 1000:
            # 初始上下文太长，需要截断
            # 保留开头部分（通常包含重要信息）和结尾部分
            chars_per_token = get_estimated_chars_per_token()
            max_initial_chars = int((remaining_tokens - 500) * chars_per_token)  # 留出 500 tokens
            keep_start_chars = int(max_initial_chars * 0.6)  # 保留 60% 的开头
            keep_end_chars = int(max_initial_chars * 0.4)  # 保留 40% 的结尾
            
            truncated_content = (
                initial_content[:keep_start_chars] +
                "\n\n[... 内容已截断以节省上下文空间 ...]\n\n" +
                initial_content[-keep_end_chars:]
            )
            
            truncated_context = {**initial_context, "content": truncated_content}
            return [truncated_context] + recent_messages
        else:
            # 剩余空间太小，不添加初始上下文，只保留最近对话
            logger.warning(f"初始上下文过长，已丢弃。剩余 tokens: {remaining_tokens}")
            return recent_messages
    
    return recent_messages


@router.get("/config")
async def get_openai_config():
    """获取OpenAI配置信息（包括 token 限制配置）"""
    try:
        config = openai_client.get_client_info()
        # 添加 token 限制配置信息
        config.update({
            "max_input_tokens": get_max_input_tokens(),
            "max_output_tokens": settings.OPENAI_MAX_TOKENS or 4000,
            "context_window": settings.OPENAI_CONTEXT_WINDOW or 16384,
            "estimated_chars_per_token": get_estimated_chars_per_token(),
            "max_recent_messages": get_max_recent_messages(),
        })
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
            # 智能截断对话历史，确保不超过 token 限制
            truncated_history = truncate_conversation_history(request.conversation_history)
            
            if len(truncated_history) < len(request.conversation_history):
                logger.info(
                    f"对话历史已截断: {len(request.conversation_history)} -> {len(truncated_history)} 条消息"
                )
            
            # 确保历史记录格式正确
            for item in truncated_history:
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
        
        # 最终检查：如果总长度仍然过长，进行二次截断（保留最近的）
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        max_context_chars = get_max_context_chars()
        if total_chars > max_context_chars:
            logger.warning(f"消息总长度仍然过长 ({total_chars} 字符)，进行二次截断")
            # 保留系统提示词和最近的对话
            system_msg = messages[0] if messages and messages[0].get("role") == "system" else None
            other_messages = messages[1:] if system_msg else messages
            
            # 从后往前保留，直到满足长度要求
            kept_messages = []
            current_chars = len(system_msg.get("content", "")) if system_msg else 0
            
            for msg in reversed(other_messages):
                msg_chars = len(msg.get("content", ""))
                if current_chars + msg_chars <= max_context_chars:
                    kept_messages.insert(0, msg)
                    current_chars += msg_chars
                else:
                    break
            
            messages = ([system_msg] if system_msg else []) + kept_messages
            logger.info(f"二次截断后保留 {len(messages)} 条消息")
        
        # 调用OpenAI API
        max_output_tokens = settings.OPENAI_MAX_TOKENS or 4000
        response = await openai_client._call_api(
            messages=messages,
            max_tokens=max_output_tokens,
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


@router.post("/chat/stream")
async def chat_with_ai_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    流式AI对话接口，支持实时流式响应
    
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
            # 智能截断对话历史，确保不超过 token 限制
            truncated_history = truncate_conversation_history(request.conversation_history)
            
            if len(truncated_history) < len(request.conversation_history):
                logger.info(
                    f"对话历史已截断: {len(request.conversation_history)} -> {len(truncated_history)} 条消息"
                )
            
            # 确保历史记录格式正确
            for item in truncated_history:
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
        
        # 最终检查：如果总长度仍然过长，进行二次截断（保留最近的）
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        max_context_chars = get_max_context_chars()
        if total_chars > max_context_chars:
            logger.warning(f"消息总长度仍然过长 ({total_chars} 字符)，进行二次截断")
            # 保留系统提示词和最近的对话
            system_msg = messages[0] if messages and messages[0].get("role") == "system" else None
            other_messages = messages[1:] if system_msg else messages
            
            # 从后往前保留，直到满足长度要求
            kept_messages = []
            current_chars = len(system_msg.get("content", "")) if system_msg else 0
            
            for msg in reversed(other_messages):
                msg_chars = len(msg.get("content", ""))
                if current_chars + msg_chars <= max_context_chars:
                    kept_messages.insert(0, msg)
                    current_chars += msg_chars
                else:
                    break
            
            messages = ([system_msg] if system_msg else []) + kept_messages
            logger.info(f"二次截断后保留 {len(messages)} 条消息")
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            """生成流式响应"""
            try:
                # 调用OpenAI流式API
                max_output_tokens = settings.OPENAI_MAX_TOKENS or 4000
                async for chunk in openai_client._call_api_stream(
                    messages=messages,
                    max_tokens=max_output_tokens,
                    temperature=settings.OPENAI_TEMPERATURE
                ):
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content:
                            # 发送内容块
                            data = {
                                "type": "content",
                                "content": delta.content
                            }
                            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                        
                        # 检查是否完成
                        if chunk.choices[0].finish_reason:
                            # 发送完成信号
                            usage_data = {}
                            if hasattr(chunk, 'usage') and chunk.usage:
                                usage_data = {
                                    "prompt_tokens": chunk.usage.prompt_tokens if hasattr(chunk.usage, 'prompt_tokens') else 0,
                                    "completion_tokens": chunk.usage.completion_tokens if hasattr(chunk.usage, 'completion_tokens') else 0,
                                    "total_tokens": chunk.usage.total_tokens if hasattr(chunk.usage, 'total_tokens') else 0
                                }
                            
                            data = {
                                "type": "done",
                                "usage": usage_data
                            }
                            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                            break
            except Exception as e:
                # 发送错误信息
                error_data = {
                    "type": "error",
                    "message": str(e)
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI流式对话失败: {str(e)}")