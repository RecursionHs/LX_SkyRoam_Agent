#!/usr/bin/env python3
"""
小红书Cookie管理工具
用于查看、清除和管理小红书登录cookies
"""

import asyncio
import sys
from pathlib import Path
from loguru import logger

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from app.platforms.xhs.playwright_crawler import PlaywrightXHSCrawler


async def show_cookie_info():
    """显示cookie信息"""
    crawler = PlaywrightXHSCrawler()
    info = crawler.get_cookie_info()
    
    print("\n" + "="*50)
    print("🍪 小红书Cookie信息")
    print("="*50)
    
    if not info["exists"]:
        print("❌ 没有找到cookie文件")
        if "error" in info:
            print(f"   错误: {info['error']}")
        else:
            print(f"   {info.get('message', '未知原因')}")
    else:
        print(f"✅ Cookie文件存在")
        print(f"📁 存储路径: {crawler.cookies_file}")
        print(f"📊 Cookie数量: {info['count']}")
        print(f"📅 保存时间: {info['saved_at']}")
        print(f"⏰ 存储天数: {info['age_days']} 天")
        print(f"📋 文件格式: {info['format']}")
        
        if info.get('expired'):
            print("⚠️  状态: 已过期 (>7天)")
        else:
            print("✅ 状态: 有效")
    
    print("="*50)


async def clear_cookies():
    """清除cookies"""
    crawler = PlaywrightXHSCrawler()
    
    # 先显示当前信息
    info = crawler.get_cookie_info()
    if not info["exists"]:
        print("❌ 没有找到cookie文件，无需清除")
        return
    
    print(f"\n将要删除cookie文件: {crawler.cookies_file}")
    confirm = input("确认删除吗？(y/N): ").strip().lower()
    
    if confirm in ['y', 'yes']:
        crawler.clear_cookies()
        print("✅ Cookie文件已删除")
    else:
        print("❌ 操作已取消")


async def test_login():
    """测试登录状态"""
    print("\n🔍 测试当前登录状态...")
    
    async with PlaywrightXHSCrawler() as crawler:
        try:
            # 访问小红书首页
            await crawler.page.goto('https://www.xiaohongshu.com/explore')
            await asyncio.sleep(10)
            
            # 检查登录状态
            is_logged_in = await crawler.check_login_status()
            
            if is_logged_in:
                print("✅ 当前已登录小红书")
            else:
                print("❌ 当前未登录小红书")
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")


async def interactive_login():
    """交互式登录"""
    print("\n🔐 开始交互式登录...")
    
    async with PlaywrightXHSCrawler() as crawler:
        try:
            # 先检查当前状态
            await crawler.page.goto('https://www.xiaohongshu.com/explore')
            await asyncio.sleep(10)
            
            if await crawler.check_login_status():
                print("✅ 已经登录，无需重新登录")
                return
            
            # 执行登录流程
            success = await crawler.login_with_qr()
            
            if success:
                print("🎉 登录成功！Cookie已自动保存")
            else:
                print("❌ 登录失败")
                
        except Exception as e:
            print(f"❌ 登录过程出错: {e}")


def show_menu():
    """显示菜单"""
    print("\n" + "="*50)
    print("🍪 小红书Cookie管理工具")
    print("="*50)
    print("1. 查看Cookie信息")
    print("2. 清除Cookie文件")
    print("3. 测试登录状态")
    print("4. 交互式登录")
    print("0. 退出")
    print("="*50)


async def main():
    """主函数"""
    while True:
        show_menu()
        
        try:
            choice = input("请选择操作 (0-4): ").strip()
            
            if choice == "0":
                print("👋 再见！")
                break
            elif choice == "1":
                await show_cookie_info()
            elif choice == "2":
                await clear_cookies()
            elif choice == "3":
                await test_login()
            elif choice == "4":
                await interactive_login()
            else:
                print("❌ 无效选择，请重新输入")
                
        except KeyboardInterrupt:
            print("\n👋 用户取消操作，再见！")
            break
        except Exception as e:
            print(f"❌ 操作出错: {e}")
        
        input("\n按回车键继续...")


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")