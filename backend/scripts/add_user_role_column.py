"""
为现有数据库的 users 表添加 role 列，并设置默认值与初始管理员角色。

使用：
    python -m backend.scripts.add_user_role_column

说明：
- 依赖后端的同步数据库引擎配置（PostgreSQL）。
- 如果列已存在，使用 IF NOT EXISTS 保持幂等。
"""
import asyncio
import os
import sys
from sqlalchemy import text
from loguru import logger

backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_root not in sys.path:
    sys.path.append(backend_root)
    
from app.core.database import sync_engine


def main():
    with sync_engine.begin() as conn:
        # 添加 role 列，默认值为 'user'
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user'"
        ))
        # 将 ID=1 的默认管理员设置为 admin 角色
        conn.execute(text(
            "UPDATE users SET role = 'admin' WHERE id = 1"
        ))
    print("✅ 已为 users 表添加 role 列（如需），并设置默认管理员角色")


if __name__ == "__main__":
    main()