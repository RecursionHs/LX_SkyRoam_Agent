#!/usr/bin/env python3
"""
小红书登录演示脚本
测试Playwright真实爬虫的登录和搜索功能
"""

import asyncio
import sys
from pathlib import Path
from loguru import logger

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from app.platforms.xhs.real_crawler import XiaoHongShuLoginCrawler


async def main():
    """主函数"""
    logger.info("🚀 小红书真实数据爬虫 - 登录演示")
    logger.info("=" * 50)
    
    # 创建爬虫实例
    crawler = XiaoHongShuLoginCrawler()
    
    try:
        logger.info("步骤1: 开始登录流程")
        
        # 启动爬虫（会自动尝试加载cookies）
        await crawler.start()
        
        # 检查登录状态
        if not crawler.is_logged_in:
            logger.info("需要手动登录...")
            success = await crawler.login()
            if not success:
                logger.error("❌ 登录失败")
                return
        
        logger.info("\n步骤2: 测试搜索功能")
        
        # 测试搜索关键词
        test_keywords = ["北京旅游", "上海美食", "成都景点"]
        
        for keyword in test_keywords:
            logger.info(f"\n🔍 搜索关键词: {keyword}")
            try:
                notes = await crawler.search_notes(keyword, limit=5)
                
                if notes:
                    logger.info(f"✅ 成功获取 {len(notes)} 条笔记数据")
                    
                    # 显示前3条笔记的基本信息
                    for i, note in enumerate(notes[:3], 1):
                        logger.info(f"  {i}. {note.get('title', '无标题')[:30]}...")
                        logger.info(f"     👍 {note.get('like_count', 0)} | 💬 {note.get('comment_count', 0)}")
                else:
                    logger.warning(f"⚠️ 未获取到 {keyword} 的笔记数据")
                    
            except Exception as e:
                logger.error(f"❌ 搜索 {keyword} 失败: {e}")
            
            # 等待一下避免请求过快
            await asyncio.sleep(2)
        
        logger.info("\n🎉 测试完成！")
        
        # 显示cookie信息
        cookie_info = crawler.crawler.get_cookie_info()
        if cookie_info["exists"]:
            logger.info(f"📁 Cookie已保存，有效期还有 {7 - float(cookie_info['age_days']):.1f} 天")
        
    except Exception as e:
        logger.error(f"❌ 程序执行出错: {e}")
        
    finally:
        # 关闭爬虫
        await crawler.close()


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level:<8} | {message}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 用户取消操作")
    except Exception as e:
        logger.error(f"❌ 程序异常: {e}")