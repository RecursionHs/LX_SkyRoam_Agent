"""
日志配置模块
支持控制台和文件输出，自动日志轮转，最大50M存储
"""

import os
import sys
import multiprocessing
from pathlib import Path
from loguru import logger
from app.core.config import settings


def setup_logging():
    """配置日志系统"""
    
    # 移除默认的控制台处理器
    logger.remove()
    
    # 确保日志目录存在
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 控制台日志配置
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 文件日志配置
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # 添加控制台处理器
    if settings.LOG_TO_CONSOLE:
        logger.add(
            sys.stdout,
            format=console_format,
            level=settings.LOG_LEVEL,
            colorize=True,
            backtrace=True,
            diagnose=True
        )
    
    # 添加应用日志文件处理器（自动轮转）
    if settings.LOG_TO_FILE:
        logger.add(
            settings.LOG_FILE,
            format=file_format,
            level=settings.LOG_LEVEL,
            rotation=settings.LOG_MAX_SIZE,
            retention=settings.LOG_RETENTION,
            compression=settings.LOG_COMPRESSION,
            backtrace=True,
            diagnose=True,
            encoding="utf-8"
        )
    
    # 添加错误日志文件处理器
    if settings.LOG_TO_FILE:
        logger.add(
            "logs/error.log",
            format=file_format,
            level="ERROR",
            rotation="5 MB",  # 错误日志每5MB轮转
            retention=3,  # 保留3个错误日志文件
            compression=settings.LOG_COMPRESSION,
            backtrace=True,
            diagnose=True,
            encoding="utf-8"
        )
    
    # 添加API访问日志处理器
    if settings.LOG_TO_FILE:
        logger.add(
            "logs/access.log",
            format=file_format,
            level="INFO",
            rotation="10 MB",
            retention=3,
            compression=settings.LOG_COMPRESSION,
            filter=lambda record: "API" in record["message"] or "访问" in record["message"],
            encoding="utf-8"
        )
    
    # 记录日志系统启动信息
    if multiprocessing.current_process().name == "MainProcess":
        logger.info("🚀 日志系统已启动")
        logger.info(f"📁 日志目录: {log_dir.absolute()}")
        logger.info(f"📊 日志级别: {settings.LOG_LEVEL}")
        logger.info(f"💾 最大存储: 50MB (应用日志) + 15MB (错误日志) + 30MB (访问日志)")
    
    return logger


def get_logger(name: str = None):
    """获取日志记录器"""
    if name:
        return logger.bind(name=name)
    return logger


# 日志装饰器
def log_function_call(func):
    """函数调用日志装饰器"""
    def wrapper(*args, **kwargs):
        logger.debug(f"🔧 调用函数: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"✅ 函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"❌ 函数 {func.__name__} 执行失败: {e}")
            raise
    return wrapper


def log_api_access(method: str, path: str, status_code: int, duration: float = None):
    """记录API访问日志"""
    duration_str = f" ({duration:.2f}ms)" if duration else ""
    logger.info(f"🌐 API访问: {method} {path} -> {status_code}{duration_str}")


def log_database_operation(operation: str, table: str, duration: float = None):
    """记录数据库操作日志"""
    duration_str = f" ({duration:.2f}ms)" if duration else ""
    logger.info(f"🗄️ 数据库操作: {operation} {table}{duration_str}")


def log_external_api_call(service: str, endpoint: str, status: str, duration: float = None):
    """记录外部API调用日志"""
    duration_str = f" ({duration:.2f}ms)" if duration else ""
    logger.info(f"🔗 外部API调用: {service} {endpoint} -> {status}{duration_str}")


def log_task_execution(task_name: str, status: str, duration: float = None):
    """记录任务执行日志"""
    duration_str = f" ({duration:.2f}s)" if duration else ""
    status_emoji = "✅" if status == "success" else "❌" if status == "error" else "⏳"
    logger.info(f"{status_emoji} 任务执行: {task_name} -> {status}{duration_str}")


# 导出主要函数
__all__ = [
    "setup_logging",
    "get_logger", 
    "log_function_call",
    "log_api_access",
    "log_database_operation",
    "log_external_api_call",
    "log_task_execution"
]
