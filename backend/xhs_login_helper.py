#!/usr/bin/env python3
"""
小红书登录助手
简化的登录工具，帮助用户快速登录小红书账号
"""

import asyncio
import sys
from pathlib import Path
from loguru import logger

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.platforms.xhs.real_crawler import XiaoHongShuLoginCrawler
from app.services.enhanced_cookie_manager import enhanced_cookie_manager
from app.services.xhs_startup_service import handle_xhs_login_error


def print_banner():
    """打印欢迎横幅"""
    print("\n" + "="*60)
    print("🔐 小红书智能登录助手 v2.0")
    print("="*60)
    print("📱 帮助您快速登录小红书账号，获取真实数据")
    print("🎯 支持智能重试和增强Cookie管理")
    print("🚀 全新升级：更稳定、更可靠、更智能")
    print("="*60)


def print_menu():
    """显示菜单选项"""
    print("\n📋 请选择操作：")
    print("1. 🔍 检查当前登录状态")
    print("2. 📱 智能登录（支持重试）")
    print("3. 🍪 查看增强Cookie信息")
    print("4. 🧹 清除所有Cookie（重新登录）")
    print("5. ❓ 登录帮助说明")
    print("0. 🚪 退出")
    print("-" * 40)


def print_help():
    """打印帮助信息"""
    print("\n" + "="*50)
    print("📖 小红书登录帮助说明")
    print("="*50)
    print("🔐 为什么需要登录？")
    print("   小红书对未登录用户限制数据访问，登录后可以获取真实的笔记数据")
    print()
    print("📱 如何登录？")
    print("   1. 选择'智能登录'选项")
    print("   2. 系统会自动尝试多种登录方式")
    print("   3. 使用小红书APP扫描屏幕上的二维码")
    print("   4. 在APP中确认登录")
    print("   5. 等待登录成功提示")
    print()
    print("🍪 增强Cookie管理：")
    print("   - 支持主备Cookie文件，提高可靠性")
    print("   - 自动会话恢复功能")
    print("   - Cookie有效期延长至14天")
    print("   - 智能过期检测和自动更新")
    print("   - 详细的状态信息显示")
    print()
    print("🔄 智能重试机制：")
    print("   - 登录失败时自动重试")
    print("   - 支持多种登录策略")
    print("   - 运行时自动检测Cookie失效")
    print("   - 无缝的后台重新登录")
    print()
    print("⚠️  注意事项：")
    print("   - 请使用真实的小红书账号")
    print("   - 不要频繁登录，避免账号异常")
    print("   - 登录后请合理使用，遵守平台规则")
    print("   - 系统会自动管理Cookie，无需手动干预")
    print("="*50)


async def check_login_status():
    """检查登录状态"""
    print("\n🔍 正在检查登录状态...")
    try:
        # 使用增强Cookie管理器检查登录状态（独立验证）
        is_valid = await enhanced_cookie_manager.validate_cookies_standalone()
        if is_valid:
            print("✅ 登录状态有效")
            # 显示Cookie信息
            await show_cookies()
        else:
            print("❌ 登录状态无效，需要重新登录")
    except Exception as e:
        print(f"❌ 检查失败: {e}")


async def qr_login():
    """智能登录（支持重试）"""
    print("\n📱 开始智能登录流程...")
    try:
        # 使用内置重试机制进行登录
        from app.services.xhs_startup_service import xhs_startup_service
        success = await xhs_startup_service.initialize_xhs_service()
        if success:
            print("✅ 登录成功！")
            await show_cookies()
        else:
            print("❌ 登录失败，请重试")
    except Exception as e:
        print(f"❌ 登录失败: {e}")


async def show_cookies():
    """显示Cookie信息"""
    print("\n🍪 Cookie信息：")
    try:
        # 使用增强Cookie管理器显示信息
        info = enhanced_cookie_manager.get_cookie_status()
        
        print(f"📁 主Cookie文件: {info.get('primary_exists', False)}")
        print(f"📁 备份Cookie文件: {info.get('backup_exists', False)}")
        print(f"📁 会话文件: {info.get('session_exists', False)}")
        
        # 从文件信息中获取详细数据
        files = info.get('files', [])
        primary_file = next((f for f in files if f.get('name') == 'primary'), None)
        
        if primary_file and 'cookie_count' in primary_file:
            print(f"📊 Cookie数量: {primary_file['cookie_count']}")
            
            if primary_file.get('saved_at') and primary_file['saved_at'] != 'Unknown':
                print(f"💾 保存时间: {primary_file['saved_at']}")
                
            if primary_file.get('expires_at') and primary_file['expires_at'] != 'Unknown':
                from datetime import datetime
                try:
                    expires_time = datetime.fromisoformat(primary_file['expires_at'].replace('Z', '+00:00'))
                    current_time = datetime.now()
                    if expires_time > current_time:
                        days_remaining = (expires_time - current_time).days
                        print(f"⏰ 剩余有效期: {days_remaining} 天")
                        print("✅ 状态: 有效")
                    else:
                        print("⚠️ Cookie已过期")
                        print("❌ 状态: 无效")
                except Exception:
                    print("⚠️ 无法解析过期时间")
                    print("❓ 状态: 未知")
            else:
                print("❓ 状态: 未知")
        else:
            print("📊 Cookie数量: 0")
            print("❌ 状态: 无效")
        
    except Exception as e:
        print(f"❌ 获取Cookie信息失败: {e}")


def clear_cookies():
    """清除Cookie"""
    print("\n🧹 清除Cookie...")
    try:
        # 使用增强Cookie管理器清除所有Cookie文件
        enhanced_cookie_manager.clear_all_cookies()
        print("✅ 所有Cookie文件已清除，下次需要重新登录")
    except Exception as e:
        print(f"❌ 清除Cookie失败: {e}")


async def main():
    """主函数"""
    print_banner()
    
    while True:
        print_menu()
        
        try:
            choice = input("请输入选项 (0-5): ").strip()
            
            if choice == "0":
                print("\n👋 再见！")
                break
            elif choice == "1":
                await check_login_status()
            elif choice == "2":
                await qr_login()
            elif choice == "3":
                await show_cookies()
            elif choice == "4":
                clear_cookies()
            elif choice == "5":
                print_help()
            else:
                print("❌ 无效选项，请重新选择")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户取消操作，再见！")
            break
        except Exception as e:
            print(f"❌ 操作失败: {e}")
        
        # 等待用户按键继续
        if choice != "0":
            input("\n按回车键继续...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")