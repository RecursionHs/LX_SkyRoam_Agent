"""
目的地相关模型
"""

from sqlalchemy import Column, String, Text, Float, JSON
from app.models.base import BaseModel


class Destination(BaseModel):
    """目的地模型"""
    __tablename__ = "destinations"
    
    # 基本信息
    name = Column(String(100), nullable=False, index=True)
    country = Column(String(100), nullable=False)
    city = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    
    # 地理信息
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timezone = Column(String(50), nullable=True)
    
    # 描述信息
    description = Column(Text, nullable=True)
    highlights = Column(JSON, nullable=True)  # 主要亮点
    best_time_to_visit = Column(String(200), nullable=True)
    
    # 统计信息
    popularity_score = Column(Float, default=0.0, nullable=False)
    safety_score = Column(Float, nullable=True)
    cost_level = Column(String(20), nullable=True)  # low, medium, high
    
    # 媒体资源
    images = Column(JSON, nullable=True)  # 图片URL列表
    videos = Column(JSON, nullable=True)  # 视频URL列表
    
    def __repr__(self):
        return f"<Destination(name={self.name}, country={self.country})>"
