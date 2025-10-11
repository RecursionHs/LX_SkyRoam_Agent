"""
MCP (Model Control Protocol) 客户端
用于调用各种第三方API和工具
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from loguru import logger
import httpx
import json

from app.core.config import settings


class MCPClient:
    """MCP客户端"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=settings.MCP_TIMEOUT)
        self.base_url = "https://api.example.com"  # 示例API地址
    
    async def get_flights(
        self, 
        destination: str, 
        departure_date: date, 
        return_date: date,
        origin: str = "北京"
    ) -> List[Dict[str, Any]]:
        """获取航班信息"""
        try:
            # 使用Amadeus API获取真实航班数据
            if not settings.FLIGHT_API_KEY:
                logger.warning("航班API密钥未配置，使用模拟数据")
                return self._get_mock_flights(destination, departure_date, return_date, origin)
            
            # 调用Amadeus API
            flights = await self._get_amadeus_flights(origin, destination, departure_date, return_date)
            
            if not flights:
                logger.warning("Amadeus API未返回数据，使用模拟数据")
                return self._get_mock_flights(destination, departure_date, return_date, origin)
            
            logger.info(f"从Amadeus API获取到 {len(flights)} 条航班数据")
            return flights
            
        except Exception as e:
            logger.error(f"获取航班数据失败: {e}")
            return self._get_mock_flights(destination, departure_date, return_date, origin)
    
    async def _get_amadeus_flights(
        self, 
        origin: str, 
        destination: str, 
        departure_date: date, 
        return_date: date
    ) -> List[Dict[str, Any]]:
        """调用Amadeus API获取航班数据"""
        try:
            # Amadeus API端点
            url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
            
            params = {
                "originLocationCode": self._get_city_code(origin),
                "destinationLocationCode": self._get_city_code(destination),
                "departureDate": departure_date.strftime("%Y-%m-%d"),
                "returnDate": return_date.strftime("%Y-%m-%d"),
                "adults": 1,
                "max": 10
            }
            
            headers = {
                "Authorization": f"Bearer {settings.FLIGHT_API_KEY}",
                "Content-Type": "application/json"
            }
            
            async with self.http_client.get(url, params=params, headers=headers) as response:
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_amadeus_flights(data)
                else:
                    logger.error(f"Amadeus API错误: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Amadeus API调用失败: {e}")
            return []
    
    def _parse_amadeus_flights(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析Amadeus API返回的航班数据"""
        flights = []
        
        try:
            for offer in data.get("data", []):
                for itinerary in offer.get("itineraries", []):
                    for segment in itinerary.get("segments", []):
                        flight = {
                            "id": f"flight_{len(flights) + 1}",
                            "airline": segment.get("carrierCode", "Unknown"),
                            "flight_number": segment.get("number", "N/A"),
                            "departure_time": segment.get("departure", {}).get("at", "N/A"),
                            "arrival_time": segment.get("arrival", {}).get("at", "N/A"),
                            "duration": segment.get("duration", "N/A"),
                            "price": float(offer.get("price", {}).get("total", 0)),
                            "currency": offer.get("price", {}).get("currency", "CNY"),
                            "aircraft": segment.get("aircraft", {}).get("code", "N/A"),
                            "stops": 0,
                            "origin": segment.get("departure", {}).get("iataCode", "N/A"),
                            "destination": segment.get("arrival", {}).get("iataCode", "N/A"),
                            "date": segment.get("departure", {}).get("at", "N/A"),
                            "rating": 4.0
                        }
                        flights.append(flight)
                        
            return flights
            
        except Exception as e:
            logger.error(f"解析Amadeus航班数据失败: {e}")
            return []
    
    def _get_city_code(self, city: str) -> str:
        """获取城市代码"""
        city_codes = {
            "北京": "PEK",
            "上海": "PVG", 
            "广州": "CAN",
            "深圳": "SZX",
            "成都": "CTU",
            "杭州": "HGH",
            "南京": "NKG",
            "武汉": "WUH",
            "西安": "XIY",
            "重庆": "CKG",
            "厦门": "XMN",
            "青岛": "TAO",
            "大连": "DLC",
            "昆明": "KMG",
            "长沙": "CSX",
            "沈阳": "SHE",
            "哈尔滨": "HRB",
            "长春": "CGQ",
            "石家庄": "SJW",
            "太原": "TYN",
            "呼和浩特": "HET",
            "兰州": "LHW",
            "西宁": "XNN",
            "银川": "INC",
            "乌鲁木齐": "URC",
            "拉萨": "LXA",
            "香港": "HKG",
            "台北": "TPE",
            "澳门": "MFM"
        }
        return city_codes.get(city, "PEK")  # 默认返回北京
    
    def _get_mock_flights(
        self, 
        destination: str, 
        departure_date: date, 
        return_date: date,
        origin: str = "北京"
    ) -> List[Dict[str, Any]]:
        """获取模拟航班数据"""
        flights = [
            {
                "id": "flight_1",
                "airline": "中国国际航空",
                "flight_number": "CA1234",
                "departure_time": "08:00",
                "arrival_time": "11:30",
                "duration": "3h30m",
                "price": 1200,
                "currency": "CNY",
                "aircraft": "Boeing 737",
                "stops": 0,
                "origin": origin,
                "destination": destination,
                "date": departure_date.isoformat(),
                "rating": 4.0
            },
            {
                "id": "flight_2", 
                "airline": "东方航空",
                "flight_number": "MU5678",
                "departure_time": "14:20",
                "arrival_time": "17:45",
                "duration": "3h25m",
                "price": 1350,
                "currency": "CNY",
                "aircraft": "Airbus A320",
                "stops": 0,
                "origin": origin,
                "destination": destination,
                "date": departure_date.isoformat(),
                "rating": 4.2
            }
        ]
        
        logger.info(f"获取到 {len(flights)} 条模拟航班信息")
        return flights
    
    async def get_hotels(
        self, 
        destination: str, 
        check_in: date, 
        check_out: date
    ) -> List[Dict[str, Any]]:
        """获取酒店信息"""
        try:
            # 使用Booking.com API获取真实酒店数据
            if not settings.HOTEL_API_KEY:
                logger.warning("酒店API密钥未配置，使用模拟数据")
                return self._get_mock_hotels(destination, check_in, check_out)
            
            # 调用Booking.com API
            hotels = await self._get_booking_hotels(destination, check_in, check_out)
            
            if not hotels:
                logger.warning("Booking.com API未返回数据，使用模拟数据")
                return self._get_mock_hotels(destination, check_in, check_out)
            
            logger.info(f"从Booking.com API获取到 {len(hotels)} 条酒店数据")
            return hotels
            
        except Exception as e:
            logger.error(f"获取酒店数据失败: {e}")
            return self._get_mock_hotels(destination, check_in, check_out)
    
    async def _get_booking_hotels(
        self, 
        destination: str, 
        check_in: date, 
        check_out: date
    ) -> List[Dict[str, Any]]:
        """调用Booking.com API获取酒店数据"""
        try:
            # Booking.com API端点
            url = "https://distribution-xml.booking.com/2.0/json/hotelAvailability"
            
            params = {
                "city": destination,
                "checkin": check_in.strftime("%Y-%m-%d"),
                "checkout": check_out.strftime("%Y-%m-%d"),
                "rooms": 1,
                "adults": 2,
                "limit": 10
            }
            
            headers = {
                "Authorization": f"Bearer {settings.HOTEL_API_KEY}",
                "Content-Type": "application/json"
            }
            
            async with self.http_client.get(url, params=params, headers=headers) as response:
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_booking_hotels(data)
                else:
                    logger.error(f"Booking.com API错误: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Booking.com API调用失败: {e}")
            return []
    
    def _parse_booking_hotels(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析Booking.com API返回的酒店数据"""
        hotels = []
        
        try:
            for hotel in data.get("result", []):
                hotel_data = {
                    "id": f"hotel_{len(hotels) + 1}",
                    "name": hotel.get("name", "Unknown Hotel"),
                    "address": hotel.get("address", "N/A"),
                    "rating": float(hotel.get("rating", 0)),
                    "price_per_night": float(hotel.get("price", 0)),
                    "currency": hotel.get("currency", "CNY"),
                    "amenities": hotel.get("amenities", []),
                    "room_types": hotel.get("room_types", []),
                    "check_in": hotel.get("check_in", ""),
                    "check_out": hotel.get("check_out", ""),
                    "images": hotel.get("images", []),
                    "coordinates": hotel.get("coordinates", {}),
                    "star_rating": hotel.get("star_rating", 0)
                }
                hotels.append(hotel_data)
                
            return hotels
            
        except Exception as e:
            logger.error(f"解析Booking.com酒店数据失败: {e}")
            return []
    
    def _get_mock_hotels(
        self, 
        destination: str, 
        check_in: date, 
        check_out: date
    ) -> List[Dict[str, Any]]:
        """获取模拟酒店数据"""
        hotels = [
            {
                "id": "hotel_1",
                "name": "希尔顿酒店",
                "address": f"{destination}市中心",
                "rating": 4.5,
                "price_per_night": 800,
                "currency": "CNY",
                "amenities": ["WiFi", "健身房", "游泳池", "餐厅"],
                "room_types": ["标准间", "豪华间", "套房"],
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "images": ["https://example.com/hotel1.jpg"],
                "coordinates": {"lat": 39.9042, "lng": 116.4074},
                "star_rating": 5
            },
            {
                "id": "hotel_2",
                "name": "万豪酒店",
                "address": f"{destination}商业区",
                "rating": 4.8,
                "price_per_night": 1200,
                "currency": "CNY",
                "amenities": ["WiFi", "健身房", "水疗中心", "商务中心"],
                "room_types": ["豪华间", "行政间", "总统套房"],
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "images": ["https://example.com/hotel2.jpg"],
                "coordinates": {"lat": 39.9042, "lng": 116.4074},
                "star_rating": 5
            }
        ]
        
        logger.info(f"获取到 {len(hotels)} 条模拟酒店信息")
        return hotels
    
    async def get_attractions(self, destination: str) -> List[Dict[str, Any]]:
        """获取景点信息"""
        try:
            # 使用Google Places API获取真实景点数据
            if not settings.MAP_API_KEY:
                logger.warning("地图API密钥未配置，使用模拟数据")
                return self._get_mock_attractions(destination)
            
            # 调用Google Places API
            attractions = await self._get_google_places(destination)
            
            if not attractions:
                logger.warning("Google Places API未返回数据，使用模拟数据")
                return self._get_mock_attractions(destination)
            
            logger.info(f"从Google Places API获取到 {len(attractions)} 条景点数据")
            return attractions
            
        except Exception as e:
            logger.error(f"获取景点数据失败: {e}")
            return self._get_mock_attractions(destination)
    
    async def _get_google_places(self, destination: str) -> List[Dict[str, Any]]:
        """调用Google Places API获取景点数据"""
        try:
            # Google Places API端点
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            
            params = {
                "query": f"{destination} tourist attractions",
                "key": settings.MAP_API_KEY,
                "language": "zh-CN"
            }
            
            async with self.http_client.get(url, params=params) as response:
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_google_places(data)
                else:
                    logger.error(f"Google Places API错误: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Google Places API调用失败: {e}")
            return []
    
    def _parse_google_places(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析Google Places API返回的景点数据"""
        attractions = []
        
        try:
            for place in data.get("results", []):
                attraction = {
                    "id": f"attr_{len(attractions) + 1}",
                    "name": place.get("name", "Unknown Place"),
                    "category": place.get("types", ["attraction"])[0],
                    "description": place.get("formatted_address", "N/A"),
                    "rating": float(place.get("rating", 0)),
                    "price": 0,  # Google Places不提供价格信息
                    "currency": "CNY",
                    "opening_hours": "N/A",
                    "address": place.get("formatted_address", "N/A"),
                    "coordinates": place.get("geometry", {}).get("location", {}),
                    "images": [],
                    "features": place.get("types", []),
                    "visit_duration": "1-2小时"
                }
                attractions.append(attraction)
                
            return attractions
            
        except Exception as e:
            logger.error(f"解析Google Places景点数据失败: {e}")
            return []
    
    def _get_mock_attractions(self, destination: str) -> List[Dict[str, Any]]:
        """获取模拟景点数据"""
        attractions = [
            {
                "id": "attr_1",
                "name": f"{destination}著名景点1",
                "category": "历史建筑",
                "description": f"{destination}的标志性建筑",
                "rating": 4.7,
                "price": 0,
                "currency": "CNY",
                "opening_hours": "全天开放",
                "address": f"{destination}市中心",
                "coordinates": {"lat": 39.9042, "lng": 116.4074},
                "images": ["https://example.com/attraction1.jpg"],
                "features": ["免费参观", "历史意义", "拍照圣地"],
                "visit_duration": "2-3小时"
            },
            {
                "id": "attr_2",
                "name": f"{destination}著名景点2",
                "category": "博物馆",
                "description": f"{destination}的文化地标",
                "rating": 4.8,
                "price": 60,
                "currency": "CNY",
                "opening_hours": "08:30-17:00",
                "address": f"{destination}文化区",
                "coordinates": {"lat": 39.9163, "lng": 116.3972},
                "images": ["https://example.com/attraction2.jpg"],
                "features": ["世界文化遗产", "古建筑", "文物展览"],
                "visit_duration": "3-4小时"
            }
        ]
        
        logger.info(f"获取到 {len(attractions)} 条模拟景点信息")
        return attractions
    
    async def get_weather(
        self, 
        destination: str, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """获取天气信息"""
        try:
            if not settings.WEATHER_API_KEY:
                logger.warning("天气API密钥未配置")
                return {}
            
            # 模拟API调用
            weather_data = {
                "location": destination,
                "forecast": [
                    {
                        "date": start_date.isoformat(),
                        "temperature": {"high": 25, "low": 15},
                        "condition": "晴天",
                        "humidity": 60,
                        "wind_speed": 10,
                        "precipitation": 0
                    },
                    {
                        "date": end_date.isoformat(),
                        "temperature": {"high": 22, "low": 12},
                        "condition": "多云",
                        "humidity": 70,
                        "wind_speed": 8,
                        "precipitation": 0
                    }
                ],
                "recommendations": [
                    "建议携带轻便外套",
                    "适合户外活动",
                    "注意防晒"
                ]
            }
            
            logger.info(f"获取到天气信息: {destination}")
            return weather_data
            
        except Exception as e:
            logger.error(f"获取天气信息失败: {e}")
            return {}
    
    async def get_restaurants(self, destination: str) -> List[Dict[str, Any]]:
        """获取餐厅信息"""
        try:
            # 模拟API调用
            restaurants = [
                {
                    "id": "rest_1",
                    "name": "全聚德烤鸭店",
                    "cuisine_type": "北京菜",
                    "rating": 4.5,
                    "price_range": "$$$",
                    "address": f"{destination}王府井大街",
                    "coordinates": {"lat": 39.9042, "lng": 116.4074},
                    "opening_hours": "11:00-22:00",
                    "specialties": ["北京烤鸭", "炸酱面", "豆汁"],
                    "images": ["https://example.com/restaurant1.jpg"],
                    "features": ["传统老字号", "适合聚餐", "有包间"]
                },
                {
                    "id": "rest_2",
                    "name": "海底捞火锅",
                    "cuisine_type": "火锅",
                    "rating": 4.7,
                    "price_range": "$$",
                    "address": f"{destination}三里屯",
                    "coordinates": {"lat": 39.9042, "lng": 116.4074},
                    "opening_hours": "10:00-24:00",
                    "specialties": ["麻辣火锅", "番茄锅", "服务好"],
                    "images": ["https://example.com/restaurant2.jpg"],
                    "features": ["24小时营业", "优质服务", "适合家庭"]
                }
            ]
            
            logger.info(f"获取到 {len(restaurants)} 条餐厅信息")
            return restaurants
            
        except Exception as e:
            logger.error(f"获取餐厅信息失败: {e}")
            return []
    
    async def get_transportation(self, destination: str) -> List[Dict[str, Any]]:
        """获取交通信息"""
        try:
            # 使用MCP服务获取真实交通数据
            transportation = await self._get_mcp_transportation(destination)
            
            if not transportation:
                logger.warning("MCP服务未返回数据，使用模拟数据")
                return self._get_mock_transportation(destination)
            
            logger.info(f"从MCP服务获取到 {len(transportation)} 条交通数据")
            return transportation
            
        except Exception as e:
            logger.error(f"获取交通数据失败: {e}")
            return self._get_mock_transportation(destination)
    
    async def _get_mcp_transportation(self, destination: str) -> List[Dict[str, Any]]:
        """通过MCP服务获取交通数据"""
        try:
            # MCP服务端点 - 从配置中获取
            mcp_endpoints = [
                settings.BAIDU_MCP_ENDPOINT,  # 百度地图MCP服务
                settings.AMAP_MCP_ENDPOINT   # 高德地图MCP服务
            ]
            
            transportation = []
            
            # 尝试百度地图MCP服务
            try:
                baidu_data = await self._call_mcp_service(
                    mcp_endpoints[0], 
                    "map_directions",
                    {
                        "origin": "上海市中心",
                        "destination": destination,
                        "model": "transit",
                        "is_china": "true"
                    }
                )
                if baidu_data:
                    transportation.extend(self._parse_mcp_transportation(baidu_data, "百度地图"))
            except Exception as e:
                logger.warning(f"百度地图MCP服务调用失败: {e}")
            
            # 尝试高德地图MCP服务
            try:
                amap_data = await self._call_mcp_service(
                    mcp_endpoints[1],
                    "route_planning",
                    {
                        "origin": "上海市中心",
                        "destination": destination,
                        "strategy": "0"  # 推荐路线
                    }
                )
                if amap_data:
                    transportation.extend(self._parse_mcp_transportation(amap_data, "高德地图"))
            except Exception as e:
                logger.warning(f"高德地图MCP服务调用失败: {e}")
            
            return transportation
            
        except Exception as e:
            logger.error(f"MCP服务调用失败: {e}")
            return []
    
    async def _call_mcp_service(self, endpoint: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用MCP服务"""
        try:
            # 直接调用内置的百度地图MCP功能
            if "localhost" in endpoint:
                return await self._call_builtin_baidu_maps(method, params)
            else:
                # 其他服务使用JSON-RPC协议
                return await self._call_json_rpc_mcp(endpoint, method, params)
                    
        except Exception as e:
            logger.error(f"MCP服务调用异常: {e}")
            return None
    
    async def _call_baidu_mcp_api(self, endpoint: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用百度地图MCP API"""
        try:
            # 百度地图MCP服务使用HTTP API方式
            url = endpoint
            
            # 根据方法构建请求参数
            if method == "map_directions":
                api_params = {
                    "origin": params.get("origin", ""),
                    "destination": params.get("destination", ""),
                    "mode": params.get("mode", "transit"),
                    "output": "json"
                }
            else:
                api_params = params
            
            # 使用POST方法调用百度地图API
            response = await self.http_client.post(url, json=api_params)
            if response.status_code == 200:
                result = response.json()
                # 百度地图API返回格式
                if result.get("status") == 0:
                    return result
                else:
                    logger.error(f"百度地图API错误: {result.get('message', 'Unknown error')}")
                    return None
            else:
                logger.error(f"百度地图API HTTP错误: {response.status_code}")
                return None
                    
        except Exception as e:
            logger.error(f"百度地图MCP API调用异常: {e}")
            return None
    
    async def _call_builtin_baidu_maps(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """直接调用内置的百度地图功能"""
        try:
            # 导入百度地图集成模块
            from app.tools.baidu_maps_integration import call_baidu_maps_tool
            
            # 调用对应的工具函数
            result = await call_baidu_maps_tool(method, params)
            
            return result
                
        except Exception as e:
            logger.error(f"内置百度地图调用异常: {e}")
            return None

    async def _call_json_rpc_mcp(self, endpoint: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用JSON-RPC MCP服务"""
        try:
            # MCP服务使用JSON-RPC协议
            url = endpoint
            
            # 构建JSON-RPC请求
            json_rpc_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = await self.http_client.post(url, json=json_rpc_request, headers=headers)
            if response.status_code == 200:
                result = response.json()
                # 检查JSON-RPC响应格式
                if "result" in result:
                    content = result["result"]
                    # 处理TextContent格式（百度地图MCP返回格式）
                    if isinstance(content, list) and len(content) > 0:
                        text_content = content[0]
                        if isinstance(text_content, dict) and text_content.get("type") == "text":
                            # 解析返回的JSON文本
                            try:
                                return json.loads(text_content.get("text", "{}"))
                            except json.JSONDecodeError:
                                logger.error("MCP服务返回的文本不是有效JSON")
                                return None
                    return content
                elif "error" in result:
                    logger.error(f"MCP服务错误: {result['error']}")
                    return None
                else:
                    return result
            else:
                logger.error(f"MCP服务HTTP错误: {response.status_code}")
                return None
                    
        except Exception as e:
            logger.error(f"JSON-RPC MCP服务调用异常: {e}")
            return None
    
    def _parse_mcp_transportation(self, data: Dict[str, Any], source: str) -> List[Dict[str, Any]]:
        """解析MCP服务返回的交通数据"""
        transportation = []
        
        try:
            # 处理百度地图MCP返回的数据
            if source == "百度地图":
                # 百度地图API返回格式
                routes = data.get("result", {}).get("routes", [])
                for i, route in enumerate(routes[:2]):  # 只取前2条路线
                    transportation.append({
                        "id": f"baidu_trans_{i+1}",
                        "type": "公共交通",
                        "name": f"百度路线{i+1}",
                        "description": f"百度地图推荐路线",
                        "price": self._estimate_cost_from_route(route),
                        "currency": "CNY",
                        "operating_hours": "06:00-23:00",
                        "frequency": "3-10分钟",
                        "coverage": [route.get("destination", {}).get("name", "目的地")],
                        "features": ["实时路况", "多方案选择"],
                        "source": "百度地图",
                        "duration": route.get("duration", 0) // 60,
                        "distance": route.get("distance", 0) // 1000
                    })
            
            # 处理高德地图MCP返回的数据
            elif source == "高德地图":
                routes = data.get("route", {}).get("paths", [])
                for i, route in enumerate(routes[:2]):  # 只取前2条路线
                    transportation.append({
                        "id": f"amap_trans_{i+1}",
                        "type": "公共交通",
                        "name": f"高德路线{i+1}",
                        "description": f"高德地图推荐路线",
                        "price": self._estimate_cost_from_route(route),
                        "currency": "CNY",
                        "operating_hours": "06:00-23:00",
                        "frequency": "3-10分钟",
                        "coverage": [route.get("destination", {}).get("name", "目的地")],
                        "features": ["实时路况", "多方案选择"],
                        "source": "高德地图",
                        "duration": route.get("duration", 0) // 60,
                        "distance": route.get("distance", 0) // 1000
                    })
            
            return transportation
            
        except Exception as e:
            logger.error(f"解析MCP交通数据失败: {e}")
            return []
    
    def _estimate_cost_from_route(self, route: Dict[str, Any]) -> int:
        """从路线信息估算费用"""
        try:
            # 根据距离和交通方式估算费用
            distance = route.get("distance", 0) / 1000  # 转换为公里
            duration = route.get("duration", 0) / 60    # 转换为分钟
            
            # 简单估算：地铁3元起步，公交2元起步，出租车按距离计费
            if distance < 5:
                return 3  # 地铁短途
            elif distance < 10:
                return 5  # 地铁中途
            elif distance < 20:
                return 8  # 地铁长途
            else:
                return max(10, int(distance * 0.8))  # 出租车
                
        except Exception:
            return 5  # 默认费用
    
    def _get_mock_transportation(self, destination: str) -> List[Dict[str, Any]]:
        """获取模拟交通数据"""
        transportation = [
            {
                "id": "trans_1",
                "type": "地铁",
                "name": "地铁1号线",
                "description": "连接市中心主要景点",
                "price": 3,
                "currency": "CNY",
                "operating_hours": "05:00-23:00",
                "frequency": "2-3分钟",
                "coverage": ["天安门", "王府井", "西单"],
                "features": ["快速", "便宜", "覆盖广"],
                "source": "模拟数据",
                "duration": 30,
                "distance": 15
            },
            {
                "id": "trans_2",
                "type": "出租车",
                "name": "出租车服务",
                "description": "便捷的出行方式",
                "price": 13,
                "currency": "CNY",
                "operating_hours": "24小时",
                "frequency": "随时",
                "coverage": ["全城覆盖"],
                "features": ["门到门", "舒适", "24小时"],
                "source": "模拟数据",
                "duration": 20,
                "distance": 12
            }
        ]
        
        logger.info(f"获取到 {len(transportation)} 条模拟交通信息")
        return transportation
    
    async def get_images(self, query: str, count: int = 5) -> List[str]:
        """获取图片"""
        try:
            if not settings.MAP_API_KEY:
                logger.warning("地图API密钥未配置")
                return []
            
            # 模拟图片API调用
            images = [
                f"https://example.com/image1_{query}.jpg",
                f"https://example.com/image2_{query}.jpg",
                f"https://example.com/image3_{query}.jpg"
            ]
            
            logger.info(f"获取到 {len(images)} 张图片")
            return images[:count]
            
        except Exception as e:
            logger.error(f"获取图片失败: {e}")
            return []
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.http_client.aclose()
