#!/usr/bin/env python3
"""
小红书数据集成功能演示脚本
展示完整的数据获取、处理和格式化流程
"""

import asyncio
import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.xhs_integration_service import XHSIntegrationService
from app.services.data_collector import DataCollector


async def demo_xhs_integration():
    """演示小红书数据集成功能"""
    
    logger.info("🚀 小红书数据集成功能演示开始")
    
    try:
        # 1. 初始化服务
        logger.info("1. 初始化小红书集成服务")
        xhs_service = XHSIntegrationService()
        logger.info("✓ XHSIntegrationService 初始化成功")
        
        # 2. 测试不同目的地的数据获取
        destinations = ["杭州"]
        
        for destination in destinations:
            logger.info(f"\n2. 获取 {destination} 的小红书数据")
            
            # 获取笔记数据
            notes = await xhs_service.get_destination_notes(destination)
            logger.info(f"✓ 成功获取 {len(notes)} 条 {destination} 相关笔记")
            
            # 显示笔记标题
            for i, note in enumerate(notes[:3], 1):
                logger.info(f"  {i}. {note.title}")
                logger.info(f"     👍 {note.liked_count} | 💾 {note.collected_count} | 💬 {note.comment_count}")
            
            # 格式化数据
            formatted_text = xhs_service.format_notes_for_llm(notes, destination)
            logger.info(f"✓ 格式化文本长度: {len(formatted_text)} 字符")
            
            # 显示格式化文本的开头部分
            preview = formatted_text[:200] + "..." if len(formatted_text) > 200 else formatted_text
            logger.info(f"📝 格式化文本预览:\n{preview}")
        
        # 3. 测试DataCollector集成
        logger.info("\n3. 测试DataCollector集成")
        data_collector = DataCollector()
        
        # 收集数据
        collected_data = await data_collector.collect_xiaohongshu_data("北京")
        logger.info(f"✓ DataCollector成功收集 {len(collected_data)} 条数据")
        
        # 格式化数据
        formatted_data = data_collector.format_xiaohongshu_data_for_llm("北京", collected_data)
        logger.info(f"✓ DataCollector格式化文本长度: {len(formatted_data)} 字符")
        
        # 4. 展示数据质量
        logger.info("\n4. 数据质量分析")
        if collected_data:
            sample_note = collected_data[0]
            logger.info(f"📊 样本数据分析:")
            logger.info(f"  - 标题: {sample_note.get('title', 'N/A')}")
            logger.info(f"  - 标签数量: {len(sample_note.get('tag_list', []))}")
            logger.info(f"  - 图片数量: {len(sample_note.get('img_urls', []))}")
            logger.info(f"  - 相关性得分: {sample_note.get('relevance_score', 0):.2f}")
            logger.info(f"  - 发布时间: {sample_note.get('publish_time', 'N/A')}")
        
        logger.info("\n🎉 小红书数据集成功能演示完成！")
        logger.info("✅ 所有功能正常工作，可以集成到旅游规划系统中")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理资源
        if 'data_collector' in locals():
            await data_collector.close()


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # 运行演示
    result = asyncio.run(demo_xhs_integration())
    
    if result:
        logger.info("🌟 演示成功完成")
        sys.exit(0)
    else:
        logger.error("💥 演示失败")
        sys.exit(1)