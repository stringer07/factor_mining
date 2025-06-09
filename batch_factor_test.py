#!/usr/bin/env python3
"""
批量因子测试工具
自动测试所有已注册的因子，评估其有效性并保存结果
"""

import sys
import os
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.factors.base.factor import factor_registry
from src.evaluation.metrics.ic_analysis import ICAnalyzer
from src.evaluation.metrics.performance import PerformanceAnalyzer
import src.factors.technical  # 触发因子注册


class BatchFactorTester:
    """批量因子测试器"""
    
    def __init__(self, results_dir: str = "factor_test_results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        self.ic_analyzer = ICAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
        
        # 测试结果存储
        self.test_results = []
        self.summary_results = pd.DataFrame()
        
        print(f"🎯 批量因子测试器初始化完成")
        print(f"📁 结果保存目录: {self.results_dir.absolute()}")
    
    def create_test_data(self, days: int = 200, with_trend: bool = True) -> pd.DataFrame:
        """创建测试数据"""
        print(f"📊 创建 {days} 天的测试数据...")
        
        dates = pd.date_range('2024-01-01', periods=days, freq='D')
        np.random.seed(42)  # 固定随机种子确保一致性
        
        price = 50000
        prices = [price]
        
        for i in range(days - 1):
            if with_trend:
                # 多种周期的趋势组合
                trend1 = 0.0008 * np.sin(i * 2 * np.pi / 30)    # 30天周期
                trend2 = 0.0005 * np.sin(i * 2 * np.pi / 60)    # 60天周期
                trend3 = 0.0003 * np.sin(i * 2 * np.pi / 120)   # 120天周期
                trend = trend1 + trend2 + trend3
                
                noise = np.random.normal(0, 0.02)
                change = trend + noise
            else:
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
    
    def test_single_factor(self, factor_name: str, data: pd.DataFrame) -> dict:
        """测试单个因子"""
        try:
            # 获取因子
            factor = factor_registry.get_factor(factor_name)
            if not factor:
                return {"error": f"因子 {factor_name} 不存在"}
            
            # 计算因子值
            factor_values = factor.calculate(data)
            
            if factor_values.empty or factor_values.isna().all():
                return {"error": f"因子 {factor_name} 计算失败"}
            
            # 基础统计
            basic_stats = {
                'total_count': len(factor_values),
                'valid_count': factor_values.count(),
                'valid_rate': factor_values.count() / len(factor_values),
                'mean': factor_values.mean(),
                'std': factor_values.std(),
                'min': factor_values.min(),
                'max': factor_values.max()
            }
            
            # IC分析
            returns = data['close'].pct_change()
            ic_results = {}
            periods = [1, 3, 5, 10, 20]
            
            for period in periods:
                future_returns = returns.shift(-period)
                
                ic = self.ic_analyzer.calculate_ic(factor_values, future_returns)
                rolling_ic = self.ic_analyzer.calculate_rolling_ic(
                    factor_values, future_returns, window=20
                )
                ic_ir = self.ic_analyzer.calculate_ic_ir(
                    factor_values, future_returns, window=20
                )
                ic_win_rate = (rolling_ic > 0).mean() if not rolling_ic.empty else 0
                
                ic_results[f'period_{period}'] = {
                    'ic': ic,
                    'ic_ir': ic_ir,
                    'ic_win_rate': ic_win_rate
                }
            
            # 分层回测
            backtest_result = self._simple_backtest(factor_values, returns)
            
            # 计算评分
            score_result = self._calculate_factor_score(ic_results, backtest_result)
            
            # 组装结果
            result = {
                'factor_name': factor_name,
                'factor_description': factor.metadata.description,
                'factor_category': factor.metadata.category,
                'factor_sub_category': factor.metadata.sub_category,
                'calculation_window': factor.metadata.calculation_window,
                'basic_stats': basic_stats,
                'ic_results': ic_results,
                'backtest_result': backtest_result,
                'score_result': score_result,
                'test_timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            return {"error": f"测试因子 {factor_name} 时出错: {str(e)}"}
    
    def _simple_backtest(self, factor_values: pd.Series, returns: pd.Series) -> dict:
        """简单分层回测"""
        try:
            future_returns = returns.shift(-1)
            aligned_data = pd.concat([factor_values, future_returns], axis=1).dropna()
            
            if len(aligned_data) < 10:
                return {"error": "数据不足"}
            
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
            
            quantile_stats = {}
            for q in aligned_data['quantile'].unique():
                if pd.isna(q):
                    continue
                
                mask = aligned_data['quantile'] == q
                q_returns = return_col[mask]
                
                if len(q_returns) > 0:
                    quantile_stats[str(q)] = {
                        'avg_return': q_returns.mean(),
                        'std_return': q_returns.std(),
                        'sharpe': q_returns.mean() / q_returns.std() if q_returns.std() > 0 else 0,
                        'win_rate': (q_returns > 0).mean(),
                        'count': len(q_returns)
                    }
            
            # 计算多空收益
            long_short_return = 0
            if 'Q1' in quantile_stats and 'Q5' in quantile_stats:
                long_short_return = quantile_stats['Q5']['avg_return'] - quantile_stats['Q1']['avg_return']
            
            return {
                'quantile_stats': quantile_stats,
                'long_short_return': long_short_return,
                'total_samples': len(aligned_data)
            }
            
        except Exception as e:
            return {"error": f"回测失败: {str(e)}"}
    
    def _calculate_factor_score(self, ic_results: dict, backtest_result: dict) -> dict:
        """计算因子评分"""
        score = 0
        total_checks = 0
        details = {}
        
        # IC分析评分
        if ic_results and 'period_1' in ic_results:
            period_1 = ic_results['period_1']
            period_5 = ic_results.get('period_5', {})
            
            ic_1 = period_1.get('ic', 0)
            ic_5 = period_5.get('ic', 0)
            ic_ir_1 = period_1.get('ic_ir', 0)
            
            # IC强度评分
            total_checks += 1
            if abs(ic_1) > 0.05:
                score += 1
                ic_rating = "优秀"
            elif abs(ic_1) > 0.02:
                score += 0.6
                ic_rating = "良好"
            else:
                score += 0.2
                ic_rating = "一般"
            
            details['ic_strength'] = {
                'value': ic_1,
                'rating': ic_rating,
                'score': score / total_checks
            }
            
            # IC稳定性评分
            total_checks += 1
            if abs(ic_ir_1) > 1.0:
                score += 1
                ir_rating = "稳定"
            elif abs(ic_ir_1) > 0.5:
                score += 0.6
                ir_rating = "一般"
            else:
                score += 0.2
                ir_rating = "不稳定"
            
            details['ic_stability'] = {
                'value': ic_ir_1,
                'rating': ir_rating,
                'score': (score - details['ic_strength']['score'] * (total_checks - 1)) / 1
            }
            
            # IC持续性评分
            total_checks += 1
            if abs(ic_5) > 0.02:
                score += 1
                persistence_rating = "持续性好"
            elif abs(ic_5) > 0.01:
                score += 0.6
                persistence_rating = "持续性一般"
            else:
                score += 0.2
                persistence_rating = "持续性差"
            
            details['ic_persistence'] = {
                'value': ic_5,
                'rating': persistence_rating,
                'score': (score - sum(d['score'] for d in details.values() if isinstance(d, dict)) * (total_checks - 1)) / 1
            }
        
        # 分层效果评分
        if backtest_result and 'long_short_return' in backtest_result:
            total_checks += 1
            ls_return = backtest_result['long_short_return']
            
            if abs(ls_return) > 0.005:
                score += 1
                layer_rating = "分层效果优秀"
            elif abs(ls_return) > 0.001:
                score += 0.6
                layer_rating = "分层效果良好"
            else:
                score += 0.2
                layer_rating = "分层效果一般"
            
            details['layer_effect'] = {
                'value': ls_return,
                'rating': layer_rating,
                'score': (score - sum(d['score'] for d in details.values() if isinstance(d, dict) and 'score' in d) * (total_checks - 1)) / 1
            }
        
        # 计算最终评分
        final_score = score / total_checks if total_checks > 0 else 0
        
        if final_score >= 0.8:
            overall_rating = "优秀"
            recommendation = "强烈推荐"
        elif final_score >= 0.6:
            overall_rating = "良好"
            recommendation = "推荐使用"
        elif final_score >= 0.4:
            overall_rating = "一般"
            recommendation = "谨慎使用"
        else:
            overall_rating = "较差"
            recommendation = "不推荐"
        
        return {
            'final_score': final_score,
            'overall_rating': overall_rating,
            'recommendation': recommendation,
            'details': details,
            'total_checks': total_checks
        }
    
    def run_batch_test(self, factor_filter: str = None, save_results: bool = True) -> pd.DataFrame:
        """运行批量测试"""
        print("🚀 开始批量因子测试")
        print("=" * 60)
        
        # 获取所有因子
        all_factors = factor_registry.list_factors()
        
        # 过滤因子
        if factor_filter:
            test_factors = [f for f in all_factors if factor_filter.lower() in f.lower()]
            print(f"🔍 过滤条件: {factor_filter}")
        else:
            test_factors = all_factors
        
        print(f"📋 待测试因子数量: {len(test_factors)}")
        
        # 创建测试数据
        test_data = self.create_test_data(days=200, with_trend=True)
        
        # 批量测试
        self.test_results = []
        successful_tests = 0
        
        for i, factor_name in enumerate(test_factors, 1):
            print(f"\n🧪 [{i}/{len(test_factors)}] 测试因子: {factor_name}")
            
            result = self.test_single_factor(factor_name, test_data)
            self.test_results.append(result)
            
            if "error" not in result:
                successful_tests += 1
                score = result['score_result']['final_score']
                rating = result['score_result']['overall_rating']
                print(f"   ✅ 完成 - 评分: {score:.3f} ({rating})")
            else:
                print(f"   ❌ 失败 - {result['error']}")
        
        print(f"\n📊 测试总结:")
        print(f"   总因子数: {len(test_factors)}")
        print(f"   成功测试: {successful_tests}")
        print(f"   失败测试: {len(test_factors) - successful_tests}")
        
        # 生成汇总结果
        self._generate_summary()
        
        # 保存结果
        if save_results:
            self._save_results()
        
        return self.summary_results
    
    def _generate_summary(self):
        """生成汇总结果"""
        summary_data = []
        
        for result in self.test_results:
            if "error" in result:
                continue
            
            # 提取关键指标
            row = {
                'factor_name': result['factor_name'],
                'description': result['factor_description'],
                'category': result['factor_category'],
                'sub_category': result['factor_sub_category'],
                'calculation_window': result['calculation_window'],
                'final_score': result['score_result']['final_score'],
                'overall_rating': result['score_result']['overall_rating'],
                'recommendation': result['score_result']['recommendation'],
                'valid_rate': result['basic_stats']['valid_rate'],
                'ic_1d': result['ic_results'].get('period_1', {}).get('ic', 0),
                'ic_5d': result['ic_results'].get('period_5', {}).get('ic', 0),
                'ic_ir_1d': result['ic_results'].get('period_1', {}).get('ic_ir', 0),
                'ic_win_rate_1d': result['ic_results'].get('period_1', {}).get('ic_win_rate', 0),
                'long_short_return': result['backtest_result'].get('long_short_return', 0),
                'test_timestamp': result['test_timestamp']
            }
            
            summary_data.append(row)
        
        self.summary_results = pd.DataFrame(summary_data)
        
        # 按评分排序
        if not self.summary_results.empty:
            self.summary_results = self.summary_results.sort_values('final_score', ascending=False)
    
    def _save_results(self):
        """保存测试结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存详细结果（JSON）
        detailed_file = self.results_dir / f"factor_test_detailed_{timestamp}.json"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2, default=str)
        
        # 保存汇总结果（CSV）
        summary_file = self.results_dir / f"factor_test_summary_{timestamp}.csv"
        self.summary_results.to_csv(summary_file, index=False, encoding='utf-8')
        
        # 保存最新结果（用于查看）
        latest_summary = self.results_dir / "latest_factor_test_summary.csv"
        self.summary_results.to_csv(latest_summary, index=False, encoding='utf-8')
        
        latest_detailed = self.results_dir / "latest_factor_test_detailed.json"
        with open(latest_detailed, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 结果已保存:")
        print(f"   详细结果: {detailed_file}")
        print(f"   汇总结果: {summary_file}")
        print(f"   最新结果: {latest_summary}")
    
    def get_top_factors(self, n: int = 10, min_score: float = 0.4) -> pd.DataFrame:
        """获取表现最好的因子"""
        if self.summary_results.empty:
            print("⚠️ 暂无测试结果，请先运行批量测试")
            return pd.DataFrame()
        
        # 过滤评分
        filtered_results = self.summary_results[
            self.summary_results['final_score'] >= min_score
        ].head(n)
        
        print(f"🏆 表现最好的 {len(filtered_results)} 个因子 (评分 ≥ {min_score}):")
        print("=" * 80)
        
        for idx, row in filtered_results.iterrows():
            print(f"{row.name + 1:2d}. {row['factor_name']:<25} "
                  f"评分: {row['final_score']:.3f} ({row['overall_rating']}) "
                  f"IC: {row['ic_1d']:.4f}")
        
        return filtered_results
    
    def get_factor_details(self, factor_name: str) -> dict:
        """获取因子详细信息"""
        for result in self.test_results:
            if result.get('factor_name') == factor_name:
                return result
        
        print(f"⚠️ 未找到因子 {factor_name} 的测试结果")
        return {}
    
    def print_factor_report(self, factor_name: str):
        """打印因子详细报告"""
        details = self.get_factor_details(factor_name)
        
        if not details or "error" in details:
            print(f"❌ 无法获取因子 {factor_name} 的详细信息")
            return
        
        print(f"\n📄 {factor_name} 因子详细报告")
        print("=" * 60)
        
        # 基本信息
        print(f"📋 基本信息:")
        print(f"   名称: {details['factor_name']}")
        print(f"   描述: {details['factor_description']}")
        print(f"   类别: {details['factor_category']} - {details['factor_sub_category']}")
        print(f"   计算窗口: {details['calculation_window']}")
        
        # 评分结果
        score_result = details['score_result']
        print(f"\n🏆 评分结果:")
        print(f"   综合评分: {score_result['final_score']:.3f}")
        print(f"   总体评级: {score_result['overall_rating']}")
        print(f"   使用建议: {score_result['recommendation']}")
        
        # 详细评分
        print(f"\n📈 详细评分:")
        for key, detail in score_result['details'].items():
            if isinstance(detail, dict):
                print(f"   {key}: {detail['rating']} (值: {detail['value']:.4f})")
        
        # IC分析
        ic_results = details['ic_results']
        print(f"\n📊 IC分析:")
        for period, ic_data in ic_results.items():
            period_num = period.split('_')[1]
            ic = ic_data['ic']
            ic_ir = ic_data['ic_ir']
            win_rate = ic_data['ic_win_rate']
            print(f"   {period_num}期: IC={ic:.4f}, IC_IR={ic_ir:.4f}, 胜率={win_rate:.2%}")
        
        # 分层回测
        backtest = details['backtest_result']
        if 'quantile_stats' in backtest:
            print(f"\n🔍 分层回测:")
            print(f"   多空收益: {backtest['long_short_return']:.4f}")
            print(f"   样本数量: {backtest['total_samples']}")
    
    def load_previous_results(self, file_path: str = None):
        """加载之前的测试结果"""
        if file_path is None:
            file_path = self.results_dir / "latest_factor_test_summary.csv"
        
        try:
            self.summary_results = pd.read_csv(file_path)
            print(f"✅ 已加载测试结果: {len(self.summary_results)} 个因子")
            return True
        except Exception as e:
            print(f"❌ 加载结果失败: {e}")
            return False


def main():
    """主函数"""
    print("🎯 批量因子测试工具")
    print("用途: 自动测试所有因子并生成评估报告")
    print()
    
    # 创建测试器
    tester = BatchFactorTester()
    
    # 菜单选择
    while True:
        print("\n📋 请选择操作:")
        print("1. 运行批量测试 (所有因子)")
        print("2. 运行批量测试 (按类别过滤)")
        print("3. 查看最佳因子")
        print("4. 查看因子详情")
        print("5. 加载之前的结果")
        print("0. 退出")
        
        choice = input("\n请输入选项 (0-5): ").strip()
        
        if choice == "0":
            print("👋 再见!")
            break
        elif choice == "1":
            tester.run_batch_test()
            tester.get_top_factors(n=10)
        elif choice == "2":
            filter_text = input("请输入过滤条件 (如 momentum, volatility): ").strip()
            tester.run_batch_test(factor_filter=filter_text)
            tester.get_top_factors(n=10)
        elif choice == "3":
            n = int(input("显示前几名 (默认10): ") or "10")
            min_score = float(input("最低评分 (默认0.4): ") or "0.4")
            tester.get_top_factors(n=n, min_score=min_score)
        elif choice == "4":
            factor_name = input("请输入因子名称: ").strip()
            tester.print_factor_report(factor_name)
        elif choice == "5":
            tester.load_previous_results()
            print(f"已加载 {len(tester.summary_results)} 个因子的结果")
        else:
            print("⚠️ 无效选项，请重新选择")


if __name__ == "__main__":
    main() 