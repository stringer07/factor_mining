#!/usr/bin/env python3
"""
简化版 Momentum_20 因子有效性测试脚本
专注于基础的因子分析和IC测试
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.factors.base.factor import factor_registry
from src.evaluation.metrics.ic_analysis import ICAnalyzer
from src.evaluation.metrics.performance import PerformanceAnalyzer
import src.factors.technical  # 触发因子注册


class SimpleMomentum20Tester:
    """简化版 Momentum_20 因子测试器"""
    
    def __init__(self):
        self.factor_name = "momentum_20"
        self.factor = factor_registry.get_factor(self.factor_name)
        self.ic_analyzer = ICAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
        
        if not self.factor:
            raise ValueError(f"因子 {self.factor_name} 不存在")
        
        print(f"🎯 初始化 {self.factor_name} 因子测试器")
        print(f"📋 因子描述: {self.factor.metadata.description}")
        print(f"📈 计算窗口: {self.factor.metadata.calculation_window}")
    
    def create_test_data(self, days: int = 100, with_trend: bool = True) -> pd.DataFrame:
        """创建测试数据"""
        print(f"\n📊 创建 {days} 天的测试数据...")
        
        dates = pd.date_range('2024-01-01', periods=days, freq='D')
        np.random.seed(42)
        
        price = 50000
        prices = [price]
        
        for i in range(days - 1):
            if with_trend:
                # 添加周期性趋势，让动量因子更有效
                trend = 0.001 * np.sin(i * 2 * np.pi / 30)  # 30天周期
                noise = np.random.normal(0, 0.02)
                change = trend + noise
            else:
                # 纯随机游走
                change = np.random.normal(0, 0.02)
            
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
    
    def test_factor_calculation(self, data: pd.DataFrame) -> pd.Series:
        """测试因子计算"""
        print(f"\n🧮 测试 {self.factor_name} 因子计算...")
        
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
    
    def test_ic_analysis(self, factor_values: pd.Series, price_data: pd.DataFrame) -> dict:
        """测试IC分析"""
        print(f"\n📈 进行 {self.factor_name} IC分析...")
        
        # 计算未来收益率
        returns = price_data['close'].pct_change()
        
        ic_results = {}
        periods = [1, 3, 5, 10, 20]
        
        print("📋 IC分析结果:")
        
        for period in periods:
            # 计算前瞻收益率
            future_returns = returns.shift(-period)
            
            # 计算IC
            ic = self.ic_analyzer.calculate_ic(factor_values, future_returns)
            
            # 计算滚动IC
            rolling_ic = self.ic_analyzer.calculate_rolling_ic(
                factor_values, future_returns, window=20
            )
            
            # 计算IC_IR
            ic_ir = self.ic_analyzer.calculate_ic_ir(
                factor_values, future_returns, window=20
            )
            
            # 计算IC胜率
            ic_win_rate = (rolling_ic > 0).mean() if not rolling_ic.empty else 0
            
            ic_results[f'period_{period}'] = {
                'ic': ic,
                'ic_ir': ic_ir,
                'ic_win_rate': ic_win_rate,
                'rolling_ic': rolling_ic
            }
            
            # 显示结果
            status = "🔥" if abs(ic) > 0.05 else "✅" if abs(ic) > 0.02 else "⚠️"
            print(f"   {status} {period}期: IC={ic:.4f}, IC_IR={ic_ir:.4f}, 胜率={ic_win_rate:.2%}")
        
        return ic_results
    
    def test_simple_backtest(self, factor_values: pd.Series, price_data: pd.DataFrame) -> dict:
        """简单回测分析"""
        print(f"\n🔍 进行简单回测分析...")
        
        # 计算收益率
        returns = price_data['close'].pct_change()
        future_returns = returns.shift(-1)  # 下一期收益率
        
        # 对齐数据
        aligned_data = pd.concat([factor_values, future_returns], axis=1).dropna()
        if len(aligned_data) < 10:
            print("❌ 数据不足进行回测")
            return {}
        
        factor_col = aligned_data.iloc[:, 0]
        return_col = aligned_data.iloc[:, 1]
        
        # 分层分析
        quantiles = 5
        aligned_data['quantile'] = pd.qcut(
            factor_col, 
            q=quantiles, 
            labels=[f'Q{i+1}' for i in range(quantiles)],
            duplicates='drop'
        )
        
        # 计算各层表现
        quantile_stats = {}
        print("\n📊 分层分析结果:")
        
        for q in aligned_data['quantile'].unique():
            if pd.isna(q):
                continue
            
            mask = aligned_data['quantile'] == q
            q_returns = return_col[mask]
            
            if len(q_returns) > 0:
                avg_return = q_returns.mean()
                std_return = q_returns.std()
                sharpe = avg_return / std_return if std_return > 0 else 0
                win_rate = (q_returns > 0).mean()
                
                quantile_stats[q] = {
                    'avg_return': avg_return,
                    'std_return': std_return,
                    'sharpe': sharpe,
                    'win_rate': win_rate,
                    'count': len(q_returns)
                }
                
                print(f"   {q}: 平均收益={avg_return:.4f}, 夏普={sharpe:.3f}, 胜率={win_rate:.2%}, 样本={len(q_returns)}")
        
        # 计算多空组合收益
        if 'Q1' in quantile_stats and 'Q5' in quantile_stats:
            long_short_return = quantile_stats['Q5']['avg_return'] - quantile_stats['Q1']['avg_return']
            print(f"\n📈 多空组合收益: {long_short_return:.4f}")
        
        return {
            'quantile_stats': quantile_stats,
            'total_samples': len(aligned_data)
        }
    
    def generate_summary_report(self, ic_results: dict, backtest_results: dict):
        """生成总结报告"""
        print(f"\n📄 {self.factor_name} 因子评估总结")
        print("=" * 60)
        
        score = 0
        total_checks = 0
        
        # IC分析评估
        if ic_results:
            period_1 = ic_results.get('period_1', {})
            period_5 = ic_results.get('period_5', {})
            
            ic_1 = period_1.get('ic', 0)
            ic_5 = period_5.get('ic', 0)
            ic_ir_1 = period_1.get('ic_ir', 0)
            
            total_checks += 3
            
            # IC大小评估
            if abs(ic_1) > 0.05:
                score += 1
                ic_rating = "🔥 优秀"
            elif abs(ic_1) > 0.02:
                score += 0.5
                ic_rating = "✅ 良好"
            else:
                ic_rating = "⚠️ 一般"
            
            # IC稳定性评估
            if abs(ic_ir_1) > 1.0:
                score += 1
                ir_rating = "✅ 稳定"
            else:
                ir_rating = "⚠️ 不稳定"
            
            # IC持续性评估
            if abs(ic_5) > 0.02:
                score += 0.5
                persistence_rating = "✅ 持续性好"
            else:
                persistence_rating = "⚠️ 持续性一般"
            
            print(f"📈 IC评估:")
            print(f"   IC强度: {ic_rating} (1期IC={ic_1:.4f})")
            print(f"   IC稳定性: {ir_rating} (IC_IR={ic_ir_1:.4f})")
            print(f"   IC持续性: {persistence_rating} (5期IC={ic_5:.4f})")
        
        # 分层回测评估
        if backtest_results:
            quantile_stats = backtest_results.get('quantile_stats', {})
            
            if 'Q1' in quantile_stats and 'Q5' in quantile_stats:
                total_checks += 1
                
                q1_return = quantile_stats['Q1']['avg_return']
                q5_return = quantile_stats['Q5']['avg_return']
                spread = q5_return - q1_return
                
                if abs(spread) > 0.001:  # 0.1%的差异
                    score += 1
                    spread_rating = "✅ 分层效果明显"
                else:
                    spread_rating = "⚠️ 分层效果微弱"
                
                print(f"📊 分层评估:")
                print(f"   分层效果: {spread_rating} (收益差={spread:.4f})")
        
        # 综合评级
        if total_checks > 0:
            final_score = score / total_checks
            if final_score >= 0.8:
                overall_rating = "🔥 优秀"
                recommendation = "强烈推荐使用"
            elif final_score >= 0.6:
                overall_rating = "✅ 良好"
                recommendation = "推荐使用，注意监控"
            elif final_score >= 0.4:
                overall_rating = "⚠️ 一般"
                recommendation = "谨慎使用，需要优化"
            else:
                overall_rating = "❌ 较差"
                recommendation = "不推荐使用"
            
            print(f"\n🏆 综合评级: {overall_rating} (得分: {score:.1f}/{total_checks})")
            print(f"💡 使用建议: {recommendation}")
    
    def run_comprehensive_test(self, use_trend_data: bool = True):
        """运行综合测试"""
        print("🚀 开始 Momentum_20 因子有效性测试")
        print("=" * 60)
        
        try:
            # 1. 创建测试数据
            data = self.create_test_data(days=100, with_trend=use_trend_data)
            
            # 2. 测试因子计算
            factor_values = self.test_factor_calculation(data)
            
            # 3. IC分析
            ic_results = self.test_ic_analysis(factor_values, data)
            
            # 4. 简单回测分析
            backtest_results = self.test_simple_backtest(factor_values, data)
            
            # 5. 生成总结报告
            self.generate_summary_report(ic_results, backtest_results)
            
            print("\n✅ 测试完成!")
            
            return {
                'ic_results': ic_results,
                'backtest_results': backtest_results,
                'factor_values': factor_values,
                'price_data': data
            }
            
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {e}")
            raise


def main():
    """主函数"""
    print("🎯 Momentum_20 因子有效性测试工具 (简化版)")
    print("使用说明: 本工具对 momentum_20 因子进行基础的有效性评估")
    print()
    
    # 询问用户是否使用趋势数据
    use_trend = input("是否使用包含趋势的测试数据? (y/n, 默认 y): ").lower()
    use_trend_data = use_trend != 'n'
    
    # 创建测试器并运行测试
    tester = SimpleMomentum20Tester()
    results = tester.run_comprehensive_test(use_trend_data)
    
    # 显示如何进一步分析的建议
    print(f"\n📋 进一步分析建议:")
    print(f"   1. 在不同市场环境下测试因子表现")
    print(f"   2. 调整因子参数（如窗口大小）进行优化")
    print(f"   3. 与其他因子进行相关性分析")
    print(f"   4. 加入交易成本进行更精确的回测")
    print(f"   5. 使用真实市场数据验证结果")


if __name__ == "__main__":
    main() 