"""
数据处理和格式化工具
"""
import json
import copy
from typing import Dict, Any, List, Optional, Set
from loguru import logger
from types import SimpleNamespace
from datetime import datetime, timedelta

DOMESTIC_KEYWORDS_CN = {
    "中国",
    "大陆",
    "内地",
    "北京",
    "上海",
    "广州",
    "深圳",
    "杭州",
    "南京",
    "苏州",
    "成都",
    "重庆",
    "西安",
    "武汉",
    "长沙",
    "厦门",
    "青岛",
    "三亚",
    "海口",
    "拉萨",
    "乌鲁木齐",
}


DOMESTIC_KEYWORDS_EN = {
    "beijing",
    "shanghai",
    "guangzhou",
    "shenzhen",
    "hangzhou",
    "suzhou",
    "nanjing",
    "chengdu",
    "chongqing",
    "wuhan",
    "xiamen",
    "sanya",
    "urumqi",
    "xi'an",
    "xian",
    "qingdao",
    "haikou",
    "lhasa",
    "china",
    "prc",
}

class DataProcessor:
    """数据处理器"""

    @staticmethod
    def to_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                if date_parser:
                    return date_parser.parse(value)
                return datetime.fromisoformat(value)
            except Exception:
                return None
        return None
    
    @staticmethod
    def format_traffic_info(traffic_conditions: Dict[str, Any]) -> str:
        """格式化路况信息"""
        if not traffic_conditions:
            return "暂无路况信息"
        
        info_parts = []
        
        # 拥堵程度
        congestion_level = traffic_conditions.get('congestion_level', '未知')
        if congestion_level != '未知':
            info_parts.append(f"拥堵程度: {congestion_level}")
        
        # 道路状况
        road_conditions = traffic_conditions.get('road_conditions', [])
        if road_conditions:
            info_parts.append(f"道路状况: {', '.join(road_conditions)}")
        
        # 实时信息
        real_time = traffic_conditions.get('real_time', False)
        if real_time:
            info_parts.append("实时路况: 是")
        
        return ', '.join(info_parts) if info_parts else "暂无路况信息"

    @staticmethod
    def format_data_for_llm(data: List[Dict[str, Any]], data_type: str) -> str:
        """格式化数据供LLM使用"""
        if not data:
            return "暂无数据"
        
        formatted_items = []
        for i, item in enumerate(data[:10]):  # 限制数量，避免prompt过长
            if data_type == 'flight':
                # 格式化时间显示
                departure_time = item.get('departure_time', 'N/A')
                arrival_time = item.get('arrival_time', 'N/A')
                if departure_time != 'N/A' and 'T' in departure_time:
                    departure_time = departure_time.split('T')[1][:5]  # 只显示时间部分 HH:MM
                if arrival_time != 'N/A' and 'T' in arrival_time:
                    arrival_time = arrival_time.split('T')[1][:5]  # 只显示时间部分 HH:MM
                
                # 格式化价格显示
                price_display = "N/A"
                if item.get('price_cny'):
                    price_display = f"{item.get('price_cny')}元"
                elif item.get('price'):
                    currency = item.get('currency', 'CNY')
                    price_display = f"{item.get('price')}{currency}"
                
                # 中转信息
                stops = item.get('stops', 0)
                stops_text = "直飞" if stops == 0 else f"{stops}次中转"
                
                formatted_items.append(f"""
  {i+1}. 航班号: {item.get('flight_number', 'N/A')}
     航空公司: {item.get('airline_name', item.get('airline', 'N/A'))}
     出发时间: {departure_time}
     到达时间: {arrival_time}
     飞行时长: {item.get('duration', 'N/A')}
     价格: {price_display}
     舱位等级: {item.get('cabin_class', 'N/A')}
     中转情况: {stops_text}
     出发机场: {item.get('origin', 'N/A')}
     到达机场: {item.get('destination', 'N/A')}
     行李额度: {item.get('baggage_allowance', 'N/A')}""")
            
            elif data_type == 'hotel':
                formatted_items.append(f"""
  {i+1}. 酒店名称: {item.get('name', 'N/A')}
     地址: {item.get('address', 'N/A')}
     每晚价格: {item.get('price_per_night', 'N/A')}元
     评分: {item.get('rating', 'N/A')}
     设施: {', '.join(item.get('amenities', []))}
     星级: {item.get('star_rating', 'N/A')}""")
            
            elif data_type == 'attraction':
                # 增强景点信息格式化，包含百度地图的详细信息
                formatted_items.append(f"""
  {i+1}. 景点名称: {item.get('name', 'N/A')}
     类型: {item.get('category', 'N/A')}
     描述: {item.get('description', 'N/A')}
     门票价格: {item.get('price', 'N/A')}元
     评分: {item.get('rating', 'N/A')}
     地址: {item.get('address', 'N/A')}
     开放时间: {item.get('opening_hours', 'N/A')}
     建议游览时间: {item.get('visit_duration', 'N/A')}
     特色标签: {', '.join(item.get('tags', []))}
     联系方式: {item.get('phone', 'N/A')}
     官方网站: {item.get('website', 'N/A')}
     交通便利性: {item.get('accessibility', 'N/A')}
     数据来源: {item.get('source', 'N/A')}""")
            
            elif data_type == 'restaurant':
                formatted_items.append(f"""
  {i+1}. 餐厅名称: {item.get('name', 'N/A')}
     菜系: {item.get('cuisine', 'N/A')}
     参考消费: {item.get('price_range', '价格未知')}
     评分: {item.get('rating', 'N/A')}
     地址: {item.get('address', 'N/A')}
     特色菜: {', '.join(item.get('specialties', []))}""")
            
            elif data_type == 'transportation':
                # 增强交通信息格式化，包含百度地图的详细信息
                formatted_items.append(f"""
  {i+1}. 交通方式: {item.get('type', 'N/A')}
     名称: {item.get('name', 'N/A')}
     描述: {item.get('description', 'N/A')}
     距离: {item.get('distance', 'N/A')}公里
     耗时: {item.get('duration', 'N/A')}分钟
     费用: {item.get('price', item.get('cost', 'N/A'))}元
     货币: {item.get('currency', 'CNY')}
     运营时间: {item.get('operating_hours', 'N/A')}
     发车频率: {item.get('frequency', 'N/A')}
     覆盖区域: {', '.join(item.get('coverage', []))}
     特色功能: {', '.join(item.get('features', []))}
     路线: {item.get('route', 'N/A')}
     数据来源: {item.get('source', 'N/A')}
     路况信息: {DataProcessor.format_traffic_info(item.get('traffic_conditions', {}))}""")
        
        return '\n'.join(formatted_items) if formatted_items else "暂无数据"
    
    @staticmethod
    def format_xiaohongshu_data_for_prompt(notes: List[Dict[str, Any]], destination: str) -> str:
        """格式化小红书数据为提示文本"""
        if not notes:
            return f"暂无{destination}的小红书用户分享内容"
        
        formatted_notes = []
        for note in notes[:5]:  # 限制数量
            title = note.get('title', '无标题')
            content = note.get('content', '')
            if len(content) > 200:
                content = content[:200] + "..."
            
            formatted_note = f"📍 {title}\n{content}"
            formatted_notes.append(formatted_note)
        
        return "\n\n".join(formatted_notes)
    
    @staticmethod
    def build_lookup_map(items: Optional[List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
        """构建查找映射表"""
        if not items:
            return {}
        
        lookup_map = {}
        for item in items:
            if isinstance(item, dict):
                name = item.get("name")
                if name:
                    lookup_map[name.lower().strip()] = item
        
        return lookup_map
    
    @staticmethod
    def find_lookup_match(lookup: Dict[str, Dict[str, Any]], target: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """在查找表中找到匹配项"""
        if not target or not lookup:
            return None
        
        target_name = target.get("name", "").lower().strip()
        if not target_name:
            return None
        
        # 精确匹配
        if target_name in lookup:
            return lookup[target_name]
        
        # 模糊匹配
        for key, value in lookup.items():
            if target_name in key or key in target_name:
                return value
        
        return None
    
    @staticmethod
    def combine_detail_dicts(
        source: Dict[str, Any],
        override: Dict[str, Any],
        list_fields: Set[str]
    ) -> Dict[str, Any]:
        """合并详细信息字典"""
        merged = copy.deepcopy(source) if source else {}
        if not override:
            return merged

        for key, value in override.items():
            if key in list_fields:
                merged[key] = DataProcessor.merge_list_values(merged.get(key), value)
            else:
                if value not in (None, "", [], {}):
                    merged[key] = value
        return merged
    
    @staticmethod
    def merge_list_values(existing: Any, extra: Any) -> List[Any]:
        """合并列表值，去重"""
        result = []
        seen = set()

        for collection in (existing, extra):
            for item in DataProcessor.ensure_list(collection):
                marker = DataProcessor.make_hashable(item)
                if marker in seen:
                    continue
                seen.add(marker)
                result.append(item)
        return result
    
    @staticmethod
    def ensure_list(value: Any) -> List[Any]:
        """确保返回列表类型"""
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        return [value]
    
    @staticmethod
    def make_hashable(value: Any) -> str:
        """将值转换为可哈希的字符串"""
        try:
            return json.dumps(value, sort_keys=True, ensure_ascii=False)
        except TypeError:
            return str(value)
    
    @staticmethod
    def normalize_resource_name(name: Optional[str]) -> str:
        """标准化资源名称用于去重"""
        if not name:
            return ""
        
        # 移除常见的品牌后缀、连锁标识等
        normalized = str(name).lower().strip()
        suffixes_to_remove = [
            "酒店", "宾馆", "旅馆", "度假村", "民宿",
            "餐厅", "饭店", "食府", "料理", "烤肉",
            "景区", "公园", "景点", "博物馆", "纪念馆",
            "店", "馆", "中心", "广场", "市场", "街"
        ]
        
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        
        # 移除特殊字符和数字
        import re
        normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', normalized)
        
        return normalized.strip()
    
    @staticmethod
    def clean_llm_response(response: str) -> str:
        """清理LLM响应，移除markdown标记等"""
        import re
        
        # 移除markdown代码块标记
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        cleaned = re.sub(r'```\s*', '', cleaned)  # 移除单独的```
        
        # 移除前后的空白字符
        cleaned = cleaned.strip()
        
        return cleaned
    
    @staticmethod
    def merge_total_cost(base: Dict[str, Any], segment: Dict[str, Any]) -> None:
        base_cost = base.get("total_cost")
        seg_cost = segment.get("total_cost")
        if not isinstance(seg_cost, dict):
            return
        if not isinstance(base_cost, dict):
            base_cost = {}
        for key, value in seg_cost.items():
            if isinstance(value, (int, float)):
                base_cost[key] = base_cost.get(key, 0) + value
            else:
                base_cost[key] = value
        base["total_cost"] = base_cost

    @staticmethod
    def build_segment_plan(
        plan: Any,
        segment: Dict[str, Any],
        preferences: Optional[Dict[str, Any]],
        segment_budget: Optional[float],
    ) -> Any:
        base_attrs = {
            "id": getattr(plan, "id", None),
            "title": getattr(plan, "title", None),
            "description": getattr(plan, "description", None),
            "departure": getattr(plan, "departure", None),
            "destination": getattr(plan, "destination", None),
            "transportation": getattr(plan, "transportation", None),
            "requirements": getattr(plan, "requirements", None),
            "num_people": getattr(plan, "num_people", None)
            or (preferences or {}).get("travelers")
            or getattr(plan, "travelers", None),
            "age_group": getattr(plan, "age_group", None),
            "travelers": getattr(plan, "travelers", None)
            or (preferences or {}).get("travelers"),
            "user_id": getattr(plan, "user_id", None),
            "status": getattr(plan, "status", None),
            "score": getattr(plan, "score", None),
            "is_public": getattr(plan, "is_public", None),
            "public_at": getattr(plan, "public_at", None),
        }
        base_attrs.update(
            {
                "duration_days": segment["days"],
                "start_date": segment["start_date"],
                "end_date": segment["end_date"],
                "budget": segment_budget,
            }
        )
        return SimpleNamespace(**base_attrs)

    @staticmethod
    def deduplicate_daily_attractions(plan_data: Dict[str, Any], min_attractions_per_day: int) -> None:
        """在同一方案内按天去重景点，避免同一景点出现在多个日期.

        智能去重策略：
        1. 如果景点总数充足，严格去重，确保每个景点只出现一次
        2. 如果景点总数不足，优先保留未使用的景点，但允许重复使用以填满每天的最少景点数
        
        仅依靠景点名称进行去重，名称为空或无法解析的条目原样保留。
        该函数会原地修改 plan_data 中的 daily_itineraries。
        """
        try:
            daily_itineraries = plan_data.get("daily_itineraries", []) or []
            if not daily_itineraries:
                return
            
            # 第一步：收集所有景点并统计唯一景点总数
            all_attractions: List[tuple] = []  # (attraction_obj, normalized_name)
            for day in daily_itineraries:
                attractions = day.get("attractions") or []
                if not isinstance(attractions, list):
                    continue
                for attr in attractions:
                    name = None
                    if isinstance(attr, dict):
                        name = attr.get("name")
                    elif isinstance(attr, str):
                        name = attr
                    normalized = DataProcessor.normalize_resource_name(name)
                    if normalized:  # 只统计有名字的景点
                        all_attractions.append((attr, normalized))
            
            # 统计唯一景点数量
            unique_attraction_names = set(norm for _, norm in all_attractions)
            total_unique = len(unique_attraction_names)
            total_days = len(daily_itineraries)
            
            # 如果唯一景点数足够，使用严格去重
            required_total = total_days * min_attractions_per_day
            if total_unique >= required_total:
                seen = set()
                for day in daily_itineraries:
                    attractions = day.get("attractions") or []
                    if not isinstance(attractions, list):
                        continue
                    unique = []
                    for attr in attractions:
                        name = None
                        if isinstance(attr, dict):
                            name = attr.get("name")
                        elif isinstance(attr, str):
                            name = attr
                        normalized = DataProcessor.normalize_resource_name(name)
                        # 没有名字的，或者未见过的，直接保留
                        if not normalized or normalized not in seen:
                            unique.append(attr)
                            if normalized:
                                seen.add(normalized)
                    day["attractions"] = unique
                logger.info(f"景点充足({total_unique}个唯一景点，需要{required_total}个)，已严格去重")
            else:
                # 景点不足，使用智能去重策略
                logger.info(f"景点不足({total_unique}个唯一景点，需要{required_total}个)，启用智能去重策略")
                
                # 记录每个景点的使用次数
                usage_count = {}
                # 建立景点对象到名称的映射
                attr_to_name = {}  # 使用id(attr)作为key
                
                # 第一遍：优先保留未使用的景点，统计使用次数
                seen = set()
                for day in daily_itineraries:
                    attractions = day.get("attractions") or []
                    if not isinstance(attractions, list):
                        continue
                    unique = []
                    for attr in attractions:
                        name = None
                        if isinstance(attr, dict):
                            name = attr.get("name")
                        elif isinstance(attr, str):
                            name = attr
                        normalized = DataProcessor.normalize_resource_name(name)
                        
                        if not normalized:
                            # 没有名字的，直接保留
                            unique.append(attr)
                        elif normalized not in seen:
                            # 未使用过的，优先保留
                            unique.append(attr)
                            seen.add(normalized)
                            usage_count[normalized] = 1
                            attr_to_name[id(attr)] = normalized
                        else:
                            # 已使用过的，记录使用次数
                            usage_count[normalized] = usage_count.get(normalized, 0) + 1
                            attr_to_name[id(attr)] = normalized
                    
                    day["attractions"] = unique
                
                # 第二遍：如果某天景点数不足，从已使用的景点中补充（优先选择使用次数最少的）
                for day in daily_itineraries:
                    attractions = day.get("attractions") or []
                    if not isinstance(attractions, list):
                        continue
                    
                    current_count = len([a for a in attractions if DataProcessor.normalize_resource_name(
                        a.get("name") if isinstance(a, dict) else (a if isinstance(a, str) else None)
                    )])
                    
                    # 如果当前景点数少于最少要求，需要补充
                    if current_count < min_attractions_per_day:
                        needed = min_attractions_per_day - current_count
                        
                        # 找出所有已使用的景点，按使用次数排序（使用次数少的优先）
                        available_attrs = [
                            (norm, count) for norm, count in usage_count.items()
                            if norm in seen  # 只考虑已使用过的
                        ]
                        available_attrs.sort(key=lambda x: x[1])  # 按使用次数升序
                        
                        # 从使用次数最少的景点中选择补充
                        for norm, _ in available_attrs[:needed]:
                            # 从原始数据中找到对应的景点对象
                            for orig_attr, orig_norm in all_attractions:
                                if orig_norm == norm:
                                    # 创建副本，避免引用问题
                                    if isinstance(orig_attr, dict):
                                        attr_copy = copy.deepcopy(orig_attr)
                                    else:
                                        attr_copy = orig_attr
                                    attractions.append(attr_copy)
                                    usage_count[norm] = usage_count.get(norm, 0) + 1
                                    break
                        
                        day["attractions"] = attractions
                
                logger.info(f"智能去重完成，部分景点允许重复使用以填满每天最少{min_attractions_per_day}个景点的要求")
                
        except Exception as e:  # 防御性，任何异常不影响主流程
            logger.warning(f"去重每日景点失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    @staticmethod
    def format_weather_info(weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化天气信息"""
        if not weather_data:
            return {
                "raw_data": {},
                "travel_recommendations": ["暂无天气数据，建议出行前查看最新天气预报"]
            }
        
        # 生成基于天气的旅游建议
        recommendations = []
        
        # 检查温度
        temp = weather_data.get('temperature')
        if temp:
            if isinstance(temp, (int, float)):
                if temp < 10:
                    recommendations.append("气温较低，建议穿着保暖衣物，携带外套")
                elif temp > 30:
                    recommendations.append("气温较高，建议穿着轻薄透气衣物，注意防晒")
                else:
                    recommendations.append("气温适宜，建议穿着舒适的休闲服装")
        
        # 检查天气状况
        weather_desc = weather_data.get('weather', '').lower()
        if '雨' in weather_desc or 'rain' in weather_desc:
            recommendations.append("有降雨，建议携带雨具，选择室内景点或有遮蔽的活动")
        elif '雪' in weather_desc or 'snow' in weather_desc:
            recommendations.append("有降雪，注意保暖防滑，选择适合雪天的活动")
        elif '晴' in weather_desc or 'sunny' in weather_desc:
            recommendations.append("天气晴朗，适合户外活动和观光，注意防晒")
        elif '云' in weather_desc or 'cloud' in weather_desc:
            recommendations.append("多云天气，适合各种户外活动，光线柔和适合拍照")
        
        # 检查湿度
        humidity = weather_data.get('humidity')
        if humidity and isinstance(humidity, (int, float)):
            if humidity > 80:
                recommendations.append("湿度较高，建议选择透气性好的衣物")
            elif humidity < 30:
                recommendations.append("湿度较低，注意补水保湿")
        
        # 检查风力
        wind_speed = weather_data.get('wind_speed')
        if wind_speed and isinstance(wind_speed, (int, float)):
            if wind_speed > 20:
                recommendations.append("风力较大，户外活动时注意安全，避免高空项目")
        
        # 如果没有生成任何建议，添加默认建议
        if not recommendations:
            recommendations.append("建议根据当地天气情况合理安排行程")
        
        return {
            "raw_data": weather_data,
            "travel_recommendations": recommendations
        }

    @staticmethod
    def infer_scope_from_metadata(plan: Any, destination: str) -> Optional[str]:
        """优先依据显式国家字段和关键词判断"""
        country = getattr(plan, "country", None)
        if country:
            normalized_country = str(country).strip().lower()
            if normalized_country in {"china", "cn", "prc", "中华人民共和国", "中国"}:
                return "domestic"
            return "international"

        text_lower = destination.lower()
        if any(keyword in destination for keyword in DOMESTIC_KEYWORDS_CN):
            return "domestic"
        if any(keyword in text_lower for keyword in DOMESTIC_KEYWORDS_EN):
            return "domestic"

        if destination and all(ord(ch) < 128 for ch in destination) and not any(
            keyword in text_lower for keyword in DOMESTIC_KEYWORDS_EN
        ):
            return "international"
        return None

    @staticmethod
    def normalize_preferences(preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """确保偏好字段存在并格式正确"""
        normalized = dict(preferences or {})

        def _set_default_list(key: str):
            value = normalized.get(key)
            if value is None:
                normalized[key] = []
            elif not isinstance(value, list):
                normalized[key] = [value]

        def _set_default_int(key: str, default: int = 1):
            value = normalized.get(key)
            if value is None:
                normalized[key] = default
                return
            try:
                normalized[key] = int(value)
            except (TypeError, ValueError):
                normalized[key] = default

        _set_default_int("travelers", 1)
        _set_default_list("ageGroups")
        _set_default_list("foodPreferences")
        _set_default_list("dietaryRestrictions")

        return normalized