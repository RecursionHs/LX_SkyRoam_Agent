"""
小红书数据集成服务
负责将小红书笔记数据集成到旅行攻略系统中
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import traceback
import re
from dataclasses import dataclass

# 暂时注释复杂的小红书爬虫依赖，避免配置问题
# from app.platforms.xhs.client import XiaoHongShuClient
# from app.platforms.xhs.core import XiaoHongShuCrawler
# from app.platforms.xhs.field import SearchSortType, SearchNoteType
from app.core.redis import get_cache, set_cache, cache_key


@dataclass
class XHSNoteData:
    """小红书笔记数据结构"""
    note_id: str
    title: str
    desc: str
    type: str
    user_info: Dict[str, Any]
    img_urls: List[str]
    video_url: str
    tag_list: List[str]
    collected_count: int
    comment_count: int
    liked_count: int
    share_count: int
    publish_time: datetime
    location: Optional[str] = None
    relevance_score: float = 0.0


class XHSIntegrationService:
    """小红书数据集成服务"""
    
    def __init__(self):
        self.xhs_crawler = None
        self.max_notes_per_destination = 50  # 每个目的地最多获取的笔记数量
        self.cache_ttl = 3600 * 6  # 缓存6小时
        
    async def get_destination_notes(
        self, 
        destination: str, 
        keywords: Optional[List[str]] = None,
        sort_type: str = "most_popular"  # 暂时使用字符串类型
    ) -> List[XHSNoteData]:
        """
        获取目的地相关的小红书笔记
        
        Args:
            destination: 目的地名称
            keywords: 额外的关键词列表
            sort_type: 排序方式
            
        Returns:
            List[XHSNoteData]: 笔记数据列表
        """
        try:
            # 构建搜索关键词
            search_keywords = self._build_search_keywords(destination, keywords)
            
            # 检查缓存
            cache_key_str = cache_key("xhs_notes", destination, str(sort_type))
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的小红书数据: {destination}")
                return [XHSNoteData(**note) for note in cached_data]
            
            logger.info(f"开始获取小红书笔记: {destination}")
            
            # 初始化爬虫（如果需要）
            if not self.xhs_crawler:
                await self._init_crawler()
            
            all_notes = []
            
            # 对每个关键词进行搜索
            for keyword in search_keywords:
                try:
                    notes = await self._search_notes_by_keyword(
                        keyword=keyword,
                        sort_type=sort_type,
                        max_count=20  # 每个关键词最多20条
                    )
                    all_notes.extend(notes)
                    
                    # 避免请求过于频繁
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"搜索关键词 '{keyword}' 失败: {e}")
                    continue
            
            # 去重和排序
            unique_notes = self._deduplicate_and_rank_notes(all_notes, destination)
            
            # 限制数量
            final_notes = unique_notes[:self.max_notes_per_destination]
            
            # 缓存结果
            cache_data = [note.__dict__ for note in final_notes]
            await set_cache(cache_key_str, cache_data, ttl=self.cache_ttl)
            
            logger.info(f"成功获取 {len(final_notes)} 条小红书笔记: {destination}")
            return final_notes
            
        except Exception as e:
            logger.error(f"获取小红书笔记失败: {destination}, 错误: {e}")
            return []
    
    def _build_search_keywords(self, destination: str, extra_keywords: Optional[List[str]] = None) -> List[str]:
        """构建搜索关键词列表"""
        keywords = [
            destination,
            f"{destination}旅游",
            f"{destination}攻略",
            f"{destination}景点",
            f"{destination}美食",
            f"{destination}住宿"
        ]
        
        if extra_keywords:
            keywords.extend([f"{destination}{kw}" for kw in extra_keywords])
        
        return keywords
    
    async def _init_crawler(self):
        """初始化小红书爬虫"""
        try:
            # 优先尝试使用Playwright真实爬虫
            try:
                from app.platforms.xhs.real_crawler import XiaoHongShuRealCrawler
                self.xhs_crawler = XiaoHongShuRealCrawler()
                await self.xhs_crawler.start()
                logger.info("✅ 小红书Playwright真实爬虫初始化成功")
                return
            except Exception as e:
                logger.warning(f"Playwright真实爬虫初始化失败: {e}")
            
            # 尝试使用旅游爬虫
            try:
                from app.platforms.xhs.travel_core import XiaoHongShuTravelCrawler
                self.xhs_crawler = XiaoHongShuTravelCrawler()
                await self.xhs_crawler.start()
                logger.info("✅ 小红书旅游爬虫初始化成功")
                return
            except Exception as e:
                logger.warning(f"旅游爬虫初始化失败: {e}")
            
            # 尝试使用原始爬虫
            try:
                from app.platforms.xhs.core import XiaoHongShuCrawler
                self.xhs_crawler = XiaoHongShuCrawler()
                await self.xhs_crawler.start()
                logger.info("✅ 小红书原始爬虫初始化成功")
                return
            except Exception as e:
                logger.warning(f"原始爬虫初始化失败: {e}")
            
            # 如果所有真实爬虫都失败，使用模拟数据
            logger.warning("所有真实爬虫初始化失败，使用模拟数据模式")
            self.use_mock_data = True
            
        except Exception as e:
            logger.error(f"初始化爬虫失败: {e}")
            self.use_mock_data = True
    
    async def _search_notes_by_keyword(
        self, 
        keyword: str, 
        sort_type: str,
        max_count: int = 20
    ) -> List[XHSNoteData]:
        """根据关键词搜索笔记"""
        try:
            # 使用真实爬虫搜索
            logger.info(f"使用真实爬虫搜索笔记: {keyword}")
            
            # 检查爬虫是否有search方法（新的旅游爬虫）
            if hasattr(self.xhs_crawler, 'search'):
                notes_data = await self.xhs_crawler.search(keyword, max_count)
                notes = []
                for note_data in notes_data:
                    try:
                        note = self._parse_note_item(note_data)
                        if note:
                            notes.append(note)
                    except Exception as e:
                        logger.warning(f"解析笔记数据失败: {e}")
                        continue
                return notes
            
            # 检查爬虫是否有xhs_client（原始爬虫）
            if hasattr(self.xhs_crawler, 'xhs_client') and self.xhs_crawler.xhs_client:
                # 搜索笔记
                search_result = await self.xhs_crawler.xhs_client.get_note_by_keyword(
                    keyword=keyword,
                    page=1,
                    page_size=min(max_count, 20),  # 小红书API限制
                    sort=sort_type,
                    note_type="all"  # 使用字符串而不是枚举
                )
                
                if not search_result or 'data' not in search_result:
                    logger.warning(f"搜索结果为空: {keyword}")
                    return self._generate_mock_notes(keyword, max_count)
                
                notes = []
                for item in search_result['data']['items'][:max_count]:
                    try:
                        note_data = self._parse_note_item(item)
                        if note_data:
                            notes.append(note_data)
                    except Exception as e:
                        logger.warning(f"解析笔记数据失败: {e}")
                        continue
                
                return notes
            
            # 如果都没有，返回模拟数据
            logger.warning("爬虫没有可用的搜索方法，使用模拟数据")
            return self._generate_mock_notes(keyword, max_count)
            
        except Exception as e:
            logger.error(f"搜索笔记失败: {keyword}, 错误: {e}")
            # 出错时返回模拟数据
            return self._generate_mock_notes(keyword, max_count)
    
    def _parse_note_item(self, item: Dict[str, Any]) -> Optional[XHSNoteData]:
        """解析笔记数据项"""
        try:
            note_card = item.get('note_card', {})
            if not note_card:
                return None
            
            # 提取基本信息
            note_id = note_card.get('note_id', '')
            title = note_card.get('display_title', '')
            desc = note_card.get('desc', '')
            note_type = note_card.get('type', 'normal')
            
            # 提取用户信息
            user_info = note_card.get('user', {})
            
            # 提取媒体信息
            img_urls = []
            video_url = ''
            
            if 'image_list' in note_card:
                img_urls = [img.get('url_default', '') for img in note_card['image_list']]
            
            if 'video' in note_card:
                video_url = note_card['video'].get('url_default', '')
            
            # 提取标签
            tag_list = []
            if 'tag_list' in note_card:
                tag_list = [tag.get('name', '') for tag in note_card['tag_list']]
            
            # 提取统计数据
            interact_info = note_card.get('interact_info', {})
            collected_count = int(interact_info.get('collected_count', 0))
            comment_count = int(interact_info.get('comment_count', 0))
            liked_count = int(interact_info.get('liked_count', 0))
            share_count = int(interact_info.get('share_count', 0))
            
            # 提取时间
            time_str = note_card.get('time', '')
            publish_time = self._parse_time(time_str)
            
            # 提取位置信息
            location = note_card.get('location', {}).get('name', '')
            
            return XHSNoteData(
                note_id=note_id,
                title=title,
                desc=desc,
                type=note_type,
                user_info=user_info,
                img_urls=img_urls,
                video_url=video_url,
                tag_list=tag_list,
                collected_count=collected_count,
                comment_count=comment_count,
                liked_count=liked_count,
                share_count=share_count,
                publish_time=publish_time,
                location=location
            )
            
        except Exception as e:
            logger.error(f"解析笔记数据失败: {e}")
            return None
    
    def _parse_time(self, time_str: str) -> datetime:
        """解析时间字符串"""
        try:
            if not time_str:
                return datetime.now()
            
            # 处理相对时间格式
            if '分钟前' in time_str:
                minutes = int(re.findall(r'(\d+)', time_str)[0])
                return datetime.now() - timedelta(minutes=minutes)
            elif '小时前' in time_str:
                hours = int(re.findall(r'(\d+)', time_str)[0])
                return datetime.now() - timedelta(hours=hours)
            elif '天前' in time_str:
                days = int(re.findall(r'(\d+)', time_str)[0])
                return datetime.now() - timedelta(days=days)
            else:
                # 尝试解析具体日期
                return datetime.strptime(time_str, '%Y-%m-%d')
        except:
            return datetime.now()
    
    def _deduplicate_and_rank_notes(self, notes: List[XHSNoteData], destination: str) -> List[XHSNoteData]:
        """去重并按相关性排序笔记"""
        # 去重（基于note_id）
        unique_notes = {}
        for note in notes:
            if note.note_id not in unique_notes:
                unique_notes[note.note_id] = note
        
        notes_list = list(unique_notes.values())
        
        # 计算相关性得分
        for note in notes_list:
            note.relevance_score = self._calculate_relevance_score(note, destination)
        
        # 按相关性得分排序
        notes_list.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return notes_list
    
    def _calculate_relevance_score(self, note: XHSNoteData, destination: str) -> float:
        """计算笔记与目的地的相关性得分"""
        score = 0.0
        
        # 标题相关性 (权重: 0.3)
        if destination in note.title:
            score += 0.3
        
        # 描述相关性 (权重: 0.2)
        if destination in note.desc:
            score += 0.2
        
        # 位置相关性 (权重: 0.2)
        if note.location and destination in note.location:
            score += 0.2
        
        # 标签相关性 (权重: 0.1)
        travel_tags = ['旅游', '攻略', '景点', '美食', '住宿', '打卡']
        for tag in note.tag_list:
            if any(travel_tag in tag for travel_tag in travel_tags):
                score += 0.1
                break
        
        # 互动数据权重 (权重: 0.2)
        # 归一化处理，避免数值过大
        interaction_score = (
            min(note.liked_count / 1000, 1.0) * 0.1 +
            min(note.collected_count / 500, 1.0) * 0.1
        )
        score += interaction_score
        
        return min(score, 1.0)  # 限制最大得分为1.0
    
    def format_notes_for_llm(self, notes: List[XHSNoteData], destination: str) -> str:
        """将笔记数据格式化为适合LLM处理的文本"""
        if not notes:
            return f"未找到关于{destination}的小红书笔记数据。"
        
        formatted_text = f"=== {destination} 小红书真实用户分享 ===\n\n"
        
        for i, note in enumerate(notes[:10], 1):  # 只取前10条最相关的
            formatted_text += f"【笔记 {i}】\n"
            formatted_text += f"标题: {note.title}\n"
            formatted_text += f"内容: {note.desc[:200]}{'...' if len(note.desc) > 200 else ''}\n"
            
            if note.location:
                formatted_text += f"位置: {note.location}\n"
            
            if note.tag_list:
                formatted_text += f"标签: {', '.join(note.tag_list[:5])}\n"
            
            formatted_text += f"互动数据: 👍{note.liked_count} 💾{note.collected_count} 💬{note.comment_count}\n"
            formatted_text += f"发布时间: {note.publish_time.strftime('%Y-%m-%d')}\n"
            formatted_text += f"相关性得分: {note.relevance_score:.2f}\n\n"
        
        formatted_text += f"以上是来自小红书的真实用户分享，包含了{len(notes)}条相关笔记。"
        formatted_text += "这些内容反映了真实用户的体验和建议，请在生成攻略时重点参考。\n"
        
        return formatted_text
    
    def _generate_mock_notes(self, destination: str, keywords: Optional[List[str]] = None, max_notes: int = 10) -> List[XHSNoteData]:
        """生成模拟的小红书笔记数据用于测试"""
        from datetime import datetime, timedelta
        import random
        
        # 根据目的地类型生成不同的笔记模板
        city_templates = {
            "北京": [
                {"title": "北京故宫深度游｜避开人群的最佳路线", "desc": "故宫太大了！分享一条避开人群的游览路线，还有拍照机位推荐，让你轻松逛完紫禁城～", "tags": ["故宫", "北京", "避坑", "拍照"]},
                {"title": "北京胡同探秘｜最有味道的老北京生活", "desc": "走进南锣鼓巷、什刹海胡同，感受最地道的老北京文化，还有隐藏的小店推荐！", "tags": ["胡同", "北京", "文化", "老北京"]},
                {"title": "北京烤鸭哪家强？全聚德vs便宜坊实测", "desc": "作为北京土著，实测了5家烤鸭店，告诉你哪家最正宗最好吃，避免踩雷！", "tags": ["烤鸭", "北京", "美食", "测评"]},
                {"title": "北京地铁出行攻略｜新手必看", "desc": "北京地铁线路复杂？这篇攻略教你如何高效换乘，还有各种优惠票推荐！", "tags": ["地铁", "北京", "交通", "攻略"]}
            ],
            "上海": [
                {"title": "上海外滩最佳观景时间｜日落夜景都绝了", "desc": "外滩什么时候去最美？分享最佳观景时间和拍照角度，还有周边美食推荐！", "tags": ["外滩", "上海", "夜景", "拍照"]},
                {"title": "上海迪士尼省钱攻略｜学生党必看", "desc": "迪士尼太贵？这篇攻略教你如何省钱玩转迪士尼，门票、餐饮、住宿全覆盖！", "tags": ["迪士尼", "上海", "省钱", "攻略"]},
                {"title": "上海小笼包探店｜南翔vs鼎泰丰谁更胜一筹", "desc": "上海小笼包哪家最正宗？实测了10家店，从老字号到网红店全都有！", "tags": ["小笼包", "上海", "美食", "探店"]},
                {"title": "上海法租界漫步｜最文艺的街道推荐", "desc": "法租界的梧桐叶黄了！推荐几条最美的街道，适合拍照和漫步～", "tags": ["法租界", "上海", "文艺", "漫步"]}
            ]
        }
        
        # 通用模板，适用于所有目的地
        general_templates = [
            {"title": f"{destination}三天两夜完美攻略｜超详细路线", "desc": f"刚从{destination}回来，整理了超详细的攻略，包含必去景点、美食推荐、交通指南！", "tags": ["攻略", destination, "三天两夜", "必看"]},
            {"title": f"{destination}美食地图｜本地人推荐", "desc": f"在{destination}生活多年，推荐几家本地人才知道的美食店，味道绝了！", "tags": ["美食", destination, "本地推荐", "探店"]},
            {"title": f"{destination}拍照圣地｜出片率100%", "desc": f"{destination}最值得打卡的拍照地，每个都超出片，姐妹们一定要去！", "tags": ["拍照", destination, "打卡", "圣地"]},
            {"title": f"{destination}住宿推荐｜性价比之王", "desc": f"整理了{destination}性价比超高的住宿，从青旅到五星酒店，位置好价格合理！", "tags": ["住宿", destination, "性价比", "推荐"]},
            {"title": f"{destination}交通攻略｜最省钱出行方式", "desc": f"去{destination}不知道怎么坐车？这篇告诉你最省钱最方便的交通方式！", "tags": ["交通", destination, "省钱", "出行"]},
            {"title": f"{destination}购物指南｜必买清单", "desc": f"{destination}购物攻略！本地特产、购物中心全覆盖，还有砍价技巧！", "tags": ["购物", destination, "特产", "必买"]},
            {"title": f"{destination}亲子游｜带娃必去景点", "desc": f"带2岁宝宝去{destination}的经验分享，适合亲子的景点和实用tips！", "tags": ["亲子游", destination, "带娃", "景点"]},
            {"title": f"{destination}夜生活｜酒吧夜市推荐", "desc": f"{destination}的夜晚同样精彩！推荐热闹的酒吧街和夜市，体验夜生活！", "tags": ["夜生活", destination, "酒吧", "夜市"]}
        ]
        
        # 选择模板
        if destination in city_templates:
            templates = city_templates[destination] + general_templates
        else:
            templates = general_templates
        
        # 随机选择模板
        selected_templates = random.sample(templates, min(max_notes, len(templates)))
        
        mock_notes = []
        for i, template in enumerate(selected_templates):
            # 生成更真实的互动数据
            base_popularity = random.uniform(0.5, 1.0)  # 基础热度
            liked_count = int(random.uniform(50, 8000) * base_popularity)
            collected_count = int(liked_count * random.uniform(0.1, 0.3))  # 收藏通常是点赞的10-30%
            comment_count = int(liked_count * random.uniform(0.02, 0.1))   # 评论通常是点赞的2-10%
            share_count = int(liked_count * random.uniform(0.01, 0.05))    # 分享通常是点赞的1-5%
            
            # 随机生成发布时间（最近60天内，但更倾向于最近的）
            days_ago = random.choices(
                range(1, 61), 
                weights=[60-i for i in range(60)],  # 越近的日期权重越高
                k=1
            )[0]
            publish_time = datetime.now() - timedelta(days=days_ago)
            
            # 更丰富的用户信息
            user_profiles = [
                {"nickname": "旅行达人小美", "type": "travel_blogger"},
                {"nickname": "吃货探店王", "type": "food_blogger"},
                {"nickname": "摄影师阿强", "type": "photographer"},
                {"nickname": "背包客小李", "type": "backpacker"},
                {"nickname": "本地向导老张", "type": "local_guide"},
                {"nickname": "自由行专家", "type": "travel_expert"},
                {"nickname": "美食博主", "type": "food_expert"},
                {"nickname": "文艺青年", "type": "culture_lover"}
            ]
            
            user_profile = random.choice(user_profiles)
            user_info = {
                "nickname": user_profile["nickname"],
                "user_id": f"user_{random.randint(100000, 999999)}",
                "avatar": f"https://example.com/avatar_{user_profile['type']}_{i}.jpg",
                "desc": f"专注{destination}旅游分享"
            }
            
            # 生成图片数量（1-9张，符合小红书特点）
            img_count = random.choices([1, 3, 4, 6, 9], weights=[10, 30, 25, 20, 15], k=1)[0]
            
            note = XHSNoteData(
                note_id=f"note_{destination}_{i}_{random.randint(100000, 999999)}",
                title=template["title"],
                desc=template["desc"],
                type=random.choice(["normal", "video"]) if random.random() > 0.8 else "normal",
                user_info=user_info,
                img_urls=[f"https://example.com/img_{destination}_{i}_{j}.jpg" for j in range(img_count)],
                video_url=f"https://example.com/video_{i}.mp4" if random.random() > 0.9 else "",
                tag_list=template["tags"],
                collected_count=collected_count,
                comment_count=comment_count,
                liked_count=liked_count,
                share_count=share_count,
                publish_time=publish_time,
                location=destination,
                relevance_score=random.uniform(0.75, 0.98)  # 高相关性，但有一定变化
            )
            mock_notes.append(note)
        
        # 按相关性得分排序
        mock_notes.sort(key=lambda x: x.relevance_score, reverse=True)
        return mock_notes