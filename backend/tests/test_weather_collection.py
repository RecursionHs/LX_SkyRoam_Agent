#!/usr/bin/env python3
"""
测试天气数据收集功能
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ 已加载环境变量文件: {env_path}")
else:
    print(f"⚠️ 环境变量文件不存在: {env_path}")

from app.core.config import settings
from app.services.data_collector import DataCollector
from app.tools.amap_mcp_client import AmapMCPClient
from loguru import logger

# 加载.env环境变量
load_dotenv()

async def test_weather_collection():
    """测试天气数据收集"""
    logger.info("开始测试天气数据收集功能...")
    
    # 创建数据收集器
    data_collector = DataCollector()
    
    # 测试城市
    test_cities = ["西湖", "北京"]
    
    # 测试日期
    start_date = datetime.now()
    end_date = start_date + timedelta(days=3)
    
    for city in test_cities:
        logger.info(f"\n=== 测试城市: {city} ===")
        
        try:
            # 收集天气数据
            weather_data = await data_collector.collect_weather_data(
                destination=city,
                start_date=start_date,
                end_date=end_date
            )
            
            if weather_data:
                logger.info(f"✅ {city} 天气数据收集成功")
                logger.info(f"位置: {weather_data.get('location', 'N/A')}")
                
                # 显示当前天气
                current = weather_data.get('current', {})
                if current:
                    logger.info(f"当前天气: {current.get('weather', 'N/A')}")
                    logger.info(f"温度: {current.get('temperature', 'N/A')}°C")
                    logger.info(f"湿度: {current.get('humidity', 'N/A')}%")
                
                # 显示预报天气
                forecast = weather_data.get('forecast', [])
                logger.info(f"预报天数: {len(forecast)}")
                
                # 显示建议
                recommendations = weather_data.get('recommendations', [])
                if recommendations:
                    logger.info(f"天气建议: {', '.join(recommendations)}")
                
            else:
                logger.warning(f"❌ {city} 天气数据收集失败")
                
        except Exception as e:
            logger.error(f"❌ {city} 天气数据收集异常: {e}")
    
    # 关闭客户端
    await data_collector.close()
    logger.info("天气数据收集测试完成")

async def test_amap_client_directly():
    """直接测试AmapMCPClient"""
    logger.info("\n=== 直接测试AmapMCPClient ===")
    
    amap_client = AmapMCPClient()
    
    test_cities = ["西湖", "北京"]
    
    for city in test_cities:
        logger.info(f"\n--- 测试城市: {city} ---")
        
        try:
            # 测试实况天气
            weather_data = await amap_client.get_weather(city, "base")
            logger.info(f"实况天气数据: {weather_data}")
            
            # 测试预报天气
            weather_data = await amap_client.get_weather(city, "all")
            logger.info(f"预报天气数据: {weather_data}")
            
        except Exception as e:
            logger.error(f"直接测试失败: {e}")
    
    await amap_client.close()

async def main():
    """主函数"""
    logger.info(f"当前天气数据源配置: {settings.WEATHER_DATA_SOURCE}")
    logger.info(f"高德地图API密钥配置: {'已配置' if settings.AMAP_API_KEY else '未配置'}")
    logger.info(f"高德地图MCP端点: {settings.AMAP_MCP_HTTP_URL}")
    
    # 测试直接调用
    await test_amap_client_directly()
    
    # 测试数据收集器
    await test_weather_collection()

if __name__ == "__main__":
    asyncio.run(main())