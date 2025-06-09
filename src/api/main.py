"""
Factor Mining System API
FastAPI主应用程序
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from src.config.settings import get_settings
from src.utils.logger import get_logger
from .routers import data, factors, evaluation, strategy, monitoring

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期管理"""
    # 启动时执行
    logger.info("启动 Factor Mining System API")
    
    try:
        # 初始化数据库连接等
        logger.info("初始化系统组件...")
        
        yield
        
    finally:
        # 关闭时执行
        logger.info("关闭 Factor Mining System API")


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description=settings.description,
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(data.router, prefix="/api/v1/data", tags=["数据管理"])
    app.include_router(factors.router, prefix="/api/v1/factors", tags=["因子计算"])
    app.include_router(evaluation.router, prefix="/api/v1/evaluation", tags=["因子评估"])
    app.include_router(strategy.router, prefix="/api/v1/strategy", tags=["策略生成"])
    app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["监控预警"])
    
    # 全局异常处理
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        logger.error(f"HTTP异常: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"未处理异常: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"error": "内部服务器错误", "status_code": 500}
        )
    
    # 健康检查
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.version
        }
    
    # 根路径
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "message": f"欢迎使用 {settings.app_name}",
            "version": settings.version,
            "docs": "/docs"
        }
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.debug,
        log_level="info"
    ) 