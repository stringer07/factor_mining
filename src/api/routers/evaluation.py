"""
因子评估API路由
提供因子IC分析、回测等功能
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evaluation.metrics.ic_analysis import ICAnalyzer
from src.evaluation.metrics.performance import PerformanceAnalyzer
from src.evaluation.backtesting.engine import BacktestEngine, BacktestConfig
from src.data.collectors.exchange import MultiExchangeCollector
from src.factors.base.factor import factor_registry
from src.utils.logger import get_logger

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
logger = get_logger(__name__)

# 创建全局实例
ic_analyzer = ICAnalyzer()
performance_analyzer = PerformanceAnalyzer()
data_collector = MultiExchangeCollector()


class ICAnalysisRequest(BaseModel):
    """IC分析请求"""
    factor_name: str
    symbol: str = "BTC/USDT"
    periods: List[int] = [1, 5, 10, 20]
    days: int = 90


class BacktestRequest(BaseModel):
    """回测请求"""
    factor_name: str
    symbol: str = "BTC/USDT"
    days: int = 90
    initial_capital: float = 100000.0
    commission_rate: float = 0.001


class QuantileBacktestRequest(BaseModel):
    """分层回测请求"""
    factor_name: str
    symbol: str = "BTC/USDT"
    days: int = 90
    quantiles: int = 5
    long_short: bool = True


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now()}


@router.post("/ic_analysis")
async def analyze_factor_ic(request: ICAnalysisRequest):
    """
    分析因子IC
    
    计算指定因子的信息系数，评估其预测能力
    """
    try:
        # 获取因子
        factor = factor_registry.get_factor(request.factor_name)
        if not factor:
            raise HTTPException(status_code=404, detail=f"因子 '{request.factor_name}' 不存在")
        
        # 获取历史数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=request.days)
        
        price_data = await data_collector.get_ohlcv(
            symbol=request.symbol,
            timeframe="1d",
            since=start_date,
            limit=request.days
        )
        
        if price_data.empty:
            raise HTTPException(status_code=404, detail="无法获取价格数据")
        
        # 计算因子值
        factor_values = factor.calculate(price_data)
        
        # 进行IC分析
        ic_results = ic_analyzer.comprehensive_analysis(
            factor_values=factor_values,
            price_data=price_data,
            periods=request.periods
        )
        
        # 计算基础统计
        factor_stats = {
            'mean': float(factor_values.mean()),
            'std': float(factor_values.std()),
            'min': float(factor_values.min()),
            'max': float(factor_values.max()),
            'count': int(factor_values.count())
        }
        
        return {
            "factor_name": request.factor_name,
            "symbol": request.symbol,
            "analysis_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": request.days
            },
            "factor_stats": factor_stats,
            "ic_analysis": ic_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"IC分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"IC分析失败: {str(e)}")


@router.post("/backtest/factor")
async def backtest_factor(request: BacktestRequest):
    """
    单因子回测
    
    使用指定因子进行历史回测，评估策略表现
    """
    try:
        # 获取因子
        factor = factor_registry.get_factor(request.factor_name)
        if not factor:
            raise HTTPException(status_code=404, detail=f"因子 '{request.factor_name}' 不存在")
        
        # 获取历史数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=request.days)
        
        price_data = await data_collector.get_ohlcv(
            symbol=request.symbol,
            timeframe="1d",
            since=start_date,
            limit=request.days
        )
        
        if price_data.empty:
            raise HTTPException(status_code=404, detail="无法获取价格数据")
        
        # 计算因子值
        factor_values = factor.calculate(price_data)
        
        # 创建回测配置
        config = BacktestConfig(
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate
        )
        
        # 运行回测
        backtest_engine = BacktestEngine(config)
        backtest_results = backtest_engine.run_factor_backtest(
            factor_values=factor_values,
            price_data=price_data
        )
        
        if "error" in backtest_results:
            raise HTTPException(status_code=400, detail=backtest_results["error"])
        
        # 转换时间序列为可序列化格式
        if 'portfolio_value' in backtest_results:
            portfolio_value = backtest_results['portfolio_value']
            backtest_results['portfolio_value'] = {
                'timestamps': [ts.isoformat() for ts in portfolio_value.index],
                'values': portfolio_value.tolist()
            }
        
        if 'returns' in backtest_results:
            returns = backtest_results['returns']
            backtest_results['returns'] = {
                'timestamps': [ts.isoformat() for ts in returns.index],
                'values': returns.tolist()
            }
        
        # 处理交易记录
        if 'trades' in backtest_results:
            trades = backtest_results['trades']
            backtest_results['trades'] = [
                {
                    'symbol': trade.symbol,
                    'order_type': trade.order_type.value,
                    'size': trade.size,
                    'price': trade.price,
                    'timestamp': trade.timestamp.isoformat(),
                    'commission': trade.commission
                }
                for trade in trades
            ]
        
        return {
            "factor_name": request.factor_name,
            "symbol": request.symbol,
            "backtest_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": request.days
            },
            "config": {
                "initial_capital": request.initial_capital,
                "commission_rate": request.commission_rate
            },
            "results": backtest_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"因子回测失败: {e}")
        raise HTTPException(status_code=500, detail=f"因子回测失败: {str(e)}")


@router.post("/backtest/quantile")
async def backtest_quantile(request: QuantileBacktestRequest):
    """
    分层回测
    
    将因子分层，分析不同层级的收益表现，构建多空组合
    """
    try:
        # 获取因子
        factor = factor_registry.get_factor(request.factor_name)
        if not factor:
            raise HTTPException(status_code=404, detail=f"因子 '{request.factor_name}' 不存在")
        
        # 获取历史数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=request.days)
        
        price_data = await data_collector.get_ohlcv(
            symbol=request.symbol,
            timeframe="1d",
            since=start_date,
            limit=request.days
        )
        
        if price_data.empty:
            raise HTTPException(status_code=404, detail="无法获取价格数据")
        
        # 计算因子值
        factor_values = factor.calculate(price_data)
        
        # 运行分层回测
        backtest_engine = BacktestEngine()
        quantile_results = backtest_engine.run_quantile_backtest(
            factor_values=factor_values,
            price_data=price_data,
            quantiles=request.quantiles,
            long_short=request.long_short
        )
        
        if "error" in quantile_results:
            raise HTTPException(status_code=400, detail=quantile_results["error"])
        
        return {
            "factor_name": request.factor_name,
            "symbol": request.symbol,
            "backtest_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": request.days
            },
            "config": {
                "quantiles": request.quantiles,
                "long_short": request.long_short
            },
            "results": quantile_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"分层回测失败: {e}")
        raise HTTPException(status_code=500, detail=f"分层回测失败: {str(e)}")


@router.get("/performance/metrics")
async def get_performance_metrics(
    returns: str = Query(..., description="收益率序列，逗号分隔"),
    risk_free_rate: float = Query(0.02, description="无风险收益率"),
    periods_per_year: int = Query(252, description="年化周期数")
):
    """
    计算性能指标
    
    根据提供的收益率序列计算各种性能指标
    """
    try:
        # 解析收益率数据
        returns_list = [float(x.strip()) for x in returns.split(',') if x.strip()]
        if len(returns_list) == 0:
            raise HTTPException(status_code=400, detail="收益率数据为空")
        
        returns_series = pd.Series(returns_list)
        
        # 计算性能指标
        performance_stats = performance_analyzer.comprehensive_analysis(
            returns=returns_series,
            risk_free_rate=risk_free_rate,
            periods_per_year=periods_per_year
        )
        
        return {
            "performance_metrics": performance_stats,
            "input_stats": {
                "returns_count": len(returns_list),
                "risk_free_rate": risk_free_rate,
                "periods_per_year": periods_per_year
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"收益率数据格式错误: {str(e)}")
    except Exception as e:
        logger.error(f"性能指标计算失败: {e}")
        raise HTTPException(status_code=500, detail=f"性能指标计算失败: {str(e)}")


@router.get("/factors/ranking")
async def rank_factors(
    symbol: str = Query("BTC/USDT", description="交易对"),
    days: int = Query(90, description="分析天数"),
    metric: str = Query("ic", description="排序指标 (ic, sharpe, calmar)")
):
    """
    因子排名
    
    根据指定指标对所有因子进行排名
    """
    try:
        # 获取历史数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        price_data = await data_collector.get_ohlcv(
            symbol=symbol,
            timeframe="1d",
            since=start_date,
            limit=days
        )
        
        if price_data.empty:
            raise HTTPException(status_code=404, detail="无法获取价格数据")
        
        # 获取所有因子
        all_factors = factor_registry.list_factors()
        
        factor_scores = []
        
        for factor_name in all_factors:
            try:
                factor = factor_registry.get_factor(factor_name)
                if not factor:
                    continue
                
                # 计算因子值
                factor_values = factor.calculate(price_data)
                
                if factor_values.empty or factor_values.isna().all():
                    continue
                
                # 根据选择的指标计算得分
                if metric == "ic":
                    # 计算IC
                    returns = price_data['close'].pct_change()
                    score = ic_analyzer.calculate_ic(factor_values, returns.shift(-1))
                    
                elif metric == "sharpe":
                    # 简单策略回测计算夏普比率
                    config = BacktestConfig(initial_capital=100000.0)
                    backtest_engine = BacktestEngine(config)
                    results = backtest_engine.run_factor_backtest(factor_values, price_data)
                    
                    if "error" not in results and "performance_stats" in results:
                        score = results["performance_stats"].get("sharpe_ratio", np.nan)
                    else:
                        score = np.nan
                        
                elif metric == "calmar":
                    # 简单策略回测计算卡玛比率
                    config = BacktestConfig(initial_capital=100000.0)
                    backtest_engine = BacktestEngine(config)
                    results = backtest_engine.run_factor_backtest(factor_values, price_data)
                    
                    if "error" not in results and "performance_stats" in results:
                        score = results["performance_stats"].get("calmar_ratio", np.nan)
                    else:
                        score = np.nan
                else:
                    raise HTTPException(status_code=400, detail=f"不支持的排序指标: {metric}")
                
                if not np.isnan(score):
                    factor_scores.append({
                        "factor_name": factor_name,
                        "score": float(score),
                        "metadata": factor.metadata.dict()
                    })
                    
            except Exception as e:
                logger.warning(f"评估因子 {factor_name} 失败: {e}")
                continue
        
        # 按得分排序
        factor_scores.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "ranking_metric": metric,
            "symbol": symbol,
            "analysis_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "factor_ranking": factor_scores,
            "total_factors": len(factor_scores),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"因子排名失败: {e}")
        raise HTTPException(status_code=500, detail=f"因子排名失败: {str(e)}") 