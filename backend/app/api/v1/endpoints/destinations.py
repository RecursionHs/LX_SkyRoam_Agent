"""
目的地API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from loguru import logger

from app.core.database import get_async_db
from app.models.destination import Destination, Attraction, Restaurant
from app.models.travel_plan import TravelPlan

router = APIRouter()


@router.get("/")
async def get_destinations(
    skip: int = 0,
    limit: int = 100,
    country: Optional[str] = None,
    include_from_plans: bool = Query(True, description="是否从旅行计划中提取目的地"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    获取目的地列表
    支持从数据库和旅行计划中合并获取目的地数据
    """
    from sqlalchemy import select, func
    
    # 1. 从数据库获取目的地
    query = select(Destination)
    if country:
        query = query.where(Destination.country == country)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    db_destinations = result.scalars().all()
    
    # 转换为字典格式，便于合并
    destinations_map: Dict[str, Dict[str, Any]] = {}
    
    for dest in db_destinations:
        key = dest.name.lower().strip()
        destinations_map[key] = {
            "id": dest.id,
            "name": dest.name,
            "country": dest.country,
            "city": dest.city,
            "region": dest.region,
            "latitude": dest.latitude,
            "longitude": dest.longitude,
            "timezone": dest.timezone,
            "description": dest.description,
            "highlights": dest.highlights,
            "best_time_to_visit": dest.best_time_to_visit,
            "popularity_score": dest.popularity_score or 0.0,
            "safety_score": dest.safety_score,
            "cost_level": dest.cost_level,
            "images": dest.images,
            "videos": dest.videos,
            "plan_count": 0,  # 从旅行计划中统计的数量
            "source": "database"
        }
    
    # 2. 从旅行计划中提取目的地（如果启用）
    if include_from_plans:
        try:
            # 统计每个目的地出现的次数
            plans_query = select(
                TravelPlan.destination,
                func.count(TravelPlan.id).label('count')
            ).where(
                TravelPlan.destination.isnot(None),
                TravelPlan.destination != ''
            ).group_by(TravelPlan.destination)
            
            plans_result = await db.execute(plans_query)
            plan_destinations = plans_result.all()
            
            # 合并到目的地映射中
            for plan_dest, count in plan_destinations:
                if not plan_dest:
                    continue
                    
                dest_name = plan_dest.strip()
                key = dest_name.lower()
                
                if key in destinations_map:
                    # 更新已有目的地的计划数量
                    destinations_map[key]["plan_count"] = count
                    # 如果数据库中没有热度分数，根据计划数量计算
                    if destinations_map[key]["popularity_score"] == 0:
                        destinations_map[key]["popularity_score"] = min(100, count * 2)
                else:
                    # 创建新的目的地条目
                    destinations_map[key] = {
                        "id": None,  # 动态生成的目的地没有ID
                        "name": dest_name,
                        "country": None,  # 需要后续解析
                        "city": None,
                        "region": None,
                        "latitude": None,
                        "longitude": None,
                        "timezone": None,
                        "description": f"来自 {count} 个旅行计划的热门目的地",
                        "highlights": None,
                        "best_time_to_visit": None,
                        "popularity_score": min(100, count * 2),  # 根据计划数量计算热度
                        "safety_score": None,
                        "cost_level": None,
                        "images": None,
                        "videos": None,
                        "plan_count": count,
                        "source": "travel_plans"
                    }
        except Exception as e:
            logger.warning(f"从旅行计划提取目的地失败: {e}")
    
    # 3. 转换为列表并按热度排序
    destinations_list = list(destinations_map.values())
    destinations_list.sort(key=lambda x: x["popularity_score"], reverse=True)
    
    # 4. 应用分页
    paginated = destinations_list[skip:skip + limit]
    
    return paginated


@router.get("/{destination_id}")
async def get_destination(
    destination_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """获取单个目的地详情"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(Destination)
        .options(
            selectinload(Destination.attractions),
            selectinload(Destination.restaurants)
        )
        .where(Destination.id == destination_id)
    )
    destination = result.scalar_one_or_none()
    
    if not destination:
        raise HTTPException(status_code=404, detail="目的地不存在")
    
    return destination


@router.get("/{destination_id}/attractions")
async def get_destination_attractions(
    destination_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db)
):
    """获取目的地景点列表"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Attraction)
        .where(Attraction.destination_id == destination_id)
        .offset(skip)
        .limit(limit)
    )
    attractions = result.scalars().all()
    
    return attractions


@router.get("/{destination_id}/restaurants")
async def get_destination_restaurants(
    destination_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db)
):
    """获取目的地餐厅列表"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Restaurant)
        .where(Restaurant.destination_id == destination_id)
        .offset(skip)
        .limit(limit)
    )
    restaurants = result.scalars().all()
    
    return restaurants
