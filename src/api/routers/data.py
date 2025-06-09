"""
数据管理API路由
提供数据采集、查询、管理等功能
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

from src.data.collectors.exchange import MultiExchangeCollector
from src.utils.logger import get_logger
from ..schemas.data import (
    OHLCVRequest, OHLCVResponse, 
    SymbolsResponse, HealthResponse
)

router = APIRouter()
logger = get_logger(__name__)

# 全局数据采集器实例
collector = MultiExchangeCollector()


@router.get("/exchanges/health", response_model=Dict[str, HealthResponse])
async def get_exchanges_health():
    """获取所有交易所健康状态"""
    try:
        health_results = await collector.health_check_all()
        return health_results
    except Exception as e:
        logger.error(f"获取交易所健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols", response_model=SymbolsResponse)
async def get_symbols(exchange: str = Query("binance", description="交易所名称")):
    """获取指定交易所的可用交易对"""
    try:
        if exchange not in collector.collectors:
            raise HTTPException(status_code=400, detail=f"不支持的交易所: {exchange}")
        
        symbols = await collector.collectors[exchange].get_symbols()
        
        return SymbolsResponse(
            exchange=exchange,
            symbols=symbols,
            count=len(symbols)
        )
    
    except Exception as e:
        logger.error(f"获取交易对失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ohlcv", response_model=OHLCVResponse)
async def get_ohlcv_data(request: OHLCVRequest):
    """获取OHLCV数据"""
    try:
        # 参数验证
        if not request.symbol or "/" not in request.symbol:
            raise HTTPException(status_code=400, detail="无效的交易对格式")
        
        if request.timeframe not in ["1m", "5m", "15m", "1h", "4h", "1d"]:
            raise HTTPException(status_code=400, detail="不支持的时间周期")
        
        # 获取数据
        df = await collector.get_ohlcv_from_best_source(
            symbol=request.symbol,
            timeframe=request.timeframe,
            since=request.since,
            limit=request.limit
        )
        
        if df.empty:
            raise HTTPException(status_code=404, detail="未找到数据")
        
        # 转换为响应格式
        data_records = []
        for timestamp, row in df.iterrows():
            data_records.append({
                "timestamp": timestamp.isoformat(),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": float(row['volume'])
            })
        
        return OHLCVResponse(
            symbol=request.symbol,
            timeframe=request.timeframe,
            exchange=df['exchange'].iloc[0] if 'exchange' in df.columns else "unknown",
            data=data_records,
            count=len(data_records)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取OHLCV数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticker/{symbol}")
async def get_ticker(
    symbol: str,
    exchange: str = Query("binance", description="交易所名称")
):
    """获取实时行情数据"""
    try:
        if exchange not in collector.collectors:
            raise HTTPException(status_code=400, detail=f"不支持的交易所: {exchange}")
        
        ticker = await collector.collectors[exchange].get_ticker(symbol)
        
        if not ticker:
            raise HTTPException(status_code=404, detail="未找到行情数据")
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "ticker": ticker
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取行情数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{symbol}")
async def get_24h_stats(
    symbol: str,
    exchange: str = Query("binance", description="交易所名称")
):
    """获取24小时统计数据"""
    try:
        if exchange not in collector.collectors:
            raise HTTPException(status_code=400, detail=f"不支持的交易所: {exchange}")
        
        stats = await collector.collectors[exchange].get_24h_stats(symbol)
        
        if not stats:
            raise HTTPException(status_code=404, detail="未找到统计数据")
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "stats": stats
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orderbook/{symbol}")
async def get_orderbook(
    symbol: str,
    exchange: str = Query("binance", description="交易所名称"),
    limit: int = Query(50, description="订单簿深度")
):
    """获取订单簿数据"""
    try:
        if exchange not in collector.collectors:
            raise HTTPException(status_code=400, detail=f"不支持的交易所: {exchange}")
        
        orderbook = await collector.collectors[exchange].get_orderbook(symbol, limit)
        
        if not orderbook:
            raise HTTPException(status_code=404, detail="未找到订单簿数据")
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "orderbook": orderbook
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取订单簿失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect/start")
async def start_data_collection(
    symbols: List[str],
    timeframes: List[str],
    exchanges: List[str] = None
):
    """启动数据采集任务"""
    try:
        if exchanges is None:
            exchanges = list(collector.collectors.keys())
        
        # 验证参数
        for exchange in exchanges:
            if exchange not in collector.collectors:
                raise HTTPException(status_code=400, detail=f"不支持的交易所: {exchange}")
        
        # 这里应该启动后台任务进行数据采集
        # 暂时返回成功响应
        logger.info(f"启动数据采集: symbols={symbols}, timeframes={timeframes}, exchanges={exchanges}")
        
        return {
            "status": "started",
            "symbols": symbols,
            "timeframes": timeframes,
            "exchanges": exchanges,
            "message": "数据采集任务已启动"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动数据采集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect/stop")
async def stop_data_collection():
    """停止数据采集任务"""
    try:
        # 这里应该停止后台采集任务
        logger.info("停止数据采集任务")
        
        return {
            "status": "stopped",
            "message": "数据采集任务已停止"
        }
    
    except Exception as e:
        logger.error(f"停止数据采集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 