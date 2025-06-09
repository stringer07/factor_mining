#!/usr/bin/env python3
"""
Factor Mining System 启动脚本
"""

import sys
import os
import asyncio
import uvicorn
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    try:
        # 创建必要的目录
        os.makedirs("logs", exist_ok=True)
        
        # 获取配置
        settings = get_settings()
        
        logger.info(f"启动 {settings.app_name} v{settings.version}")
        logger.info(f"API服务地址: http://{settings.api.host}:{settings.api.port}")
        logger.info(f"API文档地址: http://{settings.api.host}:{settings.api.port}/docs")
        
        # 启动FastAPI服务
        uvicorn.run(
            "src.api.main:app",
            host=settings.api.host,
            port=settings.api.port,
            reload=settings.api.debug,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务...")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 