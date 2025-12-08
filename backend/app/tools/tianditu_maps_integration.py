#!/usr/bin/env python3
"""
天地图API集成模块
"""

import os
import json
import httpx
import re
from typing import Dict, Any, List, Optional
from loguru import logger
from app.core.config import settings

# 获取API密钥
api_key = os.getenv('TIANDITU_API_KEY', getattr(settings, 'TIANDITU_API_KEY', ''))
api_url = os.getenv('TIANDITU_API_BASE', getattr(settings, 'TIANDITU_API_BASE', 'https://api.tianditu.gov.cn'))

# 天地图类型编码映射（根据分类表）
# 注意：根据图片，天地图的编码体系：
# 110xxx - 餐饮相关（110100餐馆，110200快餐，110300休闲餐饮）
# 120xxx - 住宿相关（120100商业性住宿，120101星级宾馆）
# 130xxx - 零售相关
# 景点编码需要根据实际API文档确认，暂时使用关键词搜索
TIANDITU_TYPE_CODES = {
    # 餐饮相关（110xxx系列）- 根据图片
    "餐厅": "110100",  # 餐馆
    "餐馆": "110100",
    "饭店": "110100",  # 饭店也是餐馆
    "中餐馆": "110101",
    "异国风味": "110102",
    "地方风味": "110103",
    "快餐": "110200",
    "休闲餐饮": "110300",
    "酒吧": "110301",
    "咖啡馆": "110303",
    "茶楼": "110304",
    "茶艺馆": "110304",
    
    # 住宿相关（120xxx系列）- 根据图片
    "酒店": "120100",  # 商业性住宿
    "宾馆": "120101",  # 星级宾馆
    "旅馆": "120102",
    "招待所": "120102",
    "酒店式公寓": "120103",
    
    # 购物相关（130xxx系列）- 根据图片
    "购物": "130100",  # 综合零售
    "超市": "130105",
    "便利店": "130104",
    "小商品城": "130101",
    "百货商城": "130102",
    "百货商店": "130102",

    "休闲度假": "180300",
    "公园": "180304",
    "街心公园": "180305",
    "广场": "180306",
    "游乐园": "180307",
    "动物园": "180308",
    "植物园": "180309",
    "水族馆": "180310",
    
    # 景点相关 - 图片中未明确显示编码，使用关键词搜索
    # 如果需要精确搜索，可能需要查找天地图的实际景点编码
    "景区服务点": "180402",  # 使用关键词搜索
    "风景名胜": "180400",  # 使用关键词搜索
    "博物馆": "160205",  # 使用关键词搜索，或查找对应编码
}

def mask_api_key(text: str) -> str:
    """信息脱敏函数"""
    if not text or not api_key:
        return text
    
    if api_key not in text:
        return text
    
    if len(api_key) <= 8:
        masked_key = api_key[:2] + '*' * (len(api_key) - 4) + api_key[-2:]
    else:
        masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
    
    return text.replace(api_key, masked_key)

def is_latlng(text: str) -> bool:
    """判断输入是否为经纬度坐标"""
    pattern = r'^\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*$'
    match = re.match(pattern, text)
    if not match:
        return False
    lat, lng = float(match.group(1)), float(match.group(2))
    return -90 <= lat <= 90 and -180 <= lng <= 180

async def map_geocode(address: str) -> Dict[str, Any]:
    """
    地理编码服务 - 地址转坐标
    """
    try:
        if not api_key:
            raise Exception("天地图API密钥未配置")
        
        url = f"{api_url}/geocoder"
        params = {
            "ds": json.dumps({"keyWord": address}),
            "tk": api_key
        }
        
        async with httpx.AsyncClient(timeout=30.0, proxies={}) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") != "0":
                error_msg = result.get("msg", "未知错误")
                raise Exception(f"地理编码错误: {mask_api_key(error_msg)}")
            
            return result
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP请求失败: {str(e)}"
        raise Exception(error_msg) from e
    except Exception as e:
        error_msg = f"地理编码异常: {str(e)}"
        raise Exception(error_msg) from e

async def map_directions(
    origin: str,
    destination: str,
    mode: str = "driving",
    waypoints: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    路线规划服务
    mode: "driving" 或 "transit"
    """
    try:
        if not api_key:
            raise Exception("天地图API密钥未配置")
        
        # 如果输入不是坐标，先进行地理编码
        if not is_latlng(origin):
            geocode_result = await map_geocode(origin)
            location = geocode_result.get("location", {})
            origin = f"{location.get('lon')},{location.get('lat')}"
        
        if not is_latlng(destination):
            geocode_result = await map_geocode(destination)
            location = geocode_result.get("location", {})
            destination = f"{location.get('lon')},{location.get('lat')}"
        
        if mode == "driving":
            # 驾车规划
            url = f"{api_url}/drive"
            post_data = {
                "orig": origin,
                "dest": destination,
                "style": "0"  # 0：最快路线，1：最短路线，2：避开高速，3：步行
            }
            
            if waypoints:
                post_data["mid"] = ";".join(waypoints)
            
            params = {
                "postStr": json.dumps(post_data),
                "type": "search",
                "tk": api_key
            }
        else:
            # 公交规划
            url = f"{api_url}/transit"
            post_data = {
                "startposition": origin,
                "endposition": destination,
                "linetype": "1"  # 1：较快捷
            }
            
            params = {
                "postStr": json.dumps(post_data),
                "type": "busline",
                "tk": api_key
            }
        
        async with httpx.AsyncClient(timeout=30.0, proxies={}) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            # 公交规划返回XML，驾车规划返回XML
            content_type = response.headers.get("content-type", "")
            if "xml" in content_type.lower():
                # 解析XML响应（简化处理，实际应该用xml解析器）
                result = {"status": "0", "data": response.text}
            else:
                result = response.json()
            
            if result.get("status") != "0" and result.get("resultCode") != 0:
                error_msg = result.get("msg") or result.get("message", "未知错误")
                raise Exception(f"路线规划错误: {mask_api_key(error_msg)}")
            
            return result
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP请求失败: {str(e)}"
        raise Exception(error_msg) from e
    except Exception as e:
        error_msg = f"路线规划异常: {str(e)}"
        raise Exception(error_msg) from e

async def map_search_places(
    query: str = "",
    location: Optional[str] = None,
    radius: int = 5000,
    count: int = 10,
    data_types: Optional[str] = None,
    keywords: Optional[str] = None
) -> Dict[str, Any]:
    """
    周边搜索服务
    
    Args:
        query: 搜索关键词（已废弃，使用keywords代替）
        location: 中心点坐标 "经度,纬度"
        radius: 搜索半径（米）
        count: 返回数量
        data_types: 类型编码（优先使用，如 "110100" 表示餐馆，多个用逗号分隔）
        keywords: 关键词（作为补充，当有data_types时可以为空）
    """
    try:
        if not api_key:
            raise Exception("天地图API密钥未配置")
        
        url = f"{api_url}/v2/search"
        
        # 优先使用 keywords 参数，如果没有则使用 query（向后兼容）
        key_word = keywords or query or ""
        
        if location:
            # 周边搜索 - 有坐标时优先使用 dataTypes
            post_data = {
                "level": 12,
                "queryRadius": radius,
                "pointLonlat": location,
                "queryType": 3,  # 3：周边搜索
                "start": 0,
                "count": count
            }
            
            # 有坐标时：优先使用类型编码，关键词作为补充
            if data_types:
                # 支持多个类型编码，用逗号分隔
                if isinstance(data_types, str):
                    # 如果是字符串，可能是逗号分隔的多个编码
                    type_list = [t.strip() for t in data_types.split(",") if t.strip()]
                    if len(type_list) == 1:
                        post_data["dataTypes"] = type_list[0]  # 单个编码
                    else:
                        # 多个编码，天地图API可能需要特殊格式，先尝试第一个
                        post_data["dataTypes"] = type_list[0]
                        logger.debug(f"天地图多个类型编码，使用第一个: {type_list[0]}")
                else:
                    post_data["dataTypes"] = str(data_types)
                
                # 如果有关键词，也加上（作为补充筛选，提高准确性）
                if key_word:
                    post_data["keyWord"] = key_word
            else:
                # 没有类型编码，必须使用关键词
                if not key_word:
                    raise Exception("周边搜索需要提供关键词或类型编码")
                post_data["keyWord"] = key_word
        else:
            # 区域搜索 - 没有坐标时，必须使用类型编码来限制内容，避免搜索到不相关的地名
            if not data_types and not key_word:
                raise Exception("区域搜索需要提供关键词或类型编码")
            
            post_data = {
                "level": 12,
                "queryType": 1,  # 1：区域搜索
                "start": 0,
                "count": count
            }
            
            # 区域搜索优先使用类型编码来限制内容
            if data_types:
                if isinstance(data_types, str):
                    type_list = [t.strip() for t in data_types.split(",") if t.strip()]
                    if type_list:
                        post_data["dataTypes"] = type_list[0]
                else:
                    post_data["dataTypes"] = str(data_types)
                
                # 如果有关键词，也加上（作为补充）
                if key_word:
                    post_data["keyWord"] = key_word
            else:
                # 没有类型编码，使用关键词（但可能搜索到地名，不够精确）
                post_data["keyWord"] = key_word
        
        params = {
            "postStr": json.dumps(post_data),
            "type": "query",
            "tk": api_key
        }
        
        async with httpx.AsyncClient(timeout=30.0, proxies={}) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status", {}).get("infocode") != 1000:
                error_msg = result.get("status", {}).get("cndesc", "未知错误")
                raise Exception(f"地点搜索错误: {mask_api_key(error_msg)}")
            
            return result
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP请求失败: {str(e)}"
        raise Exception(error_msg) from e
    except Exception as e:
        error_msg = f"地点搜索异常: {str(e)}"
        raise Exception(error_msg) from e

def get_tianditu_type_code(category: str) -> Optional[str]:
    """
    根据分类名称获取天地图类型编码
    
    Args:
        category: 分类名称，如 "景点"、"餐厅"、"酒店"
    
    Returns:
        类型编码字符串，如果未找到或为None（表示需使用关键词）则返回None
    """
    code = TIANDITU_TYPE_CODES.get(category)
    # 如果编码为None，表示该分类需要使用关键词搜索，而不是类型编码
    return code if code is not None else None

async def map_static_image(
    center: str,
    width: int = 400,
    height: int = 300,
    zoom: int = 10
) -> bytes:
    """
    静态地图服务
    center: "经度,纬度"
    """
    try:
        if not api_key:
            raise Exception("天地图API密钥未配置")
        
        url = f"{api_url}/staticimage"
        params = {
            "center": center,
            "width": str(width),
            "height": str(height),
            "zoom": str(zoom),
            "tk": api_key
        }
        
        async with httpx.AsyncClient(timeout=30.0, proxies={}) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.content
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP请求失败: {str(e)}"
        raise Exception(error_msg) from e
    except Exception as e:
        error_msg = f"静态地图异常: {str(e)}"
        raise Exception(error_msg) from e

# 工具函数映射
TOOL_FUNCTIONS = {
    "map_geocode": map_geocode,
    "map_directions": map_directions,
    "map_search_places": map_search_places,
    "map_static_image": map_static_image,
}

async def call_tianditu_maps_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """调用天地图工具"""
    if tool_name not in TOOL_FUNCTIONS:
        raise ValueError(f"未知工具: {tool_name}")
    
    func = TOOL_FUNCTIONS[tool_name]
    return await func(**arguments)

