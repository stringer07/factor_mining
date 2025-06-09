"""
因子评估演示脚本
展示IC分析、回测、性能评估等功能
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation.metrics.ic_analysis import ICAnalyzer
from src.evaluation.metrics.performance import PerformanceAnalyzer
from src.evaluation.backtesting.engine import BacktestEngine, BacktestConfig
from src.data.collectors.exchange import MultiExchangeCollector
from src.factors.base.factor import factor_registry
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def demo_ic_analysis():
    """演示IC分析功能"""
    print("\n" + "="*50)
    print("IC分析演示")
    print("="*50)
    
    try:
        # 创建IC分析器
        ic_analyzer = ICAnalyzer()
        
        # 获取数据收集器
        data_collector = MultiExchangeCollector()
        
        # 获取历史数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        print(f"获取 BTC/USDT 历史数据 ({start_date.date()} 到 {end_date.date()})")
        price_data = await data_collector.get_ohlcv(
            symbol="BTC/USDT",
            timeframe="1d",
            since=start_date,
            limit=90
        )
        
        if price_data.empty:
            print("❌ 无法获取价格数据")
            return
        
        print(f"✅ 获取到 {len(price_data)} 条数据")
        
        # 测试多个因子的IC分析
        test_factors = [
            "momentum_5",
            "momentum_20", 
            "rsi_momentum_14",
            "volatility_20",
            "reversal_5"
        ]
        
        print(f"\n分析 {len(test_factors)} 个因子的IC表现:")
        
        ic_results = {}
        
        for factor_name in test_factors:
            factor = factor_registry.get_factor(factor_name)
            if not factor:
                print(f"⚠️  因子 {factor_name} 不存在")
                continue
            
            # 计算因子值
            factor_values = factor.calculate(price_data)
            
            if factor_values.empty or factor_values.isna().all():
                print(f"⚠️  因子 {factor_name} 计算失败")
                continue
            
            # 进行IC分析
            comprehensive_results = ic_analyzer.comprehensive_analysis(
                factor_values=factor_values,
                price_data=price_data,
                periods=[1, 5, 10]
            )
            
            ic_results[factor_name] = comprehensive_results
            
            # 显示基础IC统计
            basic_stats = comprehensive_results.get('basic_ic_stats', {})
            if basic_stats:
                period_1 = basic_stats.get('period_1', {})
                ic_value = period_1.get('ic', 0)
                ic_ir = period_1.get('ic_ir', 0)
                print(f"  {factor_name:<20} IC: {ic_value:>8.4f}  IC_IR: {ic_ir:>8.4f}")
        
        print(f"\n✅ IC分析完成，共分析了 {len(ic_results)} 个因子")
        
        return ic_results
        
    except Exception as e:
        print(f"❌ IC分析失败: {e}")
        return None


async def demo_factor_backtest():
    """演示因子回测功能"""
    print("\n" + "="*50)
    print("因子回测演示")
    print("="*50)
    
    try:
        # 获取数据收集器
        data_collector = MultiExchangeCollector()
        
        # 获取历史数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=120)
        
        print(f"获取 BTC/USDT 历史数据用于回测 ({start_date.date()} 到 {end_date.date()})")
        price_data = await data_collector.get_ohlcv(
            symbol="BTC/USDT",
            timeframe="1d",
            since=start_date,
            limit=120
        )
        
        if price_data.empty:
            print("❌ 无法获取价格数据")
            return
        
        print(f"✅ 获取到 {len(price_data)} 条数据")
        
        # 选择几个因子进行回测对比
        test_factors = ["momentum_20", "rsi_momentum_14", "volatility_20"]
        
        # 配置回测参数
        config = BacktestConfig(
            initial_capital=100000.0,
            commission_rate=0.001,
            slippage_rate=0.0005
        )
        
        print(f"\n开始回测 {len(test_factors)} 个因子:")
        print(f"初始资金: ${config.initial_capital:,.0f}")
        print(f"手续费率: {config.commission_rate:.1%}")
        
        backtest_results = {}
        
        for factor_name in test_factors:
            factor = factor_registry.get_factor(factor_name)
            if not factor:
                print(f"⚠️  因子 {factor_name} 不存在")
                continue
            
            # 计算因子值
            factor_values = factor.calculate(price_data)
            
            if factor_values.empty or factor_values.isna().all():
                print(f"⚠️  因子 {factor_name} 计算失败")
                continue
            
            # 运行回测
            backtest_engine = BacktestEngine(config)
            results = backtest_engine.run_factor_backtest(
                factor_values=factor_values,
                price_data=price_data
            )
            
            if "error" in results:
                print(f"⚠️  因子 {factor_name} 回测失败: {results['error']}")
                continue
            
            backtest_results[factor_name] = results
            
            # 显示回测结果
            performance_stats = results.get('performance_stats', {})
            final_value = results.get('final_value', 0)
            total_return = results.get('total_return', 0)
            
            sharpe = performance_stats.get('sharpe_ratio', 0)
            max_dd = performance_stats.get('max_drawdown', 0)
            win_rate = performance_stats.get('win_rate', 0)
            
            print(f"  {factor_name:<20} 总收益: {total_return:>8.2%}  夏普: {sharpe:>6.2f}  最大回撤: {max_dd:>7.2%}  胜率: {win_rate:>6.2%}")
        
        print(f"\n✅ 因子回测完成，共回测了 {len(backtest_results)} 个因子")
        
        return backtest_results
        
    except Exception as e:
        print(f"❌ 因子回测失败: {e}")
        return None


async def demo_quantile_backtest():
    """演示分层回测功能"""
    print("\n" + "="*50)
    print("分层回测演示")
    print("="*50)
    
    try:
        # 获取数据收集器
        data_collector = MultiExchangeCollector()
        
        # 获取历史数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=120)
        
        print(f"获取 BTC/USDT 历史数据用于分层回测")
        price_data = await data_collector.get_ohlcv(
            symbol="BTC/USDT",
            timeframe="1d",
            since=start_date,
            limit=120
        )
        
        if price_data.empty:
            print("❌ 无法获取价格数据")
            return
        
        # 选择一个因子进行分层回测
        factor_name = "momentum_20"
        factor = factor_registry.get_factor(factor_name)
        
        if not factor:
            print(f"❌ 因子 {factor_name} 不存在")
            return
        
        # 计算因子值
        factor_values = factor.calculate(price_data)
        
        if factor_values.empty or factor_values.isna().all():
            print(f"❌ 因子 {factor_name} 计算失败")
            return
        
        print(f"使用因子: {factor_name}")
        print(f"分层数量: 5")
        
        # 运行分层回测
        backtest_engine = BacktestEngine()
        quantile_results = backtest_engine.run_quantile_backtest(
            factor_values=factor_values,
            price_data=price_data,
            quantiles=5,
            long_short=True
        )
        
        if "error" in quantile_results:
            print(f"❌ 分层回测失败: {quantile_results['error']}")
            return
        
        # 显示分层结果
        quantile_stats = quantile_results.get('quantile_stats', {})
        factor_ic = quantile_results.get('factor_ic', 0)
        
        print(f"\n因子IC: {factor_ic:.4f}")
        print("\n各分层表现:")
        print("分层      平均收益    夏普比率    总收益     样本数")
        print("-" * 55)
        
        for quantile_name, stats in quantile_stats.items():
            mean_return = stats.get('mean_return', 0)
            sharpe_ratio = stats.get('sharpe_ratio', 0)
            total_return = stats.get('total_return', 0)
            count = stats.get('count', 0)
            
            print(f"{quantile_name:<8} {mean_return:>10.4f} {sharpe_ratio:>10.2f} {total_return:>10.2%} {count:>8}")
        
        print("\n✅ 分层回测完成")
        
        return quantile_results
        
    except Exception as e:
        print(f"❌ 分层回测失败: {e}")
        return None


def demo_performance_analysis():
    """演示性能分析功能"""
    print("\n" + "="*50)
    print("性能分析演示")
    print("="*50)
    
    try:
        # 创建性能分析器
        performance_analyzer = PerformanceAnalyzer()
        
        # 生成模拟收益率数据
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)  # 模拟一年的日收益率
        returns_series = pd.Series(returns)
        
        print("使用模拟收益率数据进行性能分析")
        print(f"数据长度: {len(returns)} 天")
        
        # 进行综合性能分析
        performance_stats = performance_analyzer.comprehensive_analysis(
            returns=returns_series,
            risk_free_rate=0.02,
            periods_per_year=252
        )
        
        print("\n性能指标:")
        print("-" * 40)
        
        metrics = [
            ("总收益", "total_return", ".2%"),
            ("年化收益", "annual_return", ".2%"),
            ("年化波动率", "volatility", ".2%"),
            ("夏普比率", "sharpe_ratio", ".3f"),
            ("索提诺比率", "sortino_ratio", ".3f"),
            ("卡玛比率", "calmar_ratio", ".3f"),
            ("最大回撤", "max_drawdown", ".2%"),
            ("胜率", "win_rate", ".2%"),
            ("盈亏比", "profit_loss_ratio", ".3f"),
            ("偏度", "skewness", ".3f"),
            ("峰度", "kurtosis", ".3f"),
            ("VaR(5%)", "var_5pct", ".4f"),
            ("CVaR(5%)", "cvar_5pct", ".4f")
        ]
        
        for name, key, fmt in metrics:
            value = performance_stats.get(key, 0)
            if pd.notna(value):
                print(f"{name:<12}: {value:{fmt}}")
            else:
                print(f"{name:<12}: N/A")
        
        print("\n✅ 性能分析完成")
        
        return performance_stats
        
    except Exception as e:
        print(f"❌ 性能分析失败: {e}")
        return None


async def main():
    """主函数"""
    print("🚀 Factor Mining System - 因子评估演示")
    print("本演示将展示IC分析、因子回测、分层回测和性能分析功能")
    
    try:
        # 导入因子模块以触发注册
        import src.factors.technical  # 确保所有因子已注册
        
        # 显示已注册的因子
        all_factors = factor_registry.list_factors()
        print(f"\n📊 已注册因子数量: {len(all_factors)}")
        print("主要因子类别:")
        
        categories = {}
        for factor_name in all_factors:
            factor = factor_registry.get_factor(factor_name)
            if factor:
                category = factor.metadata.sub_category
                if category not in categories:
                    categories[category] = []
                categories[category].append(factor_name)
        
        for category, factors in categories.items():
            print(f"  {category}: {len(factors)} 个因子")
        
        # 运行演示
        ic_results = await demo_ic_analysis()
        backtest_results = await demo_factor_backtest()
        quantile_results = await demo_quantile_backtest()
        performance_stats = demo_performance_analysis()
        
        print("\n" + "="*50)
        print("演示总结")
        print("="*50)
        
        success_count = 0
        if ic_results: success_count += 1
        if backtest_results: success_count += 1
        if quantile_results: success_count += 1
        if performance_stats: success_count += 1
        
        print(f"✅ 成功完成 {success_count}/4 个演示模块")
        print("\n可以使用以下功能:")
        print("- IC分析: 评估因子预测能力")
        print("- 因子回测: 验证因子策略表现")
        print("- 分层回测: 多空组合构建")
        print("- 性能分析: 全面的指标计算")
        print("\n💡 提示: 可以通过API接口 (/docs) 使用这些功能")
        
    except KeyboardInterrupt:
        print("\n⏹️  演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        logger.error(f"演示失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main()) 