"""
数据收集服务
负责从各种数据源收集旅行相关信息
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from loguru import logger
import httpx

from app.core.config import settings
from app.tools.mcp_client import MCPClient
from app.tools.baidu_maps_integration import (
    map_directions, 
    map_search_places, 
    map_geocode,
    map_weather
)
from app.services.web_scraper import WebScraper
from app.core.redis import get_cache, set_cache, cache_key


class DataCollector:
    """数据收集器"""
    
    def __init__(self):
        self.mcp_client = MCPClient()
        self.web_scraper = WebScraper()
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    async def collect_flight_data(
        self, 
        destination: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """收集航班数据"""
        try:
            cache_key_str = cache_key("flights", destination, start_date.date(), end_date.date())
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的航班数据: {destination}")
                return cached_data
            
            # 使用MCP工具收集航班信息
            flight_data = await self.mcp_client.get_flights(
                destination=destination,
                departure_date=start_date.date(),
                return_date=end_date.date()
            )
            
            # 如果MCP数据不足，使用爬虫补充
            if len(flight_data) < 5:
                scraped_flights = await self.web_scraper.scrape_flights(
                    destination, start_date, end_date
                )
                flight_data.extend(scraped_flights)
            
            # 缓存数据
            await set_cache(cache_key_str, flight_data, ttl=3600)  # 1小时缓存
            
            logger.info(f"收集到 {len(flight_data)} 条航班数据")
            return flight_data
            
        except Exception as e:
            logger.error(f"收集航班数据失败: {e}")
            return []
    
    async def collect_hotel_data(
        self, 
        destination: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """收集酒店数据"""
        try:
            cache_key_str = cache_key("hotels", destination, start_date.date(), end_date.date())
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的酒店数据: {destination}")
                return cached_data
            
            # 使用MCP工具收集酒店信息
            hotel_data = await self.mcp_client.get_hotels(
                destination=destination,
                check_in=start_date.date(),
                check_out=end_date.date()
            )
            
            # 如果MCP数据不足，使用爬虫补充
            if len(hotel_data) < 10:
                scraped_hotels = await self.web_scraper.scrape_hotels(
                    destination, start_date, end_date
                )
                hotel_data.extend(scraped_hotels)
            
            # 缓存数据
            await set_cache(cache_key_str, hotel_data, ttl=7200)  # 2小时缓存
            
            logger.info(f"收集到 {len(hotel_data)} 条酒店数据")
            return hotel_data
            
        except Exception as e:
            logger.error(f"收集酒店数据失败: {e}")
            return []
    
    async def collect_attraction_data(self, destination: str) -> List[Dict[str, Any]]:
        """收集景点数据"""
        try:
            cache_key_str = cache_key("attractions", destination)
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的景点数据: {destination}")
                return cached_data
            
            attraction_data = []
            
            # 优先使用内置百度地图功能
            try:
                logger.info(f"使用内置百度地图功能收集景点数据: {destination}")
                
                # 搜索景点
                places_result = await map_search_places(
                    query="景点",
                    region=destination,
                    tag="风景名胜",
                    is_china="true"
                )
                
                if places_result.get("status") == 0:
                    places = places_result.get("result", {}).get("items", [])
                    for place in places[:10]:  # 取前10个景点
                        attraction_item = {
                            "name": place.get("name", "景点"),
                            "category": "风景名胜",
                            "description": place.get("detail_info", {}).get("tag", "热门景点"),
                            "price": "免费" if place.get("detail_info", {}).get("price") == "0" else "收费",
                            "rating": place.get("detail_info", {}).get("overall_rating", "4.5"),
                            "address": place.get("address", ""),
                            "coordinates": {
                                "lat": place.get("location", {}).get("lat"),
                                "lng": place.get("location", {}).get("lng")
                            },
                            "opening_hours": place.get("detail_info", {}).get("open_time", "全天开放"),
                            "source": "百度地图API"
                        }
                        attraction_data.append(attraction_item)
                
                # 搜索博物馆
                museum_result = await map_search_places(
                    query="博物馆",
                    region=destination,
                    tag="科教文化服务",
                    is_china="true"
                )
                
                if museum_result.get("status") == 0:
                    museums = museum_result.get("result", {}).get("items", [])
                    for museum in museums[:5]:  # 取前5个博物馆
                        attraction_item = {
                            "name": museum.get("name", "博物馆"),
                            "category": "博物馆",
                            "description": museum.get("detail_info", {}).get("tag", "文化景点"),
                            "price": "免费" if museum.get("detail_info", {}).get("price") == "0" else "收费",
                            "rating": museum.get("detail_info", {}).get("overall_rating", "4.3"),
                            "address": museum.get("address", ""),
                            "coordinates": {
                                "lat": museum.get("location", {}).get("lat"),
                                "lng": museum.get("location", {}).get("lng")
                            },
                            "opening_hours": museum.get("detail_info", {}).get("open_time", "09:00-17:00"),
                            "source": "百度地图API"
                        }
                        attraction_data.append(attraction_item)
                
                logger.info(f"从百度地图API获取到 {len(attraction_data)} 条景点数据")
                
            except Exception as e:
                logger.warning(f"百度地图景点API调用失败: {e}")
            
            # 如果百度地图数据不足，使用MCP工具补充
            if len(attraction_data) < 10:
                try:
                    mcp_data = await self.mcp_client.get_attractions(destination)
                    attraction_data.extend(mcp_data)
                    logger.info(f"从MCP服务补充 {len(mcp_data)} 条景点数据")
                except Exception as e:
                    logger.warning(f"MCP景点服务调用失败: {e}")
            
            # 如果数据仍然不足，使用爬虫补充
            if len(attraction_data) < 20:
                try:
                    scraped_attractions = await self.web_scraper.scrape_attractions(destination)
                    attraction_data.extend(scraped_attractions)
                    logger.info(f"从爬虫补充 {len(scraped_attractions)} 条景点数据")
                except Exception as e:
                    logger.warning(f"爬虫景点数据收集失败: {e}")
            
            # 缓存数据
            await set_cache(cache_key_str, attraction_data, ttl=86400)  # 24小时缓存
            
            logger.info(f"收集到 {len(attraction_data)} 条景点数据")
            return attraction_data
            
        except Exception as e:
            logger.error(f"收集景点数据失败: {e}")
            return []
    
    async def collect_weather_data(
        self, 
        destination: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """收集天气数据"""
        try:
            cache_key_str = cache_key("weather", destination, start_date.date(), end_date.date())
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的天气数据: {destination}")
                return cached_data
            
            weather_data = {}
            
            # 优先使用内置百度地图功能
            try:
                logger.info(f"使用内置百度地图功能收集天气数据: {destination}")
                
                # 先获取目的地的坐标
                geocode_result = await map_geocode(destination, is_china="true")
                if geocode_result.get("status") == 0:
                    location = geocode_result.get("result", {}).get("location", {})
                    lat = location.get("lat")
                    lng = location.get("lng")
                    
                    if lat and lng:
                        # 使用坐标查询天气
                        weather_result = await map_weather(
                            location=f"{lng},{lat}",  # 百度地图API需要经度在前
                            is_china="true"
                        )
                        
                        if weather_result.get("status") == 0:
                            weather_data = {
                                "destination": destination,
                                "location": {"lat": lat, "lng": lng},
                                "current_weather": weather_result.get("result", {}),
                                "source": "百度地图API",
                                "collected_at": datetime.now().isoformat()
                            }
                            logger.info(f"从百度地图API获取到天气数据: {destination}")
                
            except Exception as e:
                logger.warning(f"百度地图天气API调用失败: {e}")
            
            # 如果百度地图数据不足，使用MCP工具补充
            if not weather_data:
                try:
                    weather_data = await self.mcp_client.get_weather(
                        destination=destination,
                        start_date=start_date.date(),
                        end_date=end_date.date()
                    )
                    logger.info(f"从MCP服务获取到天气数据: {destination}")
                except Exception as e:
                    logger.warning(f"MCP天气服务调用失败: {e}")
            
            # 如果仍然没有数据，使用模拟数据
            if not weather_data:
                weather_data = {
                    "destination": destination,
                    "current_weather": {
                        "temperature": "22°C",
                        "condition": "晴",
                        "humidity": "65%",
                        "wind": "微风"
                    },
                    "forecast": [
                        {"date": start_date.date().isoformat(), "high": "25°C", "low": "18°C", "condition": "晴"},
                        {"date": end_date.date().isoformat(), "high": "23°C", "low": "16°C", "condition": "多云"}
                    ],
                    "source": "模拟数据",
                    "collected_at": datetime.now().isoformat()
                }
                logger.info(f"使用模拟天气数据: {destination}")
            
            # 缓存数据
            await set_cache(cache_key_str, weather_data, ttl=1800)  # 30分钟缓存
            
            logger.info(f"收集到天气数据: {destination}")
            return weather_data
            
        except Exception as e:
            logger.error(f"收集天气数据失败: {e}")
            return {}
    
    async def collect_restaurant_data(self, destination: str) -> List[Dict[str, Any]]:
        """收集餐厅数据"""
        try:
            cache_key_str = cache_key("restaurants", destination)
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的餐厅数据: {destination}")
                return cached_data
            
            restaurant_data = []
            
            # 优先使用内置百度地图功能
            try:
                logger.info(f"使用内置百度地图功能收集餐厅数据: {destination}")
                
                # 搜索餐厅
                restaurants_result = await map_search_places(
                    query="餐厅",
                    region=destination,
                    tag="美食",
                    is_china="true"
                )
                
                if restaurants_result.get("status") == 0:
                    restaurants = restaurants_result.get("result", {}).get("items", [])
                    for restaurant in restaurants[:10]:  # 取前10个餐厅
                        restaurant_item = {
                            "name": restaurant.get("name", "餐厅"),
                            "cuisine": restaurant.get("detail_info", {}).get("tag", "中餐"),
                            "rating": restaurant.get("detail_info", {}).get("overall_rating", "4.2"),
                            "price_range": "$$" if restaurant.get("detail_info", {}).get("price") else "$$$",
                            "address": restaurant.get("address", ""),
                            "coordinates": {
                                "lat": restaurant.get("location", {}).get("lat"),
                                "lng": restaurant.get("location", {}).get("lng")
                            },
                            "opening_hours": restaurant.get("detail_info", {}).get("open_time", "10:00-22:00"),
                            "specialties": restaurant.get("detail_info", {}).get("tag", "").split(",") if restaurant.get("detail_info", {}).get("tag") else ["特色菜"],
                            "source": "百度地图API"
                        }
                        restaurant_data.append(restaurant_item)
                
                # 搜索特色小吃
                snack_result = await map_search_places(
                    query="小吃",
                    region=destination,
                    tag="美食",
                    is_china="true"
                )
                
                if snack_result.get("status") == 0:
                    snacks = snack_result.get("result", {}).get("items", [])
                    for snack in snacks[:5]:  # 取前5个小吃店
                        restaurant_item = {
                            "name": snack.get("name", "小吃店"),
                            "cuisine": "小吃",
                            "rating": snack.get("detail_info", {}).get("overall_rating", "4.0"),
                            "price_range": "$",
                            "address": snack.get("address", ""),
                            "coordinates": {
                                "lat": snack.get("location", {}).get("lat"),
                                "lng": snack.get("location", {}).get("lng")
                            },
                            "opening_hours": snack.get("detail_info", {}).get("open_time", "08:00-20:00"),
                            "specialties": ["特色小吃"],
                            "source": "百度地图API"
                        }
                        restaurant_data.append(restaurant_item)
                
                logger.info(f"从百度地图API获取到 {len(restaurant_data)} 条餐厅数据")
                
            except Exception as e:
                logger.warning(f"百度地图餐厅API调用失败: {e}")
            
            # 如果百度地图数据不足，使用MCP工具补充
            if len(restaurant_data) < 10:
                try:
                    mcp_data = await self.mcp_client.get_restaurants(destination)
                    restaurant_data.extend(mcp_data)
                    logger.info(f"从MCP服务补充 {len(mcp_data)} 条餐厅数据")
                except Exception as e:
                    logger.warning(f"MCP餐厅服务调用失败: {e}")
            
            # 如果数据仍然不足，使用爬虫补充
            if len(restaurant_data) < 15:
                try:
                    scraped_restaurants = await self.web_scraper.scrape_restaurants(destination)
                    restaurant_data.extend(scraped_restaurants)
                    logger.info(f"从爬虫补充 {len(scraped_restaurants)} 条餐厅数据")
                except Exception as e:
                    logger.warning(f"爬虫餐厅数据收集失败: {e}")
            
            # 缓存数据
            await set_cache(cache_key_str, restaurant_data, ttl=43200)  # 12小时缓存
            
            logger.info(f"收集到 {len(restaurant_data)} 条餐厅数据")
            return restaurant_data
            
        except Exception as e:
            logger.error(f"收集餐厅数据失败: {e}")
            return []
    
    async def collect_transportation_data(self, destination: str) -> List[Dict[str, Any]]:
        """收集交通数据"""
        try:
            cache_key_str = cache_key("transportation", destination)
            
            # 检查缓存
            cached_data = await get_cache(cache_key_str)
            if cached_data:
                logger.info(f"使用缓存的交通数据: {destination}")
                return cached_data
            
            transport_data = []
            
            # 优先使用内置百度地图功能
            try:
                logger.info(f"使用内置百度地图功能收集交通数据: {destination}")
                
                # 获取路线规划数据
                directions_result = await map_directions(
                    origin="上海市中心",
                    destination=destination,
                    model="transit",
                    is_china="true"
                )
                
                if directions_result.get("status") == 0:
                    routes = directions_result.get("result", {}).get("routes", [])
                    for i, route in enumerate(routes[:3]):  # 取前3条路线
                        transport_item = {
                            "type": "公交",
                            "description": f"从上海市中心到{destination}的公交路线",
                            "duration": route.get("duration", 0) // 60,  # 转换为分钟
                            "distance": route.get("distance", 0) // 1000,  # 转换为公里
                            "cost": "2-8元",
                            "route": f"路线{i+1}",
                            "operating_hours": "06:00-23:00",
                            "source": "百度地图API"
                        }
                        transport_data.append(transport_item)
                
                # 获取地点搜索数据（交通枢纽）
                places_result = await map_search_places(
                    query="地铁站",
                    region=destination,
                    tag="交通设施服务",
                    is_china="true"
                )
                
                if places_result.get("status") == 0:
                    places = places_result.get("result", {}).get("items", [])
                    for place in places[:2]:  # 取前2个地铁站
                        transport_item = {
                            "type": "地铁",
                            "description": f"{place.get('name', '地铁站')} - {place.get('address', '')}",
                            "duration": 30,  # 估算时间
                            "distance": 5,   # 估算距离
                            "cost": "3-10元",
                            "route": place.get('name', '地铁站'),
                            "operating_hours": "05:30-23:30",
                            "source": "百度地图API"
                        }
                        transport_data.append(transport_item)
                
                logger.info(f"从百度地图API获取到 {len(transport_data)} 条交通数据")
                
            except Exception as e:
                logger.warning(f"百度地图API调用失败: {e}")
            
            # 如果百度地图数据不足，使用MCP工具补充
            if len(transport_data) < 5:
                try:
                    mcp_data = await self.mcp_client.get_transportation(destination)
                    transport_data.extend(mcp_data)
                    logger.info(f"从MCP服务补充 {len(mcp_data)} 条交通数据")
                except Exception as e:
                    logger.warning(f"MCP服务调用失败: {e}")
            
            # 如果数据仍然不足，使用爬虫补充
            if len(transport_data) < 10:
                try:
                    scraped_transport = await self.web_scraper.scrape_transportation(destination)
                    transport_data.extend(scraped_transport)
                    logger.info(f"从爬虫补充 {len(scraped_transport)} 条交通数据")
                except Exception as e:
                    logger.warning(f"爬虫数据收集失败: {e}")
            
            # 缓存数据
            await set_cache(cache_key_str, transport_data, ttl=86400)  # 24小时缓存
            
            logger.info(f"收集到 {len(transport_data)} 条交通数据")
            return transport_data
            
        except Exception as e:
            logger.error(f"收集交通数据失败: {e}")
            return []
    
    async def collect_all_data(
        self, 
        destination: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """收集所有类型的数据"""
        logger.info(f"开始收集 {destination} 的所有数据")
        
        # 并行收集所有数据
        tasks = [
            self.collect_flight_data(destination, start_date, end_date),
            self.collect_hotel_data(destination, start_date, end_date),
            self.collect_attraction_data(destination),
            self.collect_weather_data(destination, start_date, end_date),
            self.collect_restaurant_data(destination),
            self.collect_transportation_data(destination)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "flights": results[0] if not isinstance(results[0], Exception) else [],
            "hotels": results[1] if not isinstance(results[1], Exception) else [],
            "attractions": results[2] if not isinstance(results[2], Exception) else [],
            "weather": results[3] if not isinstance(results[3], Exception) else {},
            "restaurants": results[4] if not isinstance(results[4], Exception) else [],
            "transportation": results[5] if not isinstance(results[5], Exception) else []
        }
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.http_client.aclose()
