"""
策略生成API路由
提供策略生成、freqtrade集成等功能
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def strategy_root():
    """策略生成模块根路径"""
    return {"message": "策略生成模块 - 开发中"}


@router.get("/generate")
async def generate_strategy():
    """生成策略"""
    return {"message": "策略生成 - 开发中"}


@router.get("/freqtrade")
async def freqtrade_integration():
    """freqtrade集成"""
    return {"message": "freqtrade集成 - 开发中"} 