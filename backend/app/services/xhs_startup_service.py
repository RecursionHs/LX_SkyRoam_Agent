"""
小红书启动服务
负责在应用启动时自动检查和处理小红书登录
集成智能重试机制，无需额外的retry服务
"""

import asyncio
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from app.services.enhanced_cookie_manager import enhanced_cookie_manager
from app.platforms.xhs.real_crawler import XiaoHongShuRealCrawler, XiaoHongShuLoginCrawler


class XHSStartupService:
    """小红书启动服务 - 集成智能重试机制"""
    
    def __init__(self):
        self.cookie_manager = enhanced_cookie_manager
        self.login_crawler: Optional[XiaoHongShuLoginCrawler] = None
        self.real_crawler: Optional[XiaoHongShuRealCrawler] = None
        
        # 重试配置
        self.max_retries = 3
        self.base_delay = 2.0
        self.max_delay = 30.0
        self.backoff_multiplier = 2.0
        
        # 状态跟踪
        self.last_login_attempt = 0
        self.consecutive_failures = 0
        self.is_initialized = False
    
    async def initialize_xhs_service(self) -> bool:
        """
        初始化小红书服务 - 带智能重试
        
        Returns:
            bool: 是否成功初始化
        """
        try:
            logger.info("🔍 开始初始化小红书服务...")
            
            # 1. 检查现有Cookie是否有效
            if await self._check_existing_cookies_with_retry():
                logger.info("✅ 现有Cookie有效，小红书服务初始化成功")
                self.is_initialized = True
                self.consecutive_failures = 0
                return True
            
            # 2. 尝试智能登录（带重试）
            if await self._smart_login_with_retry():
                logger.info("✅ 智能登录成功，小红书服务初始化成功")
                self.is_initialized = True
                self.consecutive_failures = 0
                return True
            
            # 3. 如果所有尝试都失败，提供用户指导
            logger.warning("⚠️ 小红书服务初始化失败")
            logger.info("💡 请手动登录小红书：")
            logger.info("   方式1: python xhs_login_helper.py")
            logger.info("   方式2: python backend/app/crawlers/xhs/login_xhs.py")
            logger.info("   方式3: python backend/app/crawlers/xhs/cookie_manager.py")
            
            self.consecutive_failures += 1
            return False
            
        except Exception as e:
            logger.error(f"❌ 小红书服务初始化异常: {e}")
            self.consecutive_failures += 1
            return False
    
    async def _check_existing_cookies_with_retry(self) -> bool:
        """
        检查现有Cookie是否有效 - 带重试机制
        
        Returns:
            bool: Cookie是否有效
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"🔍 检查现有Cookie... (第 {attempt}/{self.max_retries} 次)")
                
                # 检查Cookie状态
                cookie_status = self.cookie_manager.get_cookie_status()
                if not cookie_status.get('primary_exists', False):
                    logger.info("📝 未找到主Cookie文件")
                    return False
                
                # 检查Cookie是否过期
                days_remaining = cookie_status.get('days_remaining', 0)
                if days_remaining <= 0:
                    logger.info("⏰ Cookie已过期")
                    return False
                
                # 使用独立验证方法
                is_valid = await self.cookie_manager.validate_cookies_standalone()
                
                if is_valid:
                    logger.info("✅ Cookie验证成功")
                    return True
                else:
                    logger.info(f"❌ Cookie验证失败 (第 {attempt} 次)")
                    
                    if attempt < self.max_retries:
                        delay = self._calculate_retry_delay(attempt)
                        logger.info(f"⏳ {delay:.1f} 秒后重试...")
                        await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"❌ 检查Cookie失败 (第 {attempt} 次): {e}")
                
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"⏳ {delay:.1f} 秒后重试...")
                    await asyncio.sleep(delay)
        
        logger.error("❌ 所有Cookie检查尝试均失败")
        return False
    
    async def _smart_login_with_retry(self) -> bool:
        """
        智能登录 - 带指数退避重试机制
        
        Returns:
            bool: 登录是否成功
        """
        # 检查是否需要等待冷却
        if self._should_skip_retry():
            logger.info("⏸️ 跳过登录重试（冷却期内）")
            return False
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"🔄 尝试智能登录 (第 {attempt}/{self.max_retries} 次)...")
                self.last_login_attempt = time.time()
                
                # 创建登录爬虫
                self.login_crawler = XiaoHongShuLoginCrawler()
                
                # 尝试登录（interactive_login方法会自动启动爬虫）
                success = await self.login_crawler.interactive_login()
                
                if success:
                    logger.info("✅ 智能登录成功")
                    
                    # 使用增强的Cookie保存方法
                    # 通过 login_crawler.crawler.playwright_crawler 访问 page 和 context
                    playwright_crawler = self.login_crawler.crawler.playwright_crawler
                    if playwright_crawler.page and playwright_crawler.context:
                        user_agent = await playwright_crawler.page.evaluate("navigator.userAgent")
                        await self.cookie_manager.save_cookies_enhanced(
                            playwright_crawler.context,
                            user_agent=user_agent
                        )
                    
                    # 清理登录爬虫
                    await self._cleanup_login_crawler()
                    
                    return True
                else:
                    logger.warning(f"❌ 第 {attempt} 次智能登录失败")
                    
                    # 清理登录爬虫
                    await self._cleanup_login_crawler()
                    
                    if attempt < self.max_retries:
                        delay = self._calculate_retry_delay(attempt)
                        logger.info(f"⏳ {delay:.1f} 秒后重试...")
                        await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"❌ 第 {attempt} 次登录尝试出错: {e}")
                
                # 清理登录爬虫
                await self._cleanup_login_crawler()
                
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"⏳ {delay:.1f} 秒后重试...")
                    await asyncio.sleep(delay)
        
        logger.error("❌ 所有智能登录尝试均失败")
        return False
    
    async def handle_login_required_error(self, error_context: str = "") -> bool:
        """
        处理需要登录的错误 - 运行时重试机制
        
        Args:
            error_context: 错误上下文信息
            
        Returns:
            bool: 是否成功恢复登录状态
        """
        logger.warning(f"🔄 检测到登录失效，尝试自动恢复... {error_context}")
        
        # 检查是否需要等待冷却
        if self._should_skip_retry():
            logger.info("⏸️ 跳过登录恢复（冷却期内）")
            return False
        
        # 尝试重新初始化
        success = await self.initialize_xhs_service()
        
        if success:
            logger.info("✅ 登录状态自动恢复成功")
        else:
            logger.error("❌ 登录状态自动恢复失败")
            await self._notify_manual_login_required()
        
        return success
    
    async def validate_and_retry_if_needed(self, operation_func, *args, **kwargs):
        """
        验证并在需要时重试操作
        
        Args:
            operation_func: 要执行的操作函数
            *args, **kwargs: 操作函数的参数
            
        Returns:
            操作结果
        """
        try:
            # 首先尝试执行操作
            return await operation_func(*args, **kwargs)
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # 检查是否是登录相关错误
            if any(keyword in error_msg for keyword in [
                'login', 'unauthorized', '401', '403', 
                'cookie', 'session', 'expired'
            ]):
                logger.warning(f"🔄 检测到登录相关错误，尝试自动恢复: {e}")
                
                # 尝试恢复登录状态
                if await self.handle_login_required_error(f"操作失败: {operation_func.__name__}"):
                    # 重试操作
                    logger.info("🔄 重试原始操作...")
                    return await operation_func(*args, **kwargs)
            
            # 如果不是登录错误或恢复失败，重新抛出异常
            raise e
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        计算重试延迟时间（指数退避）
        
        Args:
            attempt: 当前尝试次数
            
        Returns:
            float: 延迟时间（秒）
        """
        delay = self.base_delay * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, self.max_delay)
    
    def _should_skip_retry(self) -> bool:
        """
        检查是否应该跳过重试（冷却机制）
        
        Returns:
            bool: 是否应该跳过
        """
        if self.consecutive_failures >= 5:
            # 连续失败5次后，等待更长时间
            cooldown_period = 300  # 5分钟
        elif self.consecutive_failures >= 3:
            # 连续失败3次后，等待中等时间
            cooldown_period = 120  # 2分钟
        else:
            # 正常情况下的最小间隔
            cooldown_period = 30   # 30秒
        
        time_since_last = time.time() - self.last_login_attempt
        return time_since_last < cooldown_period
    
    async def _cleanup_login_crawler(self):
        """清理登录爬虫资源"""
        if self.login_crawler:
            try:
                await self.login_crawler.close()
            except Exception as e:
                logger.error(f"❌ 清理登录爬虫失败: {e}")
            finally:
                self.login_crawler = None
    
    async def _notify_manual_login_required(self):
        """通知需要手动登录"""
        logger.error("🚨 自动登录恢复失败，需要手动干预")
        logger.info("💡 请使用以下方式手动登录：")
        logger.info("   python xhs_login_helper.py")
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态信息
        
        Returns:
            Dict[str, Any]: 服务状态
        """
        return {
            'is_initialized': self.is_initialized,
            'consecutive_failures': self.consecutive_failures,
            'last_login_attempt': self.last_login_attempt,
            'cookie_status': self.cookie_manager.get_cookie_status(),
            'should_skip_retry': self._should_skip_retry()
        }
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.real_crawler:
                await self.real_crawler.close()
                self.real_crawler = None
            
            await self._cleanup_login_crawler()
                
        except Exception as e:
            logger.error(f"❌ 清理小红书服务资源失败: {e}")


# 全局实例
xhs_startup_service = XHSStartupService()


async def initialize_xhs_on_startup() -> bool:
    """
    在应用启动时初始化小红书服务
    
    Returns:
        bool: 是否成功初始化
    """
    return await xhs_startup_service.initialize_xhs_service()


async def cleanup_xhs_on_shutdown():
    """在应用关闭时清理小红书服务资源"""
    await xhs_startup_service.cleanup()


# 导出便捷函数供其他模块使用
async def handle_xhs_login_error(error_context: str = "") -> bool:
    """处理XHS登录错误的便捷函数"""
    return await xhs_startup_service.handle_login_required_error(error_context)


async def validate_and_retry_xhs_operation(operation_func, *args, **kwargs):
    """验证并重试XHS操作的便捷函数"""
    return await xhs_startup_service.validate_and_retry_if_needed(operation_func, *args, **kwargs)