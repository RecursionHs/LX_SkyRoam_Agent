"""
Celery配置
"""

from celery import Celery
from app.core.config import settings
from app.core.logging_config import setup_logging
import platform

# 创建Celery应用
celery_app = Celery(
    "lx_skyroam_agent",
    broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND or settings.REDIS_URL,
    include=[
        "app.tasks.travel_plan_tasks",
        "app.tasks.data_collection_tasks",
        "app.tasks.background_tasks"
    ]
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟
    worker_prefetch_multiplier=settings.CELERY_PREFETCH_MULTIPLIER,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1小时
    broker_connection_retry_on_startup=True,
)

# 初始化日志（确保在Celery进程中使用统一日志级别）
setup_logging()

# Worker并发与池类型（支持通过环境变量覆盖）
if settings.CELERY_WORKER_POOL:
    celery_app.conf.worker_pool = settings.CELERY_WORKER_POOL
if settings.CELERY_WORKER_CONCURRENCY:
    celery_app.conf.worker_concurrency = settings.CELERY_WORKER_CONCURRENCY

# 平台默认：Windows使用solo池保证稳定，*nix按配置并发
if not settings.CELERY_WORKER_POOL:
    if platform.system().lower().startswith("win"):
        celery_app.conf.worker_pool = "solo"
        celery_app.conf.worker_concurrency = 1
        if "task_soft_time_limit" in celery_app.conf:
            del celery_app.conf["task_soft_time_limit"]
    else:
        celery_app.conf.worker_concurrency = getattr(settings, "MAX_CONCURRENT_TASKS", 10)

# 定时任务配置
celery_app.conf.beat_schedule = {
    "data-refresh-task": {
        "task": "app.tasks.background_tasks.data_refresh_task",
        "schedule": 86400.0,  # 每天执行一次
    },
    "cache-cleanup-task": {
        "task": "app.tasks.background_tasks.cache_cleanup_task", 
        "schedule": 3600.0,  # 每小时执行一次
    },
    "health-check-task": {
        "task": "app.tasks.background_tasks.health_check_task",
        "schedule": 600.0,  # 每10分钟执行一次
    },
}
