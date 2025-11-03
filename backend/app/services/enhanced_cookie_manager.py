"""
增强的Cookie管理器
改进Cookie持久化机制，解决重启后失效问题
"""

import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime, timedelta

from app.platforms.xhs.playwright_crawler import PlaywrightXHSCrawler


class EnhancedCookieManager:
    """增强的Cookie管理器"""
    
    def __init__(self):
        # 统一使用 data/cookies 目录
        self.cookies_dir = Path(__file__).parent.parent.parent / "data" / "cookies"
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        
        # 多个Cookie文件，提高容错性
        self.primary_cookies_file = self.cookies_dir / "xhs_cookies_primary.json"
        self.backup_cookies_file = self.cookies_dir / "xhs_cookies_backup.json"
        self.session_cookies_file = self.cookies_dir / "xhs_session.json"
        
        # Cookie有效期配置
        self.cookie_max_age_days = 30  # 增加到30天
        self.session_max_age_hours = 12  # 会话最大12小时
    
    async def save_cookies_enhanced(self, context, user_agent: str = None) -> bool:
        """
        增强的Cookie保存方法
        
        Args:
            context: Playwright浏览器上下文
            user_agent: 用户代理字符串
            
        Returns:
            bool: 是否保存成功
        """
        try:
            cookies = await context.cookies()
            current_time = int(time.time())
            
            # 创建增强的Cookie数据结构
            cookie_data = {
                'cookies': cookies,
                'saved_at': current_time,
                'saved_at_readable': datetime.fromtimestamp(current_time).isoformat(),
                'user_agent': user_agent,
                'version': '2.0',  # 版本标识
                'domain': 'xiaohongshu.com',
                'expires_at': current_time + (self.cookie_max_age_days * 24 * 3600),
                'session_info': {
                    'login_method': 'qr_code',
                    'browser': 'playwright',
                    'platform': 'desktop'
                },
                'validation': {
                    'last_validated': current_time,
                    'validation_count': 0,
                    'success_count': 0
                }
            }
            
            # 保存到主文件
            success_primary = await self._save_to_file(self.primary_cookies_file, cookie_data)
            
            # 保存到备份文件
            success_backup = await self._save_to_file(self.backup_cookies_file, cookie_data)
            
            # 保存会话信息
            session_data = {
                'session_id': f"xhs_session_{current_time}",
                'created_at': current_time,
                'last_activity': current_time,
                'expires_at': current_time + (self.session_max_age_hours * 3600),
                'cookie_file': str(self.primary_cookies_file),
                'status': 'active'
            }
            success_session = await self._save_to_file(self.session_cookies_file, session_data)
            
            if success_primary:
                logger.info(f"✅ Cookie已保存到主文件: {self.primary_cookies_file}")
                logger.info(f"📝 保存了 {len(cookies)} 个cookie")
                logger.info(f"⏰ 有效期至: {datetime.fromtimestamp(cookie_data['expires_at']).strftime('%Y-%m-%d %H:%M:%S')}")
                
                if success_backup:
                    logger.info(f"💾 备份文件已创建: {self.backup_cookies_file}")
                
                return True
            else:
                logger.error("❌ Cookie保存失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 保存Cookie时发生异常: {e}")
            return False
    
    async def load_cookies_enhanced(self, context) -> bool:
        """
        增强的Cookie加载方法
        
        Args:
            context: Playwright浏览器上下文
            
        Returns:
            bool: 是否加载成功
        """
        try:
            # 尝试从主文件加载
            cookie_data = await self._load_from_file(self.primary_cookies_file)
            
            # 如果主文件失败，尝试备份文件
            if not cookie_data:
                logger.warning("⚠️ 主Cookie文件加载失败，尝试备份文件")
                cookie_data = await self._load_from_file(self.backup_cookies_file)
            
            if not cookie_data:
                logger.info("📂 未找到有效的Cookie文件")
                return False
            
            # 验证Cookie数据
            if not await self._validate_cookie_data(cookie_data):
                logger.warning("⚠️ Cookie数据验证失败")
                return False
            
            # 加载Cookie到浏览器上下文
            cookies = cookie_data.get('cookies', [])
            await context.add_cookies(cookies)
            
            # 更新验证信息
            await self._update_validation_info(cookie_data)
            
            logger.info(f"✅ 成功加载 {len(cookies)} 个cookie")
            return True
            
        except Exception as e:
            logger.error(f"❌ 加载Cookie时发生异常: {e}")
            return False
    
    async def validate_cookies_with_test(self, context) -> bool:
        """
        通过实际访问测试Cookie有效性
        
        Args:
            context: Playwright浏览器上下文
            
        Returns:
            bool: Cookie是否有效
        """
        try:
            page = await context.new_page()
            
            # 设置更真实的请求头
            await page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            # 访问小红书首页
            response = await page.goto(
                "https://www.xiaohongshu.com/explore", 
                timeout=15000,
                wait_until='domcontentloaded'
            )
            
            if not response or response.status != 200:
                logger.warning(f"⚠️ 页面访问失败，状态码: {response.status if response else 'None'}")
                await page.close()
                return False
            
            # 等待页面加载
            await asyncio.sleep(3)
            
            # 检查是否被重定向到登录页面
            current_url = page.url
            page_content = await page.content()
            
            await page.close()
            
            # 多重检测登录状态
            login_indicators = [
                "login" in current_url.lower(),
                "signin" in current_url.lower(),
                "登录" in page_content,
                "sign-in" in page_content.lower(),
                "请登录" in page_content,
                "立即登录" in page_content
            ]
            
            if any(login_indicators):
                logger.warning("⚠️ 检测到需要登录，Cookie可能已失效")
                return False
            
            # 检查是否有用户相关元素（更精确的登录检测）
            success_indicators = [
                "explore" in current_url,
                "用户" in page_content,
                "个人中心" in page_content,
                "我的" in page_content
            ]
            
            if any(success_indicators):
                logger.info("✅ Cookie验证成功，用户已登录")
                return True
            else:
                logger.warning("⚠️ 无法确定登录状态")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cookie验证过程中发生异常: {e}")
            return False
    
    async def _save_to_file(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """保存数据到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"❌ 保存文件失败 {file_path}: {e}")
            return False
    
    async def _load_from_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """从文件加载数据"""
        try:
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ 加载文件失败 {file_path}: {e}")
            return None
    
    async def _validate_cookie_data(self, cookie_data: Dict[str, Any]) -> bool:
        """验证Cookie数据的有效性"""
        try:
            # 检查基本结构
            if not isinstance(cookie_data, dict):
                return False
            
            cookies = cookie_data.get('cookies', [])
            if not cookies:
                logger.warning("⚠️ Cookie数据为空")
                return False
            
            saved_at = cookie_data.get('saved_at', 0)
            expires_at = cookie_data.get('expires_at', 0)
            current_time = int(time.time())
            
            # 检查是否过期
            if expires_at > 0 and current_time > expires_at:
                logger.warning("⚠️ Cookie已过期")
                return False
            
            # 检查保存时间是否合理
            if saved_at > 0:
                age_days = (current_time - saved_at) / (24 * 3600)
                if age_days > self.cookie_max_age_days:
                    logger.warning(f"⚠️ Cookie过于陈旧 ({age_days:.1f}天)")
                    return False
                else:
                    logger.info(f"📅 Cookie年龄: {age_days:.1f} 天")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 验证Cookie数据时发生异常: {e}")
            return False
    
    async def _update_validation_info(self, cookie_data: Dict[str, Any]):
        """更新验证信息"""
        try:
            if 'validation' not in cookie_data:
                cookie_data['validation'] = {}
            
            cookie_data['validation']['last_validated'] = int(time.time())
            cookie_data['validation']['validation_count'] = cookie_data['validation'].get('validation_count', 0) + 1
            
            # 保存更新后的数据
            await self._save_to_file(self.primary_cookies_file, cookie_data)
            
        except Exception as e:
            logger.error(f"❌ 更新验证信息失败: {e}")
    
    def get_cookie_status(self) -> Dict[str, Any]:
        """获取Cookie状态信息"""
        try:
            status = {
                'primary_exists': self.primary_cookies_file.exists(),
                'backup_exists': self.backup_cookies_file.exists(),
                'session_exists': self.session_cookies_file.exists(),
                'files': []
            }
            
            for file_path, name in [
                (self.primary_cookies_file, 'primary'),
                (self.backup_cookies_file, 'backup'),
                (self.session_cookies_file, 'session')
            ]:
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        file_info = {
                            'name': name,
                            'path': str(file_path),
                            'size': file_path.stat().st_size,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        }
                        
                        if name != 'session':
                            file_info.update({
                                'cookie_count': len(data.get('cookies', [])),
                                'saved_at': data.get('saved_at_readable', 'Unknown'),
                                'expires_at': datetime.fromtimestamp(data.get('expires_at', 0)).isoformat() if data.get('expires_at') else 'Unknown'
                            })
                        
                        status['files'].append(file_info)
                        
                    except Exception as e:
                        status['files'].append({
                            'name': name,
                            'path': str(file_path),
                            'error': str(e)
                        })
            
            return status
            
        except Exception as e:
            return {'error': str(e)}
    
    def clear_all_cookies(self):
        """清除所有Cookie文件"""
        try:
            files_removed = []
            for file_path in [self.primary_cookies_file, self.backup_cookies_file, self.session_cookies_file]:
                if file_path.exists():
                    file_path.unlink()
                    files_removed.append(str(file_path))
            
            if files_removed:
                logger.info(f"🗑️ 已清除Cookie文件: {', '.join(files_removed)}")
            else:
                logger.info("📂 没有找到Cookie文件")
                
        except Exception as e:
            logger.error(f"❌ 清除Cookie文件失败: {e}")
    
    async def validate_cookies_standalone(self) -> bool:
        """
        独立验证Cookie有效性（不需要外部context）
        
        Returns:
            bool: Cookie是否有效
        """
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                
                # 尝试加载Cookie
                success = await self.load_cookies_enhanced(context)
                if not success:
                    await browser.close()
                    return False
                
                # 验证Cookie
                is_valid = await self.validate_cookies_with_test(context)
                await browser.close()
                return is_valid
                
        except Exception as e:
            logger.error(f"❌ 独立验证Cookie失败: {e}")
            return False


# 全局实例
enhanced_cookie_manager = EnhancedCookieManager()