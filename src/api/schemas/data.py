"""
数据相关的API模型
定义请求和响应的数据结构
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class OHLCVRequest(BaseModel):
    """OHLCV数据请求模型"""
    symbol: str = Field(..., description="交易对符号，如 BTC/USDT")
    timeframe: str = Field(..., description="时间周期，如 1h")
    since: Optional[datetime] = Field(None, description="开始时间")
    limit: Optional[int] = Field(1000, description="数据条数限制")


class OHLCVData(BaseModel):
    """OHLCV数据项"""
    timestamp: str = Field(..., description="时间戳")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(..., description="成交量")


class OHLCVResponse(BaseModel):
    """OHLCV数据响应模型"""
    symbol: str = Field(..., description="交易对符号")
    timeframe: str = Field(..., description="时间周期")
    exchange: str = Field(..., description="交易所")
    data: List[OHLCVData] = Field(..., description="OHLCV数据列表")
    count: int = Field(..., description="数据条数")


class SymbolsResponse(BaseModel):
    """交易对列表响应模型"""
    exchange: str = Field(..., description="交易所名称")
    symbols: List[str] = Field(..., description="交易对列表")
    count: int = Field(..., description="交易对数量")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    name: str = Field(..., description="服务名称")
    connected: bool = Field(..., description="是否连接")
    symbols_count: int = Field(..., description="可用交易对数量")
    timestamp: datetime = Field(..., description="检查时间")
    status: str = Field(..., description="状态")
    error: Optional[str] = Field(None, description="错误信息")


class TickerResponse(BaseModel):
    """行情数据响应模型"""
    symbol: str = Field(..., description="交易对符号")
    exchange: str = Field(..., description="交易所")
    price: Optional[float] = Field(None, description="当前价格")
    change: Optional[float] = Field(None, description="24h变化")
    percentage: Optional[float] = Field(None, description="24h变化百分比")
    volume: Optional[float] = Field(None, description="24h成交量")
    high: Optional[float] = Field(None, description="24h最高价")
    low: Optional[float] = Field(None, description="24h最低价")
    timestamp: Optional[int] = Field(None, description="时间戳")


class OrderBookItem(BaseModel):
    """订单簿项目"""
    price: float = Field(..., description="价格")
    amount: float = Field(..., description="数量")


class OrderBookResponse(BaseModel):
    """订单簿响应模型"""
    symbol: str = Field(..., description="交易对符号")
    exchange: str = Field(..., description="交易所")
    timestamp: Optional[int] = Field(None, description="时间戳")
    bids: List[List[float]] = Field(..., description="买单列表")
    asks: List[List[float]] = Field(..., description="卖单列表")
    bid: Optional[float] = Field(None, description="最高买价")
    ask: Optional[float] = Field(None, description="最低卖价")


class DataCollectionRequest(BaseModel):
    """数据采集请求模型"""
    symbols: List[str] = Field(..., description="交易对列表")
    timeframes: List[str] = Field(..., description="时间周期列表")
    exchanges: Optional[List[str]] = Field(None, description="交易所列表")
    
    
class DataCollectionResponse(BaseModel):
    """数据采集响应模型"""
    status: str = Field(..., description="状态")
    symbols: List[str] = Field(..., description="交易对列表")
    timeframes: List[str] = Field(..., description="时间周期列表")
    exchanges: List[str] = Field(..., description="交易所列表")
    message: str = Field(..., description="响应消息") 