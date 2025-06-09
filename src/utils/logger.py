"""
日志管理模块
提供统一的日志配置和管理功能
"""

import sys
from pathlib import Path
from loguru import logger
from src.config.settings import get_settings


class Logger:
    """日志管理器"""
    
    def __init__(self):
        self.settings = get_settings().logging
        self._setup_logger()
    
    def _setup_logger(self):
        """配置日志"""
        # 移除默认处理器
        logger.remove()
        
        # 控制台输出
        logger.add(
            sys.stderr,
            format=self.settings.format,
            level=self.settings.level,
            colorize=True
        )
        
        # 文件输出
        log_path = Path(self.settings.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            self.settings.file_path,
            format=self.settings.format,
            level=self.settings.level,
            rotation=self.settings.rotation,
            retention=self.settings.retention,
            compression="zip"
        )
    
    def get_logger(self, name: str = None):
        """获取指定名称的日志器"""
        if name:
            return logger.bind(name=name)
        return logger


# 全局日志器实例
_logger_manager = Logger()
log = _logger_manager.get_logger()


def get_logger(name: str = None):
    """获取日志器"""
    return _logger_manager.get_logger(name) 