#!/usr/bin/env python3
"""
Momentum_20 因子有效性测试脚本
提供完整的因子评估流程，包括IC分析、分层回测、性能评估等
"""

import sys
import os
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.factors.base.factor import factor_registry
from src.evaluation.metrics.ic_analysis import ICAnalyzer
from src.evaluation.metrics.performance import PerformanceAnalyzer
from src.evaluation.backtesting.engine import BacktestEngine, BacktestConfig
from src.data.collectors.exchange import MultiExchangeCollector
import src.factors.technical  # 触发因子注册


class Momentum20Tester:
    """Momentum_20 因子测试器"""
    
    def __init__(self):
        self.factor_name = "momentum_20"
        self.factor = factor_registry.get_factor(self.factor_name)
        self.ic_analyzer = ICAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
        self.data_collector = MultiExchangeCollector()
        
        if not self.factor:
            raise ValueError(f"因子 {self.factor_name} 不存在")
        
        print(f"🎯 初始化 {self.factor_name} 因子测试器")
        print(f"📋 因子描述: {self.factor.metadata.description}")
        print(f"📈 计算窗口: {self.factor.metadata.calculation_window}")
    
    def create_synthetic_data(self, days: int = 100) -> pd.DataFrame:
        """创建合成测试数据"""
        print(f"\n📊 创建 {days} 天的合成测试数据...")
        
        dates = pd.date_range('2024-01-01', periods=days, freq='D')
        np.random.seed(42)
        
        # 生成具有趋势的价格数据
        price = 50000
        prices = [price]
        
        for i in range(days - 1):
            # 添加一些趋势性，使momentum因子更有效
            trend = 0.0005 if i % 30 < 15 else -0.0005  # 周期性趋势
            noise = np.random.normal(0, 0.02)
            change = trend + noise
            price = price * (1 + change)
            prices.append(price)
        
        data = pd.DataFrame({
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': [np.random.uniform(1000, 10000) for _ in prices]
        }, index=dates)
        
        print(f"✅ 数据创建完成: {len(data)} 行")
        return data
    
    async def get_real_data(self, symbol: str = "BTC/USDT", days: int = 120) -> pd.DataFrame:
        """获取真实市场数据"""
        print(f"\n📡 获取 {symbol} 真实市场数据 ({days} 天)...")
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            data = await self.data_collector.get_ohlcv(
                symbol=symbol,
                timeframe="1d",
                since=start_date,
                limit=days
            )
            
            if data.empty:
                print("❌ 无法获取真实数据，将使用合成数据")
                return self.create_synthetic_data(days)
            
            print(f"✅ 获取到真实数据: {len(data)} 行")
            return data
            
        except Exception as e:
            print(f"⚠️  获取真实数据失败: {e}")
            print("🔄 使用合成数据代替...")
            return self.create_synthetic_data(days)
    
    def test_factor_calculation(self, data: pd.DataFrame) -> pd.Series:
        """测试因子计算"""
        print(f"\n🧮 测试 {self.factor_name} 因子计算...")
        
        try:
            factor_values = self.factor.calculate(data)
            
            if factor_values.empty:
                raise ValueError("因子计算结果为空")
            
            valid_count = factor_values.count()
            total_count = len(factor_values)
            valid_rate = valid_count / total_count
            
            print(f"✅ 因子计算成功")
            print(f"   📊 总数据点: {total_count}")
            print(f"   ✅ 有效数据点: {valid_count}")
            print(f"   📈 有效率: {valid_rate:.2%}")
            print(f"   📉 均值: {factor_values.mean():.6f}")
            print(f"   📊 标准差: {factor_values.std():.6f}")
            print(f"   📈 最大值: {factor_values.max():.6f}")
            print(f"   📉 最小值: {factor_values.min():.6f}")
            
            return factor_values
            
        except Exception as e:
            print(f"❌ 因子计算失败: {e}")
            raise
    
    def test_ic_analysis(self, factor_values: pd.Series, price_data: pd.DataFrame) -> dict:
        """测试IC分析"""
        print(f"\n📈 进行 {self.factor_name} IC分析...")
        
        try:
            # 计算收益率
            returns = price_data['close'].pct_change()
            
            # 进行综合IC分析
            ic_results = self.ic_analyzer.comprehensive_analysis(
                factor_values=factor_values,
                price_data=price_data,
                periods=[1, 3, 5, 10, 20]
            )
            
            print("✅ IC分析完成")
            print("\n📋 IC分析结果:")
            
            # 显示基础IC统计
            basic_stats = ic_results.get('basic_ic_stats', {})
            for period, stats in basic_stats.items():
                ic = stats.get('ic', 0)
                ic_ir = stats.get('ic_ir', 0)
                win_rate = stats.get('ic_win_rate', 0)
                
                status = "🔥" if abs(ic) > 0.05 else "✅" if abs(ic) > 0.02 else "⚠️"
                print(f"   {status} {period}: IC={ic:.4f}, IC_IR={ic_ir:.4f}, 胜率={win_rate:.2%}")
            
            # IC衰减分析
            ic_decay = ic_results.get('ic_decay', pd.Series())
            if not ic_decay.empty:
                print(f"\n📉 IC衰减分析:")
                print(f"   1期: {ic_decay.iloc[0]:.4f}")
                print(f"   5期: {ic_decay.iloc[4]:.4f}" if len(ic_decay) > 4 else "   5期: N/A")
                print(f"   10期: {ic_decay.iloc[9]:.4f}" if len(ic_decay) > 9 else "   10期: N/A")
            
            # 分层IC分析
            rank_ic = ic_results.get('rank_ic_analysis', {})
            if rank_ic:
                rank_ic_value = rank_ic.get('rank_ic', 0)
                monotonicity = rank_ic.get('monotonicity_score', 0)
                print(f"\n📊 分层分析:")
                print(f"   等级IC: {rank_ic_value:.4f}")
                print(f"   单调性评分: {monotonicity:.4f}")
            
            return ic_results
            
        except Exception as e:
            print(f"❌ IC分析失败: {e}")
            return {}
    
    def test_quantile_backtest(self, factor_values: pd.Series, price_data: pd.DataFrame) -> dict:
        """测试分层回测"""
        print(f"\n📊 进行 {self.factor_name} 分层回测...")
        
        try:
            # 配置回测参数
            config = BacktestConfig(
                initial_capital=100000.0,
                commission_rate=0.001,
                slippage_rate=0.0005
            )
            
            backtest_engine = BacktestEngine(config)
            
            # 运行分层回测
            quantile_results = backtest_engine.run_quantile_backtest(
                factor_values=factor_values,
                price_data=price_data,
                quantiles=5,
                long_short=True
            )
            
            if "error" in quantile_results:
                print(f"❌ 分层回测失败: {quantile_results['error']}")
                return {}
            
            print("✅ 分层回测完成")
            
            # 显示分层结果
            quantile_stats = quantile_results.get('quantile_stats', {})
            factor_ic = quantile_results.get('factor_ic', 0)
            
            print(f"\n📈 分层回测结果:")
            print(f"   因子IC: {factor_ic:.4f}")
            
            if quantile_stats:
                print("\n   各分位数表现:")
                for quantile, stats in quantile_stats.items():
                    avg_return = stats.get('mean_return', 0)  # 修正 key
                    count = stats.get('count', 0)
                    print(f"     {quantile}: 平均收益={avg_return:.4f}, 样本数={count}")
            
            return quantile_results
            
        except Exception as e:
            print(f"❌ 分层回测失败: {e}")
            return {}
    
    def test_factor_backtest(self, factor_values: pd.Series, price_data: pd.DataFrame) -> dict:
        """测试因子回测"""
        print(f"\n🚀 进行 {self.factor_name} 因子回测...")
        
        try:
            # 配置回测参数
            config = BacktestConfig(
                initial_capital=100000.0,
                commission_rate=0.001,
                slippage_rate=0.0005
            )
            
            backtest_engine = BacktestEngine(config)
            
            # 运行因子回测
            backtest_results = backtest_engine.run_factor_backtest(
                factor_values=factor_values,
                price_data=price_data
            )
            
            if "error" in backtest_results:
                print(f"❌ 因子回测失败: {backtest_results['error']}")
                return {}
            
            print("✅ 因子回测完成")
            
            # 显示回测结果
            final_value = backtest_results.get('final_value', 0)
            total_return = backtest_results.get('total_return', 0)
            performance_stats = backtest_results.get('performance_stats', {})
            
            print(f"\n📊 回测结果:")
            print(f"   期末资产: ${final_value:,.2f}")
            print(f"   总收益率: {total_return:.2%}")
            
            if performance_stats:
                sharpe = performance_stats.get('sharpe_ratio', 0)
                max_dd = performance_stats.get('max_drawdown', 0)
                win_rate = performance_stats.get('win_rate', 0)
                volatility = performance_stats.get('volatility', 0)
                
                print(f"   夏普比率: {sharpe:.3f}")
                print(f"   最大回撤: {max_dd:.2%}")
                print(f"   胜率: {win_rate:.2%}")
                print(f"   年化波动率: {volatility:.2%}")
            
            return backtest_results
            
        except Exception as e:
            print(f"❌ 因子回测失败: {e}")
            return {}
    
    def generate_evaluation_report(
        self, 
        ic_results: dict, 
        quantile_results: dict, 
        backtest_results: dict
    ):
        """生成评估报告"""
        print(f"\n📄 生成 {self.factor_name} 评估报告")
        print("=" * 60)
        
        # 因子有效性评级
        score = 0
        total_checks = 0
        
        print("🎯 因子有效性评估:")
        
        # 1. IC分析评估
        basic_stats = ic_results.get('basic_ic_stats', {})
        if basic_stats:
            period_1 = basic_stats.get('period_1', {})
            ic = period_1.get('ic', 0)
            ic_ir = period_1.get('ic_ir', 0)
            
            total_checks += 2
            if abs(ic) > 0.05:
                score += 2
                ic_rating = "🔥 优秀"
            elif abs(ic) > 0.02:
                score += 1
                ic_rating = "✅ 良好"
            else:
                ic_rating = "⚠️  一般"
            
            if abs(ic_ir) > 1.0:
                score += 1
                ir_rating = "✅ 稳定"
            else:
                ir_rating = "⚠️  不稳定"
            
            print(f"   IC表现: {ic_rating} (IC={ic:.4f})")
            print(f"   IC稳定性: {ir_rating} (IC_IR={ic_ir:.4f})")
        
        # 2. 分层回测评估
        if quantile_results:
            factor_ic = quantile_results.get('factor_ic', 0)
            total_checks += 1
            
            if abs(factor_ic) > 0.05:
                score += 1
                layer_rating = "✅ 分层效果好"
            else:
                layer_rating = "⚠️  分层效果一般"
            
            print(f"   分层效果: {layer_rating} (因子IC={factor_ic:.4f})")
        
        # 3. 回测表现评估
        if backtest_results:
            performance_stats = backtest_results.get('performance_stats', {})
            if performance_stats:
                sharpe = performance_stats.get('sharpe_ratio', 0)
                max_dd = performance_stats.get('max_drawdown', 0)
                
                total_checks += 2
                if sharpe > 1.0:
                    score += 1
                    sharpe_rating = "✅ 风险调整收益好"
                else:
                    sharpe_rating = "⚠️  风险调整收益一般"
                
                if abs(max_dd) < 0.2:
                    score += 1
                    dd_rating = "✅ 回撤控制好"
                else:
                    dd_rating = "⚠️  回撤较大"
                
                print(f"   夏普比率: {sharpe_rating} ({sharpe:.3f})")
                print(f"   回撤控制: {dd_rating} ({max_dd:.2%})")
        
        # 总体评级
        if total_checks > 0:
            final_score = score / total_checks
            if final_score >= 0.8:
                overall_rating = "🔥 优秀"
            elif final_score >= 0.6:
                overall_rating = "✅ 良好"
            elif final_score >= 0.4:
                overall_rating = "⚠️  一般"
            else:
                overall_rating = "❌ 较差"
            
            print(f"\n🏆 综合评级: {overall_rating} ({score}/{total_checks} 项通过)")
        
        # 使用建议
        print(f"\n💡 使用建议:")
        if final_score >= 0.6:
            print("   ✅ 该因子具有一定的预测能力，可以考虑在投资组合中使用")
            print("   📈 建议结合其他因子进行组合优化")
            print("   ⚠️  注意定期监控因子表现，及时调整")
        else:
            print("   ⚠️  该因子预测能力有限，不建议单独使用")
            print("   🔧 建议优化因子参数或寻找其他替代因子")
            print("   📊 可以作为辅助因子与其他因子组合使用")
    
    async def run_comprehensive_test(self, use_real_data: bool = True):
        """运行综合测试"""
        print("🚀 开始 Momentum_20 因子有效性综合测试")
        print("=" * 60)
        
        try:
            # 1. 获取数据
            if use_real_data:
                data = await self.get_real_data()
            else:
                data = self.create_synthetic_data()
            
            # 2. 测试因子计算
            factor_values = self.test_factor_calculation(data)
            
            # 3. IC分析
            ic_results = self.test_ic_analysis(factor_values, data)
            
            # 4. 分层回测
            quantile_results = self.test_quantile_backtest(factor_values, data)
            
            # 5. 因子回测
            backtest_results = self.test_factor_backtest(factor_values, data)
            
            # 6. 生成评估报告
            self.generate_evaluation_report(ic_results, quantile_results, backtest_results)
            
            print("\n✅ 测试完成!")
            
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {e}")
            raise
        
        finally:
            # 确保释放交易所连接（兼容不同实现）
            try:
                if hasattr(self.data_collector, "close"):
                    await self.data_collector.close()
                elif hasattr(self.data_collector, "disconnect_all"):
                    await self.data_collector.disconnect_all()
            except Exception as _e:
                print(f"⚠️  断开交易所连接时出现问题: {_e}")


async def main():
    """主函数"""
    print("🎯 Momentum_20 因子有效性测试工具")
    print("使用说明: 本工具将对 momentum_20 因子进行全面的有效性评估")
    print()
    
    # 询问用户是否使用真实数据
    use_real = input("是否使用真实市场数据进行测试? (y/n, 默认 y): ").lower()
    use_real_data = use_real != 'n'
    
    # 创建测试器并运行测试
    tester = Momentum20Tester()
    await tester.run_comprehensive_test(use_real_data)


if __name__ == "__main__":
    asyncio.run(main()) 