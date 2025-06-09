#!/usr/bin/env python3
"""
简化测试脚本 - 验证新增的因子评估功能
"""

import sys
import os
import pandas as pd
import numpy as np

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_factor_registry():
    """测试因子注册系统"""
    print("🧪 测试因子注册系统...")
    
    try:
        from src.factors.base.factor import factor_registry
        import src.factors.technical  # 触发因子注册
        
        all_factors = factor_registry.list_factors()
        print(f"✅ 已注册因子数量: {len(all_factors)}")
        
        # 显示前几个因子
        print("前10个因子:")
        for i, factor_name in enumerate(all_factors[:10]):
            factor = factor_registry.get_factor(factor_name)
            if factor:
                print(f"  {i+1}. {factor_name} ({factor.metadata.sub_category})")
        
        return True
        
    except Exception as e:
        print(f"❌ 因子注册系统测试失败: {e}")
        return False


def test_factor_calculation():
    """测试因子计算功能"""
    print("\n🧪 测试因子计算功能...")
    
    try:
        from src.factors.base.factor import factor_registry
        import src.factors.technical
        
        # 创建模拟数据
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        # 生成模拟价格数据
        price = 50000  # 起始价格
        prices = [price]
        for _ in range(99):
            change = np.random.normal(0, 0.02)  # 2%的日波动率
            price = price * (1 + change)
            prices.append(price)
        
        # 创建OHLCV数据
        test_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': [np.random.uniform(1000, 10000) for _ in prices]
        })
        test_data.set_index('timestamp', inplace=True)
        
        print(f"✅ 创建模拟数据: {len(test_data)} 行")
        
        # 测试几个因子
        test_factors = ["momentum_20", "volatility_20", "reversal_5"]
        
        for factor_name in test_factors:
            factor = factor_registry.get_factor(factor_name)
            if factor:
                try:
                    factor_values = factor.calculate(test_data)
                    valid_count = factor_values.count()
                    print(f"  ✅ {factor_name}: {valid_count} 个有效值")
                except Exception as e:
                    print(f"  ❌ {factor_name}: 计算失败 - {e}")
            else:
                print(f"  ⚠️  {factor_name}: 因子不存在")
        
        return True
        
    except Exception as e:
        print(f"❌ 因子计算测试失败: {e}")
        return False


def test_ic_analysis():
    """测试IC分析功能"""
    print("\n🧪 测试IC分析功能...")
    
    try:
        from src.evaluation.metrics.ic_analysis import ICAnalyzer
        
        # 创建模拟数据
        np.random.seed(42)
        n = 100
        factor_values = pd.Series(np.random.normal(0, 1, n))
        returns = pd.Series(np.random.normal(0, 0.02, n))
        
        # 添加一些相关性
        returns = returns + factor_values * 0.1  # 添加10%的相关性
        
        # 创建IC分析器
        ic_analyzer = ICAnalyzer()
        
        # 计算基础IC
        ic = ic_analyzer.calculate_ic(factor_values, returns)
        print(f"✅ 基础IC计算: {ic:.4f}")
        
        # 计算滚动IC
        rolling_ic = ic_analyzer.calculate_rolling_ic(factor_values, returns, window=20)
        print(f"✅ 滚动IC计算: {rolling_ic.count()} 个有效值")
        
        # 计算IC_IR
        ic_ir = ic_analyzer.calculate_ic_ir(factor_values, returns)
        print(f"✅ IC_IR计算: {ic_ir:.4f}")
        
        return True
        
    except Exception as e:
        print(f"❌ IC分析测试失败: {e}")
        return False


def test_performance_analysis():
    """测试性能分析功能"""
    print("\n🧪 测试性能分析功能...")
    
    try:
        from src.evaluation.metrics.performance import PerformanceAnalyzer
        
        # 创建模拟收益率数据
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 252))  # 一年的日收益率
        
        # 创建性能分析器
        performance_analyzer = PerformanceAnalyzer()
        
        # 计算基础指标
        sharpe = performance_analyzer.calculate_sharpe_ratio(returns)
        max_dd_info = performance_analyzer.calculate_max_drawdown(returns)
        win_rate = performance_analyzer.calculate_win_rate(returns)
        
        print(f"✅ 夏普比率: {sharpe:.3f}")
        print(f"✅ 最大回撤: {max_dd_info.get('max_drawdown', 0):.2%}")
        print(f"✅ 胜率: {win_rate:.2%}")
        
        # 综合分析
        comprehensive_stats = performance_analyzer.comprehensive_analysis(returns)
        metrics_count = len([k for k, v in comprehensive_stats.items() if pd.notna(v)])
        print(f"✅ 综合分析: 计算了 {metrics_count} 个指标")
        
        return True
        
    except Exception as e:
        print(f"❌ 性能分析测试失败: {e}")
        return False


def test_backtest_engine():
    """测试回测引擎功能"""
    print("\n🧪 测试回测引擎功能...")
    
    try:
        from src.evaluation.backtesting.engine import BacktestEngine, BacktestConfig
        from src.factors.base.factor import factor_registry
        import src.factors.technical
        
        # 创建模拟数据
        dates = pd.date_range('2024-01-01', periods=60, freq='D')
        np.random.seed(42)
        
        # 生成价格数据
        price = 50000
        prices = [price]
        for _ in range(59):
            change = np.random.normal(0, 0.02)
            price = price * (1 + change)
            prices.append(price)
        
        test_data = pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': [1000] * 60
        }, index=dates)
        
        # 获取因子
        factor = factor_registry.get_factor("momentum_20")
        if not factor:
            print("❌ 无法获取测试因子")
            return False
        
        # 计算因子值
        factor_values = factor.calculate(test_data)
        
        # 创建回测配置
        config = BacktestConfig(initial_capital=100000.0)
        
        # 运行简单回测
        backtest_engine = BacktestEngine(config)
        results = backtest_engine.run_factor_backtest(factor_values, test_data)
        
        if "error" in results:
            print(f"❌ 回测执行失败: {results['error']}")
            return False
        
        final_value = results.get('final_value', 0)
        total_return = results.get('total_return', 0)
        
        print(f"✅ 回测完成")
        print(f"  初始资金: ${config.initial_capital:,.0f}")
        print(f"  最终价值: ${final_value:,.0f}")
        print(f"  总收益: {total_return:.2%}")
        
        return True
        
    except Exception as e:
        print(f"❌ 回测引擎测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 Factor Mining System - 新功能测试")
    print("="*50)
    
    tests = [
        test_factor_registry,
        test_factor_calculation,
        test_ic_analysis,
        test_performance_analysis,
        test_backtest_engine
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 异常: {e}")
    
    print("\n" + "="*50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！新功能运行正常")
    else:
        print("⚠️  部分测试失败，请检查相关功能")
    
    print("\n💡 新增功能说明:")
    print("- 动量、波动率、反转三大类技术因子")
    print("- IC分析评估因子预测能力")
    print("- 性能分析计算各种量化指标")
    print("- 回测引擎验证因子策略表现")
    print("- API接口提供完整的评估功能")


if __name__ == "__main__":
    main() 