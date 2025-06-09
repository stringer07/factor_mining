"""
IC分析器
信息系数（Information Coefficient）分析工具
用于评估因子的预测能力
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from scipy import stats
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ICAnalyzer:
    """IC分析器"""
    
    def __init__(self):
        self.logger = get_logger("ic_analyzer")
    
    def calculate_ic(
        self, 
        factor_values: pd.Series, 
        returns: pd.Series,
        method: str = "pearson"
    ) -> float:
        """
        计算信息系数
        
        Args:
            factor_values: 因子值序列
            returns: 收益率序列
            method: 相关系数方法 ('pearson', 'spearman', 'kendall')
            
        Returns:
            IC值
        """
        try:
            # 对齐数据
            aligned_data = pd.concat([factor_values, returns], axis=1).dropna()
            if len(aligned_data) < 2:
                return np.nan
            
            factor_col = aligned_data.iloc[:, 0]
            return_col = aligned_data.iloc[:, 1]
            
            # 计算相关系数
            if method == "pearson":
                ic, _ = stats.pearsonr(factor_col, return_col)
            elif method == "spearman":
                ic, _ = stats.spearmanr(factor_col, return_col)
            elif method == "kendall":
                ic, _ = stats.kendalltau(factor_col, return_col)
            else:
                raise ValueError(f"不支持的方法: {method}")
            
            return ic if not np.isnan(ic) else 0.0
            
        except Exception as e:
            self.logger.error(f"计算IC失败: {e}")
            return np.nan
    
    def calculate_rolling_ic(
        self,
        factor_values: pd.Series,
        returns: pd.Series,
        window: int = 30,
        method: str = "pearson"
    ) -> pd.Series:
        """
        计算滚动IC
        
        Args:
            factor_values: 因子值序列
            returns: 收益率序列
            window: 滚动窗口大小
            method: 相关系数方法
            
        Returns:
            滚动IC序列
        """
        try:
            # 对齐数据
            aligned_data = pd.concat([factor_values, returns], axis=1).dropna()
            if len(aligned_data) < window:
                return pd.Series(dtype=float)
            
            # 计算滚动IC
            rolling_ic = pd.Series(index=aligned_data.index, dtype=float)
            
            for i in range(window - 1, len(aligned_data)):
                window_data = aligned_data.iloc[i - window + 1:i + 1]
                factor_window = window_data.iloc[:, 0]
                return_window = window_data.iloc[:, 1]
                
                # 计算相关系数
                ic_value = self.calculate_ic(factor_window, return_window, method)
                rolling_ic.iloc[i] = ic_value
            
            return rolling_ic
            
        except Exception as e:
            self.logger.error(f"计算滚动IC失败: {e}")
            return pd.Series(dtype=float)
    
    def calculate_ic_ir(
        self,
        factor_values: pd.Series,
        returns: pd.Series,
        window: int = 30,
        method: str = "pearson"
    ) -> float:
        """
        计算IC信息比率 (IC_IR)
        
        Args:
            factor_values: 因子值序列
            returns: 收益率序列
            window: 滚动窗口大小
            method: 相关系数方法
            
        Returns:
            IC_IR值
        """
        try:
            rolling_ic = self.calculate_rolling_ic(factor_values, returns, window, method)
            
            if len(rolling_ic.dropna()) < 2:
                return np.nan
            
            ic_mean = rolling_ic.mean()
            ic_std = rolling_ic.std()
            
            if ic_std == 0:
                return np.nan
            
            ic_ir = ic_mean / ic_std
            return ic_ir
            
        except Exception as e:
            self.logger.error(f"计算IC_IR失败: {e}")
            return np.nan
    
    def calculate_ic_stats(
        self,
        factor_values: pd.Series,
        returns: pd.Series,
        periods: List[int] = [1, 3, 5, 10, 20]
    ) -> Dict:
        """
        计算多期IC统计指标
        
        Args:
            factor_values: 因子值序列
            returns: 收益率序列
            periods: 预测期数列表
            
        Returns:
            IC统计结果字典
        """
        try:
            results = {}
            
            for period in periods:
                # 计算前瞻收益率
                forward_returns = returns.shift(-period)
                
                # 计算IC
                ic = self.calculate_ic(factor_values, forward_returns)
                
                # 计算滚动IC
                rolling_ic = self.calculate_rolling_ic(factor_values, forward_returns)
                
                # 计算IC统计
                ic_stats = {
                    'ic': ic,
                    'ic_mean': rolling_ic.mean(),
                    'ic_std': rolling_ic.std(),
                    'ic_ir': self.calculate_ic_ir(factor_values, forward_returns),
                    'ic_win_rate': (rolling_ic > 0).mean(),
                    'ic_positive_rate': (rolling_ic > 0.02).mean(),
                    'ic_negative_rate': (rolling_ic < -0.02).mean()
                }
                
                results[f'period_{period}'] = ic_stats
            
            return results
            
        except Exception as e:
            self.logger.error(f"计算IC统计失败: {e}")
            return {}
    
    def calculate_ic_decay(
        self,
        factor_values: pd.Series,
        returns: pd.Series,
        max_period: int = 20
    ) -> pd.Series:
        """
        计算IC衰减
        
        Args:
            factor_values: 因子值序列
            returns: 收益率序列
            max_period: 最大预测期数
            
        Returns:
            IC衰减序列
        """
        try:
            ic_decay = pd.Series(index=range(1, max_period + 1), dtype=float)
            
            for period in range(1, max_period + 1):
                forward_returns = returns.shift(-period)
                ic = self.calculate_ic(factor_values, forward_returns)
                ic_decay[period] = ic
            
            return ic_decay
            
        except Exception as e:
            self.logger.error(f"计算IC衰减失败: {e}")
            return pd.Series(dtype=float)
    
    def rank_ic_analysis(
        self,
        factor_values: pd.Series,
        returns: pd.Series,
        quantiles: int = 5
    ) -> Dict:
        """
        分层IC分析
        
        Args:
            factor_values: 因子值序列
            returns: 收益率序列
            quantiles: 分层数量
            
        Returns:
            分层IC分析结果
        """
        try:
            # 对齐数据
            aligned_data = pd.concat([factor_values, returns], axis=1).dropna()
            if len(aligned_data) < quantiles * 2:
                return {}
            
            factor_col = aligned_data.iloc[:, 0]
            return_col = aligned_data.iloc[:, 1]
            
            # 因子分层
            factor_quantiles = pd.qcut(factor_col, q=quantiles, labels=False, duplicates='drop')
            
            # 计算各层收益率
            quantile_returns = {}
            for q in range(quantiles):
                mask = factor_quantiles == q
                if mask.any():
                    quantile_returns[f'Q{q+1}'] = return_col[mask].mean()
            
            # 计算多空收益率
            if len(quantile_returns) >= 2:
                long_short_return = quantile_returns[f'Q{quantiles}'] - quantile_returns['Q1']
            else:
                long_short_return = np.nan
            
            return {
                'quantile_returns': quantile_returns,
                'long_short_return': long_short_return,
                'monotonicity': self._check_monotonicity(list(quantile_returns.values()))
            }
            
        except Exception as e:
            self.logger.error(f"分层IC分析失败: {e}")
            return {}
    
    def _check_monotonicity(self, values: List[float]) -> float:
        """检查单调性"""
        if len(values) < 2:
            return np.nan
        
        diffs = np.diff(values)
        positive_diffs = np.sum(diffs > 0)
        negative_diffs = np.sum(diffs < 0)
        total_diffs = len(diffs)
        
        if total_diffs == 0:
            return 0.0
        
        # 单调性得分
        monotonicity = (positive_diffs - negative_diffs) / total_diffs
        return monotonicity
    
    def comprehensive_analysis(
        self,
        factor_values: pd.Series,
        price_data: pd.DataFrame,
        periods: List[int] = [1, 5, 10, 20]
    ) -> Dict:
        """
        综合IC分析
        
        Args:
            factor_values: 因子值序列
            price_data: 价格数据 (包含close列)
            periods: 分析期数列表
            
        Returns:
            综合分析结果
        """
        try:
            # 计算收益率
            returns = price_data['close'].pct_change()
            
            results = {
                'basic_ic_stats': {},
                'rolling_ic_stats': {},
                'ic_decay': self.calculate_ic_decay(factor_values, returns),
                'rank_analysis': self.rank_ic_analysis(factor_values, returns)
            }
            
            # 基础IC统计
            results['basic_ic_stats'] = self.calculate_ic_stats(factor_values, returns, periods)
            
            # 滚动IC统计
            for window in [20, 60, 120]:
                rolling_ic = self.calculate_rolling_ic(factor_values, returns, window)
                results['rolling_ic_stats'][f'window_{window}'] = {
                    'mean': rolling_ic.mean(),
                    'std': rolling_ic.std(),
                    'min': rolling_ic.min(),
                    'max': rolling_ic.max(),
                    'positive_rate': (rolling_ic > 0).mean()
                }
            
            return results
            
        except Exception as e:
            self.logger.error(f"综合IC分析失败: {e}")
            return {} 