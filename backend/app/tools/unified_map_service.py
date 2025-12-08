"""
统一地图服务抽象层
支持多地图提供商的回退机制和数据格式统一
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from app.core.config import settings

# 导入各地图服务
from app.tools.baidu_maps_integration import (
    map_geocode as baidu_geocode,
    map_directions as baidu_directions,
    map_search_places as baidu_search_places,
    map_reverse_geocode as baidu_reverse_geocode
)
from app.tools.amap_mcp_client import AmapMCPClient
from app.tools.tianditu_maps_integration import (
    map_geocode as tianditu_geocode,
    map_directions as tianditu_directions,
    map_search_places as tianditu_search_places
)


class UnifiedMapService:
    """统一地图服务，支持多提供商回退"""
    
    def __init__(self):
        self.amap_client = AmapMCPClient()
        # 获取回退顺序，确保主提供商在第一位
        primary_provider = settings.MAP_PROVIDER
        # 解析回退顺序字符串（逗号分隔）
        fallback_str = settings.MAP_PROVIDER_FALLBACK
        fallback_list = [p.strip() for p in fallback_str.split(",") if p.strip()]
        
        # 确保主提供商在第一位
        if primary_provider in fallback_list:
            fallback_list.remove(primary_provider)
        self.provider_order = [primary_provider] + fallback_list
        
        logger.info(f"地图服务提供商顺序: {self.provider_order}")
    
    async def geocode(self, address: str, city: str = "") -> Optional[Dict[str, Any]]:
        """
        地理编码 - 地址转坐标
        支持多提供商回退
        """
        last_error = None
        
        for provider in self.provider_order:
            try:
                logger.debug(f"尝试使用 {provider} 进行地理编码: {address}")
                
                if provider == "amap":
                    result = await self.amap_client.geocode(address, city)
                    if result:
                        return self._normalize_geocode_result(result, "amap")
                
                elif provider == "baidu":
                    result = await baidu_geocode(address)
                    if result and result.get("status") == 0:
                        location = result.get("result", {}).get("location", {})
                        if location:
                            return self._normalize_geocode_result({
                                "lng": location.get("lng"),
                                "lat": location.get("lat"),
                                "formatted_address": result.get("result", {}).get("formatted_address", address)
                            }, "baidu")
                
                elif provider == "tianditu":
                    result = await tianditu_geocode(address)
                    if result and result.get("status") == "0":
                        location = result.get("location", {})
                        if location:
                            return self._normalize_geocode_result({
                                "lng": float(location.get("lon", 0)),
                                "lat": float(location.get("lat", 0)),
                                "formatted_address": location.get("keyWord", address)
                            }, "tianditu")
                
            except Exception as e:
                last_error = e
                logger.warning(f"{provider} 地理编码失败: {e}，尝试下一个提供商")
                continue
        
        logger.error(f"所有地图提供商地理编码都失败: {address}, 最后错误: {last_error}")
        return None
    
    async def search_places_around(
        self,
        location: str,
        keywords: str = "",
        types: str = "",
        radius: int = 5000,
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """
        周边搜索
        支持多提供商回退
        
        Args:
            location: 中心点坐标 "经度,纬度"
            keywords: 搜索关键词
            types: 类型编码（不同地图提供商使用不同格式）
            radius: 搜索半径（米）
            count: 返回数量
        """
        last_error = None
        
        for provider in self.provider_order:
            try:
                logger.debug(f"尝试使用 {provider} 进行周边搜索: {keywords} @ {location}, types={types}")
                
                if provider == "amap":
                    places = await self.amap_client.search_places_around(
                        location=location,
                        keywords=keywords,
                        types=types,
                        radius=radius,
                        offset=count
                    )
                    if places:
                        return [self._normalize_place_result(p, "amap") for p in places]
                
                elif provider == "baidu":
                    result = await baidu_search_places(
                        query=keywords or "景点",
                        location=location,
                        radius=str(radius),
                        tag=types
                    )
                    if result and result.get("status") == 0:
                        items = result.get("result", {}).get("items", [])
                        if items:
                            return [self._normalize_place_result(item, "baidu") for item in items[:count]]
                
                elif provider == "tianditu":
                    # 天地图：优先使用类型编码，关键词作为补充
                    from app.tools.tianditu_maps_integration import get_tianditu_type_code
                    
                    # 将高德/百度的类型编码转换为天地图编码
                    tianditu_type = None
                    if types:
                        # 高德/百度到天地图的类型编码映射
                        # 高德：110000=风景名胜, 050000=餐饮服务, 100000=住宿服务
                        # 天地图：110xxx=餐饮, 120xxx=住宿, 需要查找景点编码
                        type_mapping = {
                            "110000": "180400",  # 风景名胜 - 天地图可能没有对应编码，需要关键词搜索
                            "050000": "110100",  # 餐饮服务 -> 餐馆
                            "100000": "120100",  # 住宿服务 -> 商业性住宿
                            "140700": "160205",  # 科教文化服务（博物馆等）
                        }
                        tianditu_type = type_mapping.get(types)
                        
                        # 如果映射为None，尝试从关键词推断
                        if tianditu_type is None and keywords:
                            tianditu_type = get_tianditu_type_code(keywords)
                    
                    # 如果没有类型编码，尝试从关键词推断
                    if not tianditu_type and keywords:
                        tianditu_type = get_tianditu_type_code(keywords)
                    
                    # 调用天地图API
                    # 策略：如果有类型编码，优先使用类型编码（关键词可选）
                    #       如果没有类型编码，必须使用关键词
                    result = await tianditu_search_places(
                        location=location,
                        radius=radius,
                        count=count,
                        data_types=tianditu_type,  # 优先使用类型编码
                        keywords=keywords if (keywords and not tianditu_type) or (keywords and tianditu_type) else ""  # 有类型编码时关键词作为补充，无类型编码时关键词必需
                    )
                    if result and result.get("status", {}).get("infocode") == 1000:
                        pois = result.get("pois", [])
                        if pois:
                            return [self._normalize_place_result(poi, "tianditu") for poi in pois[:count]]
                
            except Exception as e:
                last_error = e
                logger.warning(f"{provider} 周边搜索失败: {e}，尝试下一个提供商")
                continue
        
        logger.warning(f"所有地图提供商周边搜索都失败，最后错误: {last_error}")
        return []
    
    async def get_directions(
        self,
        origin: str,
        destination: str,
        mode: str = "transit"
    ) -> List[Dict[str, Any]]:
        """
        路线规划
        支持多提供商回退
        """
        last_error = None
        
        for provider in self.provider_order:
            try:
                logger.debug(f"尝试使用 {provider} 进行路线规划: {origin} -> {destination}")
                
                if provider == "amap":
                    routes = await self.amap_client.get_directions(
                        origin=origin,
                        destination=destination,
                        mode=mode
                    )
                    if routes:
                        return routes
                
                elif provider == "baidu":
                    result = await baidu_directions(
                        origin=origin,
                        destination=destination,
                        model=mode
                    )
                    if result and result.get("status") == 0:
                        routes = result.get("result", {}).get("routes", [])
                        if routes:
                            return [self._normalize_route_result(route, "baidu", mode) for route in routes[:3]]
                
                elif provider == "tianditu":
                    result = await tianditu_directions(
                        origin=origin,
                        destination=destination,
                        mode=mode
                    )
                    if result and result.get("status") == "0":
                        # 天地图返回XML格式，需要解析
                        # 这里简化处理，实际应该解析XML
                        logger.warning("天地图路线规划返回XML格式，暂不支持解析")
                        continue
                
            except Exception as e:
                last_error = e
                logger.warning(f"{provider} 路线规划失败: {e}，尝试下一个提供商")
                continue
        
        logger.warning(f"所有地图提供商路线规划都失败，最后错误: {last_error}")
        return []
    
    def _normalize_geocode_result(self, result: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """统一地理编码结果格式"""
        return {
            "destination": result.get("formatted_address", ""),
            "latitude": float(result.get("lat", 0)),
            "longitude": float(result.get("lng", 0)),
            "location_string": f"{result.get('lng', 0)},{result.get('lat', 0)}",
            "provider": provider,
            "formatted_address": result.get("formatted_address", ""),
            "city": result.get("city", ""),
            "district": result.get("district", ""),
            "province": result.get("province", "")
        }
    
    def _normalize_place_result(self, place: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """统一地点搜索结果格式"""
        if provider == "amap":
            location_str = place.get("location", "")
            coordinates = {}
            if location_str and "," in location_str:
                try:
                    lng, lat = location_str.split(",")
                    coordinates = {"lng": float(lng.strip()), "lat": float(lat.strip())}
                except (ValueError, IndexError):
                    coordinates = {}
            
            return {
                "id": f"amap_{place.get('id', '')}",
                "name": place.get("name", ""),
                "category": place.get("category", ""),
                "description": place.get("address", ""),
                "address": place.get("address", ""),
                "rating": float(place.get("rating", 0)) if place.get("rating") else 0.0,
                "coordinates": coordinates,
                "location": location_str,
                "phone": place.get("phone", ""),
                "distance": place.get("distance", ""),
                "source": "高德地图"
            }
        
        elif provider == "baidu":
            location = place.get("location", {})
            return {
                "id": f"baidu_{place.get('uid', '')}",
                "name": place.get("name", ""),
                "category": place.get("detail_info", {}).get("tag", ""),
                "description": place.get("address", ""),
                "address": place.get("address", ""),
                "rating": float(place.get("detail_info", {}).get("overall_rating", 0)) if place.get("detail_info", {}).get("overall_rating") else 0.0,
                "coordinates": {
                    "lat": location.get("lat"),
                    "lng": location.get("lng")
                } if location else {},
                "location": f"{location.get('lng', 0)},{location.get('lat', 0)}" if location else "",
                "phone": place.get("detail_info", {}).get("phone", ""),
                "distance": place.get("distance", ""),
                "source": "百度地图"
            }
        
        elif provider == "tianditu":
            lonlat = place.get("lonlat", "")
            coordinates = {}
            if lonlat and "," in lonlat:
                try:
                    lng, lat = lonlat.split(",")
                    coordinates = {"lng": float(lng.strip()), "lat": float(lat.strip())}
                except (ValueError, IndexError):
                    coordinates = {}
            
            return {
                "id": f"tianditu_{place.get('hotPointID', '')}",
                "name": place.get("name", ""),
                "category": place.get("poiType", ""),
                "description": place.get("address", ""),
                "address": place.get("address", ""),
                "rating": 0.0,  # 天地图不提供评分
                "coordinates": coordinates,
                "location": lonlat,
                "phone": place.get("phone", ""),
                "distance": place.get("distance", ""),
                "source": "天地图"
            }
        
        return place
    
    def _normalize_route_result(self, route: Dict[str, Any], provider: str, mode: str) -> Dict[str, Any]:
        """统一路线规划结果格式"""
        distance = route.get("distance", 0)  # 米
        duration = route.get("duration", 0)  # 秒
        
        return {
            "id": f"{provider}_route_{route.get('index', 0)}",
            "type": "公共交通" if mode == "transit" else "自驾",
            "name": f"{provider}路线{route.get('index', 0) + 1}",
            "description": f"{provider}地图推荐路线",
            "duration": duration // 60 if duration > 0 else 0,  # 转换为分钟
            "distance": distance // 1000 if distance > 0 else 0,  # 转换为公里
            "price": self._estimate_cost(distance, mode),
            "currency": "CNY",
            "operating_hours": "06:00-23:00" if mode == "transit" else "24小时",
            "frequency": "5-15分钟" if mode == "transit" else "随时",
            "coverage": ["目的地"],
            "features": ["实时路况", "多方案选择"],
            "route": route.get("steps", []),
            "source": f"{provider}地图"
        }
    
    def _estimate_cost(self, distance_meters: int, mode: str) -> int:
        """估算费用"""
        distance_km = distance_meters // 1000
        
        if mode == "transit":
            return 5  # 公交费用
        else:
            # 自驾费用：油费 + 过路费
            fuel_cost = distance_km * 0.6
            toll_cost = distance_km * 0.4
            return int(fuel_cost + toll_cost)
    
    async def close(self):
        """关闭所有客户端"""
        try:
            await self.amap_client.close()
        except Exception:
            pass

