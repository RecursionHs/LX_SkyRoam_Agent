#!/usr/bin/env python3
"""
小红书 API 服务器
独立的FastAPI服务，提供小红书爬虫功能
避免主程序的异步事件循环问题
"""

import asyncio
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from loguru import logger
from dotenv import load_dotenv

# 必须在所有其他导入之前设置事件循环策略 - 使用ProactorEventLoop解决Playwright问题
if sys.platform == "win32":
    # 尝试使用ProactorEventLoop，这对Playwright更友好
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        # 如果不支持ProactorEventLoop，回退到SelectorEventLoop
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 添加项目路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# 加载环境变量
load_dotenv()

# 导入小红书相关模块
from app.platforms.xhs.playwright_crawler import PlaywrightXHSCrawler
from app.platforms.xhs.real_crawler import XiaoHongShuRealCrawler, XiaoHongShuLoginCrawler
from app.services.enhanced_cookie_manager import enhanced_cookie_manager

# 请求模型
class LoginRequest(BaseModel):
    """登录请求模型"""
    timeout: Optional[int] = 300

class SearchRequest(BaseModel):
    """搜索请求模型"""
    keyword: str
    limit: Optional[int] = 10
    sort_type: Optional[str] = "general"

class CookieStatusResponse(BaseModel):
    """Cookie状态响应模型"""
    primary_exists: bool
    backup_exists: bool
    session_exists: bool
    cookie_count: int
    save_time: Optional[str]
    remaining_days: Optional[int]
    is_valid: bool

class XHSAPIServer:
    """小红书API服务器"""
    
    def __init__(self):
        self.app = FastAPI(
            title="小红书API服务",
            description="独立的小红书爬虫API服务",
            version="1.0.0"
        )
        self.crawler: Optional[XiaoHongShuRealCrawler] = None
        self.login_crawler: Optional[XiaoHongShuLoginCrawler] = None
        self.setup_middleware()
        self.setup_routes()
    
    def setup_middleware(self):
        """设置中间件"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查"""
            return {
                "status": "ok",
                "service": "xhs-api-server",
                "version": "1.0.0"
            }
        
        @self.app.get("/cookie/status", response_model=CookieStatusResponse)
        async def get_cookie_status():
            """获取Cookie状态"""
            try:
                status = enhanced_cookie_manager.get_cookie_status()
                return CookieStatusResponse(
                    primary_exists=status.get('primary_exists', False),
                    backup_exists=status.get('backup_exists', False),
                    session_exists=status.get('session_exists', False),
                    cookie_count=status.get('cookie_count', 0),
                    save_time=status.get('save_time'),
                    remaining_days=status.get('remaining_days'),
                    is_valid=status.get('is_valid', False)
                )
            except Exception as e:
                logger.error(f"获取Cookie状态失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取Cookie状态失败: {str(e)}")
        
        @self.app.post("/login")
        async def interactive_login(request: LoginRequest, background_tasks: BackgroundTasks):
            """交互式登录"""
            try:
                if self.login_crawler is None:
                    self.login_crawler = XiaoHongShuLoginCrawler()
                
                # 在后台任务中执行登录
                background_tasks.add_task(self._perform_login, request.timeout)
                
                return {
                    "status": "started",
                    "message": "登录流程已启动，请在浏览器中完成登录",
                    "timeout": request.timeout
                }
            except Exception as e:
                logger.error(f"启动登录失败: {e}")
                raise HTTPException(status_code=500, detail=f"启动登录失败: {str(e)}")
        
        @self.app.post("/search")
        async def search_notes(request: SearchRequest):
            """搜索小红书笔记"""
            try:
                if self.crawler is None:
                    self.crawler = XiaoHongShuRealCrawler()
                    await self.crawler.start()
                
                # 检查登录状态
                if not self.crawler.is_logged_in:
                    raise HTTPException(status_code=401, detail="未登录，请先完成登录")
                
                # 执行搜索
                results = await self.crawler.search(
                    keyword=request.keyword,
                    max_notes=request.limit
                )
                
                return {
                    "status": "success",
                    "keyword": request.keyword,
                    "count": len(results),
                    "results": results
                }
            except Exception as e:
                error_msg = str(e)
                error_trace = traceback.format_exc()
                logger.error(f"搜索失败: {error_msg}")
                logger.error(f"错误堆栈: {error_trace}")
                raise HTTPException(status_code=500, detail=f"搜索失败: {error_msg}")
        
        @self.app.post("/crawler/start")
        async def start_crawler():
            """启动爬虫"""
            try:
                if self.crawler is None:
                    self.crawler = XiaoHongShuRealCrawler()
                
                await self.crawler.start()
                
                return {
                    "status": "success",
                    "message": "爬虫启动成功",
                    "is_logged_in": self.crawler.is_logged_in
                }
            except Exception as e:
                logger.error(f"启动爬虫失败: {e}")
                raise HTTPException(status_code=500, detail=f"启动爬虫失败: {str(e)}")
        
        @self.app.post("/crawler/stop")
        async def stop_crawler():
            """停止爬虫"""
            try:
                if self.crawler:
                    await self.crawler.close()
                    self.crawler = None
                
                if self.login_crawler:
                    await self.login_crawler.close()
                    self.login_crawler = None
                
                return {
                    "status": "success",
                    "message": "爬虫已停止"
                }
            except Exception as e:
                error_msg = str(e)
                error_trace = traceback.format_exc()
                logger.error(f"搜索失败: {error_msg}")
                logger.error(f"错误堆栈: {error_trace}")
                raise HTTPException(status_code=500, detail=f"搜索失败: {error_msg}")
    
    async def _perform_login(self, timeout: int):
        """执行登录流程"""
        try:
            if self.login_crawler is None:
                self.login_crawler = XiaoHongShuLoginCrawler()
            
            # XiaoHongShuLoginCrawler没有start方法，interactive_login会自动启动内部的crawler
            success = await self.login_crawler.interactive_login()
            
            if success:
                logger.info("✅ 登录成功")
            else:
                logger.warning("❌ 登录失败或超时")
                
        except Exception as e:
            logger.error(f"登录过程中出错: {e}")
        finally:
            if self.login_crawler:
                await self.login_crawler.close()

# 创建服务器实例
server = XHSAPIServer()
app = server.app

if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(
        "xhs_api_server:app",
        host="0.0.0.0",
        port=8002,
        reload=False,  # 禁用重载以避免事件循环问题
        log_level="info"
    )