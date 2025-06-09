#!/usr/bin/env python3
"""
因子测试结果查看器
提供便捷的界面查看和分析因子测试结果
"""

import sys
import os
import pandas as pd
import json
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class FactorResultsViewer:
    """因子测试结果查看器"""
    
    def __init__(self, results_dir: str = "factor_test_results"):
        self.results_dir = Path(results_dir)
        self.summary_df = pd.DataFrame()
        self.detailed_results = []
        
        print(f"🔍 因子结果查看器初始化")
        print(f"📁 结果目录: {self.results_dir.absolute()}")
        
        # 自动加载最新结果
        self.load_latest_results()
    
    def load_latest_results(self) -> bool:
        """加载最新的测试结果"""
        try:
            # 加载汇总结果
            summary_file = self.results_dir / "latest_factor_test_summary.csv"
            if summary_file.exists():
                self.summary_df = pd.read_csv(summary_file)
                print(f"✅ 已加载汇总结果: {len(self.summary_df)} 个因子")
            else:
                print("⚠️ 未找到最新的汇总结果文件")
                return False
            
            # 加载详细结果
            detailed_file = self.results_dir / "latest_factor_test_detailed.json"
            if detailed_file.exists():
                with open(detailed_file, 'r', encoding='utf-8') as f:
                    self.detailed_results = json.load(f)
                print(f"✅ 已加载详细结果: {len(self.detailed_results)} 个因子")
            else:
                print("⚠️ 未找到最新的详细结果文件")
            
            return True
            
        except Exception as e:
            print(f"❌ 加载结果失败: {e}")
            return False
    
    def show_summary_stats(self):
        """显示汇总统计"""
        if self.summary_df.empty:
            print("❌ 无可用数据")
            return
        
        print("\n📊 因子测试汇总统计")
        print("=" * 50)
        
        total_factors = len(self.summary_df)
        print(f"总因子数量: {total_factors}")
        
        # 按评级分布
        rating_counts = self.summary_df['overall_rating'].value_counts()
        print(f"\n📈 评级分布:")
        for rating, count in rating_counts.items():
            percentage = count / total_factors * 100
            print(f"   {rating}: {count} 个 ({percentage:.1f}%)")
        
        # 按类别分布
        category_counts = self.summary_df['category'].value_counts()
        print(f"\n🏷️ 类别分布:")
        for category, count in category_counts.items():
            percentage = count / total_factors * 100
            print(f"   {category}: {count} 个 ({percentage:.1f}%)")
        
        # 评分统计
        print(f"\n🏆 评分统计:")
        print(f"   最高评分: {self.summary_df['final_score'].max():.3f}")
        print(f"   最低评分: {self.summary_df['final_score'].min():.3f}")
        print(f"   平均评分: {self.summary_df['final_score'].mean():.3f}")
        print(f"   中位数评分: {self.summary_df['final_score'].median():.3f}")
    
    def show_top_factors(self, n: int = 10, min_score: float = 0.4):
        """显示最佳因子"""
        if self.summary_df.empty:
            print("❌ 无可用数据")
            return
        
        # 过滤和排序
        filtered_df = self.summary_df[
            self.summary_df['final_score'] >= min_score
        ].head(n)
        
        print(f"\n🏆 表现最好的 {len(filtered_df)} 个因子 (评分 ≥ {min_score})")
        print("=" * 100)
        print(f"{'排名':<4} {'因子名称':<25} {'评分':<6} {'评级':<6} {'1日IC':<8} {'5日IC':<8} {'多空收益':<10} {'类别':<12}")
        print("-" * 100)
        
        for i, (idx, row) in enumerate(filtered_df.iterrows(), 1):
            print(f"{i:<4} {row['factor_name']:<25} {row['final_score']:<6.3f} "
                  f"{row['overall_rating']:<6} {row['ic_1d']:<8.4f} {row['ic_5d']:<8.4f} "
                  f"{row['long_short_return']:<10.4f} {row['sub_category']:<12}")
    
    def show_factors_by_category(self, category: str = None):
        """按类别显示因子"""
        if self.summary_df.empty:
            print("❌ 无可用数据")
            return
        
        if category:
            filtered_df = self.summary_df[
                self.summary_df['category'].str.contains(category, case=False, na=False) |
                self.summary_df['sub_category'].str.contains(category, case=False, na=False)
            ]
            print(f"\n🏷️ {category} 类别因子 ({len(filtered_df)} 个)")
        else:
            filtered_df = self.summary_df
            print(f"\n📋 所有因子 ({len(filtered_df)} 个)")
        
        if filtered_df.empty:
            print(f"未找到 {category} 类别的因子")
            return
        
        # 按评分排序
        filtered_df = filtered_df.sort_values('final_score', ascending=False)
        
        print("=" * 100)
        print(f"{'因子名称':<25} {'评分':<6} {'评级':<6} {'1日IC':<8} {'IC_IR':<8} {'多空收益':<10} {'子类别':<12}")
        print("-" * 100)
        
        for idx, row in filtered_df.iterrows():
            print(f"{row['factor_name']:<25} {row['final_score']:<6.3f} "
                  f"{row['overall_rating']:<6} {row['ic_1d']:<8.4f} {row['ic_ir_1d']:<8.4f} "
                  f"{row['long_short_return']:<10.4f} {row['sub_category']:<12}")
    
    def show_factor_details(self, factor_name: str):
        """显示因子详细信息"""
        # 从详细结果中查找
        factor_details = None
        for result in self.detailed_results:
            if result.get('factor_name') == factor_name:
                factor_details = result
                break
        
        if not factor_details:
            print(f"❌ 未找到因子 {factor_name} 的详细信息")
            return
        
        if "error" in factor_details:
            print(f"❌ 因子 {factor_name} 测试失败: {factor_details['error']}")
            return
        
        print(f"\n📄 {factor_name} 详细报告")
        print("=" * 80)
        
        # 基本信息
        print(f"📋 基本信息:")
        print(f"   名称: {factor_details['factor_name']}")
        print(f"   描述: {factor_details['factor_description']}")
        print(f"   类别: {factor_details['factor_category']} - {factor_details['factor_sub_category']}")
        print(f"   计算窗口: {factor_details['calculation_window']}")
        
        # 数据统计
        basic_stats = factor_details['basic_stats']
        print(f"\n📊 数据统计:")
        print(f"   总数据点: {basic_stats['total_count']}")
        print(f"   有效数据点: {basic_stats['valid_count']}")
        print(f"   有效率: {basic_stats['valid_rate']:.2%}")
        print(f"   均值: {basic_stats['mean']:.6f}")
        print(f"   标准差: {basic_stats['std']:.6f}")
        
        # 评分结果
        score_result = factor_details['score_result']
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
        ic_results = factor_details['ic_results']
        print(f"\n📊 IC分析:")
        for period, ic_data in ic_results.items():
            period_num = period.split('_')[1]
            ic = ic_data['ic']
            ic_ir = ic_data['ic_ir']
            win_rate = ic_data['ic_win_rate']
            print(f"   {period_num}期: IC={ic:.4f}, IC_IR={ic_ir:.4f}, 胜率={win_rate:.2%}")
        
        # 分层回测
        backtest = factor_details['backtest_result']
        if 'quantile_stats' in backtest:
            print(f"\n🔍 分层回测:")
            print(f"   多空收益: {backtest['long_short_return']:.4f}")
            print(f"   样本数量: {backtest['total_samples']}")
            
            print(f"\n   各分位数表现:")
            for q, stats in backtest['quantile_stats'].items():
                print(f"     {q}: 平均收益={stats['avg_return']:.4f}, "
                      f"夏普={stats['sharpe']:.3f}, 胜率={stats['win_rate']:.2%}")
    
    def search_factors(self, keyword: str):
        """搜索因子"""
        if self.summary_df.empty:
            print("❌ 无可用数据")
            return
        
        # 在因子名称和描述中搜索
        mask = (
            self.summary_df['factor_name'].str.contains(keyword, case=False, na=False) |
            self.summary_df['description'].str.contains(keyword, case=False, na=False)
        )
        
        results = self.summary_df[mask].sort_values('final_score', ascending=False)
        
        print(f"\n🔍 搜索结果: '{keyword}' ({len(results)} 个)")
        print("=" * 100)
        
        if results.empty:
            print("未找到匹配的因子")
            return
        
        print(f"{'因子名称':<25} {'评分':<6} {'评级':<6} {'1日IC':<8} {'描述':<30}")
        print("-" * 100)
        
        for idx, row in results.iterrows():
            desc = row['description'][:27] + "..." if len(row['description']) > 30 else row['description']
            print(f"{row['factor_name']:<25} {row['final_score']:<6.3f} "
                  f"{row['overall_rating']:<6} {row['ic_1d']:<8.4f} {desc:<30}")
    
    def export_results(self, output_file: str = None, top_n: int = None):
        """导出结果到文件"""
        if self.summary_df.empty:
            print("❌ 无可用数据")
            return
        
        if output_file is None:
            output_file = f"factor_analysis_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # 选择要导出的数据
        export_df = self.summary_df.copy()
        if top_n:
            export_df = export_df.head(top_n)
        
        # 添加一些计算字段
        export_df['abs_ic_1d'] = export_df['ic_1d'].abs()
        export_df['abs_ic_5d'] = export_df['ic_5d'].abs()
        
        # 保存文件
        export_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"✅ 结果已导出到: {output_file}")
        print(f"   导出因子数量: {len(export_df)}")
    
    def interactive_menu(self):
        """交互式菜单"""
        while True:
            print("\n" + "="*50)
            print("🔍 因子测试结果查看器")
            print("="*50)
            print("1. 显示汇总统计")
            print("2. 显示最佳因子")
            print("3. 按类别查看因子")
            print("4. 查看因子详情")
            print("5. 搜索因子")
            print("6. 导出结果")
            print("7. 重新加载结果")
            print("0. 退出")
            
            choice = input("\n请选择操作 (0-7): ").strip()
            
            if choice == "0":
                print("👋 再见!")
                break
            elif choice == "1":
                self.show_summary_stats()
            elif choice == "2":
                n = input("显示前几名 (默认10): ").strip()
                n = int(n) if n else 10
                min_score = input("最低评分 (默认0.4): ").strip()
                min_score = float(min_score) if min_score else 0.4
                self.show_top_factors(n=n, min_score=min_score)
            elif choice == "3":
                category = input("输入类别名称 (如momentum, volatility, 空白显示所有): ").strip()
                category = category if category else None
                self.show_factors_by_category(category)
            elif choice == "4":
                factor_name = input("输入因子名称: ").strip()
                if factor_name:
                    self.show_factor_details(factor_name)
            elif choice == "5":
                keyword = input("输入搜索关键词: ").strip()
                if keyword:
                    self.search_factors(keyword)
            elif choice == "6":
                output_file = input("输出文件名 (空白自动生成): ").strip()
                output_file = output_file if output_file else None
                top_n = input("导出前几名 (空白导出全部): ").strip()
                top_n = int(top_n) if top_n else None
                self.export_results(output_file, top_n)
            elif choice == "7":
                self.load_latest_results()
            else:
                print("⚠️ 无效选项，请重新选择")


def main():
    """主函数"""
    print("🔍 因子测试结果查看器")
    print("用途: 查看和分析因子测试结果")
    
    viewer = FactorResultsViewer()
    
    # 如果有数据，启动交互式菜单
    if not viewer.summary_df.empty:
        viewer.interactive_menu()
    else:
        print("\n❌ 未找到测试结果数据")
        print("💡 请先运行 batch_factor_test.py 进行因子测试")


if __name__ == "__main__":
    main() 