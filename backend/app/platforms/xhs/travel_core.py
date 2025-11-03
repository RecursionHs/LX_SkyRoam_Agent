"""
小红书旅游数据爬虫核心类
专门用于旅游规划系统的数据获取
"""

import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger

from .travel_client import XHSTravelClient


class XiaoHongShuTravelCrawler:
    """小红书旅游数据爬虫"""
    
    def __init__(self):
        self.xhs_client = XHSTravelClient()
        self._initialized = False
        
    async def start(self):
        """启动爬虫"""
        try:
            await self.xhs_client.init()
            self._initialized = True
            logger.info("小红书旅游爬虫启动成功")
        except Exception as e:
            logger.error(f"小红书旅游爬虫启动失败: {e}")
            raise
            
    async def close(self):
        """关闭爬虫"""
        try:
            if self._initialized:
                await self.xhs_client.close()
                self._initialized = False
                logger.info("小红书旅游爬虫已关闭")
        except Exception as e:
            logger.error(f"关闭小红书旅游爬虫失败: {e}")
            
    async def search(self, keyword: str, max_notes: int = 20) -> List[Dict[str, Any]]:
        """
        搜索笔记
        
        Args:
            keyword: 搜索关键词
            max_notes: 最大笔记数量
            
        Returns:
            笔记数据列表
        """
        try:
            if not self._initialized:
                await self.start()
                
            notes = await self.xhs_client.search_travel_notes(
                destination=keyword,
                max_notes=max_notes
            )
            
            return notes
            
        except Exception as e:
            logger.error(f"搜索笔记失败: {keyword}, 错误: {e}")
            return []
            
    async def get_note_by_keyword(
        self, 
        keyword: str, 
        page: int = 1, 
        page_size: int = 20, 
        sort: str = "general",
        note_type: str = "all"
    ) -> Dict[str, Any]:
        """
        根据关键词获取笔记
        
        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
            sort: 排序方式
            note_type: 笔记类型
            
        Returns:
            包含笔记数据的字典
        """
        try:
            if not self._initialized:
                await self.start()
                
            result = await self.xhs_client.get_note_by_keyword(
                keyword=keyword,
                page=page,
                page_size=page_size,
                sort=sort,
                note_type=note_type
            )
            
            return result
            
        except Exception as e:
            logger.error(f"获取笔记失败: {keyword}, 错误: {e}")
            return {
                'success': False,
                'data': {'items': [], 'has_more': False, 'cursor': '', 'total': 0},
                'message': f"获取失败: {str(e)}"
            }
            
    async def launch_browser(self, *args, **kwargs):
        """兼容性方法：启动浏览器（实际不需要浏览器）"""
        logger.info("使用HTTP客户端模式，无需启动浏览器")
        return None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# 为了兼容性，创建别名
XiaoHongShuCrawler = XiaoHongShuTravelCrawler