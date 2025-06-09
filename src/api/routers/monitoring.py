"""
监控预警API路由
提供系统监控、预警等功能
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def monitoring_root():
    """监控预警模块根路径"""
    return {"message": "监控预警模块 - 开发中"}


@router.get("/system-status")
async def system_status():
    """系统状态"""
    return {"message": "系统状态监控 - 开发中"}


@router.get("/alerts")
async def alerts():
    """预警信息"""
    return {"message": "预警信息 - 开发中"} 