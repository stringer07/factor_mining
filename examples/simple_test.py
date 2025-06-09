#!/usr/bin/env python3
"""
简单的因子计算测试示例
演示如何使用因子挖掘系统
"""

import sys
import asyncio
import pandas as pd
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.collectors.exchange import MultiExchangeCollector
from src.factors.base.factor import factor_registry
from src.factors.technical.momentum import *  # 触发因子注册
from src.factors.technical.volatility import *  # 触发因子注册
from src.factors.technical.reversal import *  # 触发因子注册


def log_info(message: str):
    """简单的日志函数"""
    print(f"INFO: {message}")


def log_error(message: str):
    """简单的错误日志函数"""
    print(f"ERROR: {message}")


def log_warning(message: str):
    """简单的警告日志函数"""
    print(f"WARNING: {message}")


async def test_data_collection():
    """测试数据采集功能"""
    log_info("=== 测试数据采集功能 ===")
    
    # 创建多交易所采集器
    collector = MultiExchangeCollector()
    
    try:
        # 健康检查
        health = await collector.health_check_all()
        log_info(f"交易所健康状态: {health}")
        
        # 获取OHLCV数据
        symbol = "BTC/USDT"
        timeframe = "1h"
        limit = 100
        
        log_info(f"获取 {symbol} {timeframe} 数据...")
        df = await collector.get_ohlcv_from_best_source(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit
        )
        
        if not df.empty:
            log_info(f"成功获取 {len(df)} 条数据")
            log_info(f"数据时间范围: {df.index[0]} 到 {df.index[-1]}")
            log_info(f"最新价格: {df['close'].iloc[-1]}")
        else:
            log_warning("未获取到数据")
            
        return df
        
    except Exception as e:
        log_error(f"数据采集测试失败: {e}")
        return pd.DataFrame()
    
    finally:
        await collector.disconnect_all()


def test_factor_calculation(data: pd.DataFrame):
    """测试因子计算功能"""
    log_info("=== 测试因子计算功能 ===")
    
    if data.empty:
        log_warning("没有数据，跳过因子计算测试")
        return
    
    # 获取所有注册的因子
    all_factors = factor_registry.list_factors()
    log_info(f"已注册的因子: {all_factors}")
    
    # 测试几个因子
    test_factors = ["momentum_20", "rsi_momentum_14", "macd_momentum_12_26_9"]
    
    for factor_name in test_factors:
        if factor_name in all_factors:
            try:
                factor = factor_registry.get_factor(factor_name)
                log_info(f"\n计算因子: {factor_name}")
                log_info(f"因子描述: {factor.metadata.description}")
                
                # 计算因子值
                factor_values = factor.calculate_with_validation(data)
                
                if not factor_values.empty:
                    log_info(f"因子值数量: {len(factor_values)}")
                    log_info(f"因子值统计:")
                    log_info(f"  均值: {factor_values.mean():.6f}")
                    log_info(f"  标准差: {factor_values.std():.6f}")
                    log_info(f"  最小值: {factor_values.min():.6f}")
                    log_info(f"  最大值: {factor_values.max():.6f}")
                    log_info(f"  最新值: {factor_values.iloc[-1]:.6f}")
                else:
                    log_warning(f"因子 {factor_name} 计算结果为空")
                    
            except Exception as e:
                log_error(f"计算因子 {factor_name} 失败: {e}")


def test_factor_registry():
    """测试因子注册表功能"""
    log_info("=== 测试因子注册表功能 ===")
    
    # 获取因子分类
    all_factors = factor_registry.list_factors()
    technical_factors = factor_registry.list_factors("technical")
    
    log_info(f"总因子数量: {len(all_factors)}")
    log_info(f"技术因子数量: {len(technical_factors)}")
    
    # 显示因子信息
    for factor_name in all_factors[:5]:  # 只显示前5个
        factor = factor_registry.get_factor(factor_name)
        if factor:
            info = factor.get_factor_info()
            log_info(f"因子: {info['name']} - {info['description']}")


async def main():
    """主测试函数"""
    log_info("开始因子挖掘系统测试")
    
    try:
        # 测试因子注册表
        test_factor_registry()
        
        # 测试数据采集
        data = await test_data_collection()
        
        # 测试因子计算
        test_factor_calculation(data)
        
        log_info("测试完成！")
        
    except Exception as e:
        log_error(f"测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 