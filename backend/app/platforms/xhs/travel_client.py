"""
小红书旅游数据客户端
专门用于旅游规划系统的数据获取
"""

import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime

from .simple_crawler import SimpleXHSCrawler


class XHSTravelClient:
    """小红书旅游数据客户端"""
    
    def __init__(self):
        self.crawler = SimpleXHSCrawler()
        self._initialized = False
        
    async def init(self):
        """初始化客户端"""
        if not self._initialized:
            await self.crawler.init_session()
            self._initialized = True
            logger.info("小红书旅游客户端初始化成功")
            
    async def close(self):
        """关闭客户端"""
        if self._initialized:
            await self.crawler.close_session()
            self._initialized = False
            logger.info("小红书旅游客户端已关闭")
            
    async def get_note_by_keyword(
        self, 
        keyword: str, 
        page: int = 1, 
        page_size: int = 20, 
        sort: str = "general",
        note_type: str = "all"
    ) -> Dict[str, Any]:
        """
        根据关键词获取笔记数据
        
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
                await self.init()
                
            logger.info(f"开始搜索小红书笔记: {keyword}")
            
            # 使用爬虫获取数据
            notes_data = await self.crawler.search_notes(
                keyword=keyword,
                page=page,
                page_size=page_size
            )
            
            # 转换为标准格式
            formatted_notes = []
            for note in notes_data:
                formatted_note = self._format_note_data(note)
                formatted_notes.append(formatted_note)
                
            result = {
                'success': True,
                'data': {
                    'items': formatted_notes,
                    'has_more': len(formatted_notes) >= page_size,
                    'cursor': f"{page}_{page_size}",
                    'total': len(formatted_notes)
                },
                'message': f"成功获取 {len(formatted_notes)} 条笔记",
                'keyword': keyword,
                'fetch_time': datetime.now().isoformat()
            }
            
            logger.info(f"成功获取小红书笔记: {keyword}, 数量: {len(formatted_notes)}")
            return result
            
        except Exception as e:
            logger.error(f"获取小红书笔记失败: {keyword}, 错误: {e}")
            return {
                'success': False,
                'data': {'items': [], 'has_more': False, 'cursor': '', 'total': 0},
                'message': f"获取失败: {str(e)}",
                'keyword': keyword,
                'fetch_time': datetime.now().isoformat()
            }
            
    def _format_note_data(self, raw_note: Dict[str, Any]) -> Dict[str, Any]:
        """格式化笔记数据为标准格式"""
        return {
            'id': raw_note.get('note_id', ''),
            'model_type': 'note',
            'note_card': {
                'type': raw_note.get('type', 'normal'),
                'display_title': raw_note.get('title', ''),
                'user': {
                    'user_id': raw_note.get('user_info', {}).get('user_id', ''),
                    'nickname': raw_note.get('user_info', {}).get('nickname', ''),
                    'avatar': raw_note.get('user_info', {}).get('avatar', ''),
                    'ip_location': raw_note.get('user_info', {}).get('ip_location', '')
                },
                'interact_info': {
                    'collected_count': raw_note.get('collected_count', 0),
                    'comment_count': raw_note.get('comment_count', 0),
                    'liked_count': raw_note.get('liked_count', 0),
                    'share_count': raw_note.get('share_count', 0)
                },
                'cover': {
                    'url': raw_note.get('img_urls', [''])[0] if raw_note.get('img_urls') else '',
                    'width': 1080,
                    'height': 1440
                },
                'tag_list': [
                    {'name': tag, 'type': 'topic'} 
                    for tag in raw_note.get('tag_list', [])
                ],
                'time': raw_note.get('time', 0),
                'last_update_time': raw_note.get('last_update_time', 0)
            },
            'track_id': f"track_{raw_note.get('note_id', '')}",
            'relevance_score': raw_note.get('relevance_score', 0.8),
            'source': raw_note.get('source', 'xiaohongshu_api'),
            # 保留原始数据用于详细分析
            '_raw_data': raw_note
        }
        
    async def get_note_detail(self, note_id: str) -> Optional[Dict[str, Any]]:
        """获取笔记详情"""
        try:
            if not self._initialized:
                await self.init()
                
            detail = await self.crawler.get_note_detail(note_id)
            return detail
            
        except Exception as e:
            logger.error(f"获取笔记详情失败: {note_id}, 错误: {e}")
            return None
            
    async def search_travel_notes(
        self, 
        destination: str, 
        keywords: Optional[List[str]] = None,
        max_notes: int = 50
    ) -> List[Dict[str, Any]]:
        """
        搜索旅游相关笔记
        
        Args:
            destination: 目的地
            keywords: 额外关键词
            max_notes: 最大笔记数量
            
        Returns:
            笔记数据列表
        """
        try:
            if not self._initialized:
                await self.init()
                
            all_notes = []
            search_keywords = [destination]
            
            if keywords:
                search_keywords.extend(keywords)
            else:
                # 添加默认的旅游相关关键词
                search_keywords.extend([
                    f"{destination}旅游",
                    f"{destination}攻略",
                    f"{destination}美食",
                    f"{destination}景点"
                ])
                
            # 对每个关键词进行搜索
            for keyword in search_keywords:
                try:
                    result = await self.get_note_by_keyword(
                        keyword=keyword,
                        page_size=min(20, max_notes // len(search_keywords))
                    )
                    
                    if result['success']:
                        notes = result['data']['items']
                        all_notes.extend(notes)
                        
                    # 添加延迟避免请求过快
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"搜索关键词失败: {keyword}, 错误: {e}")
                    continue
                    
            # 去重和排序
            unique_notes = self._deduplicate_notes(all_notes)
            sorted_notes = sorted(
                unique_notes, 
                key=lambda x: x.get('relevance_score', 0), 
                reverse=True
            )
            
            # 限制数量
            final_notes = sorted_notes[:max_notes]
            
            logger.info(f"成功搜索到 {len(final_notes)} 条旅游笔记: {destination}")
            return final_notes
            
        except Exception as e:
            logger.error(f"搜索旅游笔记失败: {destination}, 错误: {e}")
            return []
            
    def _deduplicate_notes(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重笔记数据"""
        seen_ids = set()
        unique_notes = []
        
        for note in notes:
            note_id = note.get('id', '')
            if note_id and note_id not in seen_ids:
                seen_ids.add(note_id)
                unique_notes.append(note)
                
        return unique_notes
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# 创建全局客户端实例
xhs_travel_client = XHSTravelClient()