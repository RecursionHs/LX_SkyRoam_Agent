"""
数据库配置和连接管理
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import asyncio
from loguru import logger

from app.core.config import settings

# 每个事件循环维护独立的异步引擎与Session工厂，避免跨循环复用
_engines_by_loop = {}
_sessionmaker_by_loop = {}

def _current_loop_id():
    try:
        return id(asyncio.get_running_loop())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return id(loop)

def _get_async_engine_for_current_loop():
    loop_id = _current_loop_id()
    engine = _engines_by_loop.get(loop_id)
    if not engine:
        engine = create_async_engine(
            settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,
            pool_recycle=300
        )
        _engines_by_loop[loop_id] = engine
    return engine

# 创建同步数据库引擎（用于迁移等）
sync_engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_recycle=300
)

# 异步会话工厂（按当前事件循环）
def _get_sessionmaker_for_current_loop():
    loop_id = _current_loop_id()
    sm = _sessionmaker_by_loop.get(loop_id)
    if not sm:
        engine = _get_async_engine_for_current_loop()
        sm = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        _sessionmaker_by_loop[loop_id] = sm
    return sm

# 兼容导出：提供当前事件循环对应的引擎与Session工厂
def get_async_engine():
    return _get_async_engine_for_current_loop()

async_engine = _get_async_engine_for_current_loop()
AsyncSessionLocal = _get_sessionmaker_for_current_loop()

# 创建同步会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# 导入基础模型类
from app.models.base import Base

# 元数据
metadata = MetaData()


async def get_async_db():
    """获取异步数据库会话"""
    AsyncSessionFactory = _get_sessionmaker_for_current_loop()
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception as e:
            try:
                await session.rollback()
            except Exception:
                pass  # 忽略回滚错误
            logger.error(f"数据库会话错误: {e}")
            raise
        finally:
            try:
                await session.close()
            except Exception:
                pass  # 忽略关闭错误


def get_sync_db():
    """获取同步数据库会话"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"数据库会话错误: {e}")
        raise
    finally:
        db.close()


async def init_db():
    """初始化数据库"""
    try:
        # 首先尝试创建数据库（如果不存在）
        await create_database_if_not_exists()
        
        # 导入所有模型以确保它们被注册
        from app.models import user, travel_plan, destination, activity
        
        # 创建所有表
        engine = _get_async_engine_for_current_loop()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ 数据库表创建成功")
        
        # 创建默认用户数据
        await create_default_users()
        
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


async def create_database_if_not_exists():
    """如果数据库不存在则创建"""
    try:
        import asyncpg
        from urllib.parse import urlparse
        
        # 解析数据库URL
        parsed = urlparse(settings.DATABASE_URL)
        db_name = parsed.path[1:]  # 去掉开头的 '/'
        username = parsed.username
        password = parsed.password
        host = parsed.hostname
        port = parsed.port or 5432
        
        # 连接到默认的postgres数据库来创建目标数据库
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database='postgres'
        )
        
        try:
            # 检查数据库是否存在
            result = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            
            if not result:
                # 数据库不存在，创建它
                await conn.execute(f"CREATE DATABASE {db_name}")
                logger.info(f"✅ 数据库 '{db_name}' 创建成功")
            else:
                logger.info(f"✅ 数据库 '{db_name}' 已存在")
                
        finally:
            await conn.close()
        
    except Exception as e:
        logger.warning(f"⚠️ 数据库创建检查失败: {e}")
        # 如果创建失败，可能是权限问题或数据库已存在，继续执行


async def create_default_users():
    """创建默认用户数据"""
    try:
        from sqlalchemy import text
        
        engine = _get_async_engine_for_current_loop()
        async with engine.begin() as conn:
            # 检查用户表是否存在数据
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            
            # 检查是否存在ID=1的用户
            result = await conn.execute(text("SELECT id FROM users WHERE id = 1"))
            user_1_exists = result.fetchone()
            
            if not user_1_exists:
                # 创建ID=1的默认用户
                await conn.execute(text("""
                    INSERT INTO users (id, username, email, full_name, hashed_password, role, is_verified, is_active, created_at, updated_at) 
                    VALUES 
                    (1, 'admin', 'admin@lxai.com', '系统管理员', '$2b$12$w8GM49ePhxbCzT6qWNnvHOx/VHCh0MOmbFjUpFUG8Y4OTDmeM0Iq.', 'admin', true, true, NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                """))
                logger.info("✅ ID=1的默认用户创建成功")
            else:
                logger.info("✅ ID=1的用户已存在")
                
            # 检查是否存在ID=2的用户
            result = await conn.execute(text("SELECT id FROM users WHERE id = 2"))
            user_2_exists = result.fetchone()
            
            if not user_2_exists:
                # 创建ID=2的演示用户
                await conn.execute(text("""
                    INSERT INTO users (id, username, email, full_name, hashed_password, role, is_verified, is_active, created_at, updated_at) 
                    VALUES 
                    (2, 'demo_user', 'demo@lxai.com', '演示用户', '$2b$12$w8GM49ePhxbCzT6qWNnvHOx/VHCh0MOmbFjUpFUG8Y4OTDmeM0Iq.', 'user', true, true, NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                """))
                logger.info("✅ ID=2的演示用户创建成功")
            else:
                logger.info("✅ ID=2的用户已存在")
                
    except Exception as e:
        logger.warning(f"⚠️ 默认用户创建失败: {e}")
        # 如果创建失败，可能是权限问题或用户已存在，继续执行


async def close_db():
    """关闭数据库连接"""
    for engine in _engines_by_loop.values():
        await engine.dispose()
    sync_engine.dispose()
    logger.info("✅ 数据库连接已关闭")


# 便捷异步Session上下文管理器
class async_session:
    def __init__(self):
        self._session = None
        self._factory = _get_sessionmaker_for_current_loop()
    async def __aenter__(self):
        self._session = self._factory()
        return self._session
    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc:
                await self._session.rollback()
            else:
                await self._session.commit()
        finally:
            await self._session.close()
