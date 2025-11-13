"""
Redis配置和连接管理
"""

import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from loguru import logger
import asyncio

from app.core.config import settings

# Redis连接池
redis_pool: ConnectionPool = None
redis_client: redis.Redis = None
_redis_loop_id: int = None


async def init_redis():
    """初始化Redis连接"""
    global redis_pool, redis_client
    
    try:
        # 创建连接池（增加连接与读写超时，避免阻塞）
        redis_pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD,
            max_connections=20,
            retry_on_timeout=True,
            socket_connect_timeout=5,  # 连接超时（秒）
            socket_timeout=5,          # 读写操作超时（秒）
            health_check_interval=15   # 定期健康检查，避免长连接失效
        )
        
        # 创建Redis客户端
        redis_client = redis.Redis(connection_pool=redis_pool)
        # 绑定当前事件循环ID
        global _redis_loop_id
        _redis_loop_id = id(asyncio.get_running_loop())
        
        logger.info("✅ Redis连接池创建成功")
        # 测试连接（添加超时保护）
        await redis_client.ping()
        try:
            await asyncio.wait_for(redis_client.ping(), timeout=3)
        except asyncio.TimeoutError:
            raise TimeoutError("Redis ping 超时")
        logger.info("✅ Redis连接成功")
        
    except Exception as e:
        logger.error(f"❌ Redis连接失败: {e}")
        raise


async def get_redis() -> redis.Redis:
    """获取Redis客户端"""
    global _redis_loop_id
    current_loop_id = id(asyncio.get_running_loop())
    if redis_client is None or _redis_loop_id != current_loop_id:
        # 事件循环不一致或未初始化，重新初始化
        try:
            await close_redis()
        except Exception:
            pass
        await init_redis()
    return redis_client


async def close_redis():
    """关闭Redis连接"""
    global redis_client, redis_pool
    
    if redis_client:
        await redis_client.close()
        redis_client = None
    
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None
    
    logger.info("✅ Redis连接已关闭")


# 缓存装饰器
def cache_key(prefix: str, *args, **kwargs):
    """生成缓存键"""
    key_parts = [prefix]
    
    # 添加位置参数
    for arg in args:
        key_parts.append(str(arg))
    
    # 添加关键字参数
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")
    
    return ":".join(key_parts)


async def get_cache(key: str):
    """获取缓存"""
    try:
        client = await get_redis()
        value = await client.get(key)
        if value:
            import json
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"获取缓存失败: {e}")
        return None


async def set_cache(key: str, value, ttl: int = None):
    """设置缓存"""
    try:
        client = await get_redis()
        import json
        json_value = json.dumps(value, ensure_ascii=False)
        
        if ttl is None:
            ttl = settings.CACHE_TTL
        
        await client.setex(key, ttl, json_value)
        return True
    except Exception as e:
        logger.error(f"设置缓存失败: {e}")
        return False


async def delete_cache(key: str):
    """删除缓存"""
    try:
        client = await get_redis()
        await client.delete(key)
        return True
    except Exception as e:
        logger.error(f"删除缓存失败: {e}")
        return False


async def clear_cache_pattern(pattern: str):
    """清除匹配模式的缓存"""
    try:
        client = await get_redis()
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
        return len(keys)
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        return 0


def clear_cache_pattern_sync(pattern: str):
    """清除匹配模式的缓存 (同步版本，用于Celery任务)"""
    import asyncio
    try:
        # 在同步环境中运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(clear_cache_pattern(pattern))
            return result
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"清除缓存失败 (同步版本): {e}")
        return 0
