"""
地图API端点
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
import httpx
import os
from typing import Optional
from loguru import logger

router = APIRouter()

# 获取API密钥
AMAP_API_KEY = os.getenv('AMAP_API_KEY')
BAIDU_API_KEY = os.getenv('BAIDU_MAPS_API_KEY')


@router.get("/static")
async def get_static_map(
    provider: str = Query(..., description="地图提供商: amap 或 baidu"),
    longitude: float = Query(..., description="经度"),
    latitude: float = Query(..., description="纬度"),
    zoom: int = Query(13, description="缩放级别"),
    width: int = Query(400, description="图片宽度"),
    height: int = Query(300, description="图片高度"),
    title: Optional[str] = Query(None, description="标记标题")
):
    """
    获取静态地图图片（代理服务）
    """
    try:
        if provider == "amap":
            if not AMAP_API_KEY or AMAP_API_KEY == "your-amap-api-key-here":
                raise HTTPException(status_code=500, detail="高德地图API密钥未配置")
            
            # 构建高德静态地图URL - 使用正确的参数格式
            url = "https://restapi.amap.com/v3/staticmap"
            
            params = {
                "key": AMAP_API_KEY,
                "location": f"{longitude},{latitude}",
                "zoom": zoom,
                "size": f"{width}*{height}",
                "traffic": 0,
                "scale": 1
            }
            
            # 添加标记点，格式：经度,纬度
            if title:
                # 使用markers参数添加标记点
                params["markers"] = f"mid,,A:{longitude},{latitude}"
                # 使用labels参数添加标签，格式：内容,字体,字体颜色,背景颜色:经度,纬度
                params["labels"] = f"{title},1,0,16,0xFFFFFF,0x008000:{longitude},{latitude}"
            else:
                # 即使没有标题也添加一个简单的标记点
                params["markers"] = f"mid,,A:{longitude},{latitude}"
            
        elif provider == "baidu":
            if not BAIDU_API_KEY:
                raise HTTPException(status_code=500, detail="百度地图API密钥未配置")
            
            # 构建百度静态地图URL
            url = "https://api.map.baidu.com/staticimage/v2"
            params = {
                "ak": BAIDU_API_KEY,
                "center": f"{longitude},{latitude}",
                "zoom": zoom,
                "width": width,
                "height": height
            }
            
            if title:
                params["markers"] = f"{longitude},{latitude}"
                params["markerStyles"] = "m,A"
            
        else:
            raise HTTPException(status_code=400, detail="不支持的地图提供商")
        
        # 请求静态地图
        logger.info(f"请求地图API: {url}")
        logger.info(f"请求参数: {params}")
        
        async with httpx.AsyncClient(timeout=30.0, proxies=None) as client:
            response = await client.get(url, params=params)
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应头: {response.headers}")
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"地图API返回错误状态码 {response.status_code}: {error_text}")
                raise HTTPException(status_code=500, detail=f"地图API返回错误: {error_text}")
            
            response.raise_for_status()
            
            # 检查响应内容类型
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                # 如果不是图片，可能是错误响应
                error_text = response.text
                logger.error(f"地图API返回非图片内容: {error_text}")
                raise HTTPException(status_code=500, detail="地图服务返回错误")
            
            # 返回图片
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=3600",  # 缓存1小时
                    "Access-Control-Allow-Origin": "*"
                }
            )
            
    except httpx.HTTPError as e:
        logger.error(f"请求地图API失败: {str(e)}")
        raise HTTPException(status_code=500, detail="地图服务请求失败")
    except Exception as e:
        logger.error(f"获取静态地图失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取地图失败")


@router.get("/health")
async def map_health():
    """
    地图服务健康检查
    """
    return {
        "status": "ok",
        "amap_configured": bool(AMAP_API_KEY),
        "baidu_configured": bool(BAIDU_API_KEY)
    }