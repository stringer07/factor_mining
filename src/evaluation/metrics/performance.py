"""
性能分析器
提供策略回测性能分析功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from src.utils.logger import get_logger
from typing import Union, Sequence


class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self):
        self.logger = get_logger("performance_analyzer")

    def _to_series(self, returns: Union[pd.Series, np.ndarray, Sequence[float]]) -> pd.Series:
        try:
            if returns is None:
                return pd.Series(dtype=float)
            if isinstance(returns, pd.Series):
                s = returns
            else:
                s = pd.Series(returns, dtype=float)
            # 清理无穷与缺失
            return s.astype(float).replace([np.inf, -np.inf], np.nan).dropna()
        except Exception:
            # 回退为空
            return pd.Series(dtype=float)
    
    def calculate_returns(self, prices: pd.Series) -> pd.Series:
        """计算收益率"""
        return prices.pct_change().fillna(0)
    
    def calculate_cumulative_returns(self, returns: pd.Series) -> pd.Series:
        """计算累计收益率"""
        return (1 + returns).cumprod() - 1
    
    def calculate_sharpe_ratio(
        self, 
        returns: Union[pd.Series, np.ndarray, Sequence[float]], 
        risk_free_rate: float = 0.02,
        periods_per_year: int = 252
    ) -> float:
        try:
            r = self._to_series(returns)
            if r.empty:
                return np.nan

            # 使用标准差（样本）并做健壮性检查
            std = r.std(ddof=1)
            if not np.isfinite(std) or std == 0:
                return np.nan

            annual_return = r.mean() * periods_per_year
            annual_volatility = std * np.sqrt(periods_per_year)
            if not np.isfinite(annual_volatility) or annual_volatility == 0:
                return np.nan

            sharpe = (annual_return - risk_free_rate) / annual_volatility
            return float(sharpe)
        except Exception as e:
            self.logger.error(f"计算夏普比率失败: {e}")
            return np.nan
    
    def calculate_max_drawdown(self, returns: pd.Series) -> Dict:
        """
        计算最大回撤
        
        Returns:
            包含最大回撤、开始时间、结束时间等信息的字典
        """
        try:
            if len(returns) == 0:
                return {}
            
            # 计算累计收益率
            cumulative = self.calculate_cumulative_returns(returns)
            
            # 计算累计最高点
            running_max = cumulative.expanding().max()
            
            # 计算回撤
            drawdown = (cumulative - running_max) / (1 + running_max)
            
            # 最大回撤
            max_drawdown = drawdown.min()
            
            # 找到最大回撤的时间点
            max_dd_end = drawdown.idxmin()
            max_dd_start = cumulative.loc[:max_dd_end].idxmax()
            
            # 计算回撤持续时间
            if pd.notna(max_dd_start) and pd.notna(max_dd_end):
                try:
                    if isinstance(max_dd_start, str):
                        max_dd_start = pd.to_datetime(max_dd_start)
                    if isinstance(max_dd_end, str):
                        max_dd_end = pd.to_datetime(max_dd_end)
                    
                    # 如果索引是整数，则使用索引差值
                    if isinstance(max_dd_start, (int, np.integer)) or isinstance(max_dd_end, (int, np.integer)):
                        duration = int(max_dd_end) - int(max_dd_start)
                    else:
                        # 如果是datetime，计算天数差
                        duration = (max_dd_end - max_dd_start).days
                except:
                    duration = 0
            else:
                duration = 0
            
            return {
                'max_drawdown': max_drawdown,
                'max_drawdown_start': max_dd_start,
                'max_drawdown_end': max_dd_end,
                'max_drawdown_duration': duration,
                'drawdown_series': drawdown
            }
            
        except Exception as e:
            self.logger.error(f"计算最大回撤失败: {e}")
            return {}
    
    def calculate_calmar_ratio(self, returns: pd.Series, periods_per_year: int = 252) -> float:
        """计算卡玛比率"""
        try:
            annual_return = returns.mean() * periods_per_year
            max_dd_info = self.calculate_max_drawdown(returns)
            
            if not max_dd_info or max_dd_info.get('max_drawdown', 0) == 0:
                return np.nan
            
            calmar = annual_return / abs(max_dd_info['max_drawdown'])
            return calmar
            
        except Exception as e:
            self.logger.error(f"计算卡玛比率失败: {e}")
            return np.nan
    
    def calculate_sortino_ratio(
        self, 
        returns: pd.Series, 
        risk_free_rate: float = 0.02,
        periods_per_year: int = 252
    ) -> float:
        """计算索提诺比率"""
        try:
            annual_return = returns.mean() * periods_per_year
            
            # 下行标准差
            negative_returns = returns[returns < 0]
            downside_std = negative_returns.std() * np.sqrt(periods_per_year)
            
            if downside_std == 0:
                return np.nan
            
            sortino = (annual_return - risk_free_rate) / downside_std
            return sortino
            
        except Exception as e:
            self.logger.error(f"计算索提诺比率失败: {e}")
            return np.nan
    
    def calculate_win_rate(self, returns: pd.Series) -> float:
        """计算胜率"""
        try:
            if len(returns) == 0:
                return np.nan
            
            win_rate = (returns > 0).mean()
            return win_rate
            
        except Exception as e:
            self.logger.error(f"计算胜率失败: {e}")
            return np.nan
    
    def calculate_profit_loss_ratio(self, returns: pd.Series) -> float:
        """计算盈亏比"""
        try:
            positive_returns = returns[returns > 0]
            negative_returns = returns[returns < 0]
            
            if len(positive_returns) == 0 or len(negative_returns) == 0:
                return np.nan
            
            avg_profit = positive_returns.mean()
            avg_loss = abs(negative_returns.mean())
            
            if avg_loss == 0:
                return np.nan
            
            pl_ratio = avg_profit / avg_loss
            return pl_ratio
            
        except Exception as e:
            self.logger.error(f"计算盈亏比失败: {e}")
            return np.nan
    
    def calculate_volatility(self, returns: pd.Series, periods_per_year: int = 252) -> float:
        """计算年化波动率"""
        try:
            if len(returns) == 0:
                return np.nan
            
            volatility = returns.std() * np.sqrt(periods_per_year)
            return volatility
            
        except Exception as e:
            self.logger.error(f"计算波动率失败: {e}")
            return np.nan
    
    def calculate_skewness(self, returns: pd.Series) -> float:
        """计算偏度"""
        try:
            if len(returns) < 3:
                return np.nan
            
            skewness = returns.skew()
            return skewness
            
        except Exception as e:
            self.logger.error(f"计算偏度失败: {e}")
            return np.nan
    
    def calculate_kurtosis(self, returns: pd.Series) -> float:
        """计算峰度"""
        try:
            if len(returns) < 4:
                return np.nan
            
            kurtosis = returns.kurtosis()
            return kurtosis
            
        except Exception as e:
            self.logger.error(f"计算峰度失败: {e}")
            return np.nan
    
    def calculate_var(self, returns: pd.Series, confidence_level: float = 0.05) -> float:
        """计算风险价值 (VaR)"""
        try:
            if len(returns) == 0:
                return np.nan
            
            var = returns.quantile(confidence_level)
            return var
            
        except Exception as e:
            self.logger.error(f"计算VaR失败: {e}")
            return np.nan
    
    def calculate_cvar(self, returns: pd.Series, confidence_level: float = 0.05) -> float:
        """计算条件风险价值 (CVaR)"""
        try:
            if len(returns) == 0:
                return np.nan
            
            var = self.calculate_var(returns, confidence_level)
            cvar = returns[returns <= var].mean()
            return cvar
            
        except Exception as e:
            self.logger.error(f"计算CVaR失败: {e}")
            return np.nan
    
    def calculate_information_ratio(
        self, 
        strategy_returns: pd.Series, 
        benchmark_returns: pd.Series
    ) -> float:
        """计算信息比率"""
        try:
            # 超额收益
            excess_returns = strategy_returns - benchmark_returns
            
            if len(excess_returns) == 0:
                return np.nan
            
            # 跟踪误差
            tracking_error = excess_returns.std()
            
            if tracking_error == 0:
                return np.nan
            
            # 信息比率
            ir = excess_returns.mean() / tracking_error
            return ir
            
        except Exception as e:
            self.logger.error(f"计算信息比率失败: {e}")
            return np.nan
    
    def calculate_beta(
        self, 
        strategy_returns: pd.Series, 
        market_returns: pd.Series
    ) -> float:
        """计算贝塔系数"""
        try:
            # 对齐数据
            aligned_data = pd.concat([strategy_returns, market_returns], axis=1).dropna()
            if len(aligned_data) < 2:
                return np.nan
            
            strategy_aligned = aligned_data.iloc[:, 0]
            market_aligned = aligned_data.iloc[:, 1]
            
            # 计算贝塔
            covariance = np.cov(strategy_aligned, market_aligned)[0, 1]
            market_variance = np.var(market_aligned)
            
            if market_variance == 0:
                return np.nan
            
            beta = covariance / market_variance
            return beta
            
        except Exception as e:
            self.logger.error(f"计算贝塔系数失败: {e}")
            return np.nan
    
    def comprehensive_analysis(
        self, 
        returns: Union[pd.Series, np.ndarray, Sequence[float]],
        benchmark_returns: Optional[pd.Series] = None,
        risk_free_rate: float = 0.02,
        periods_per_year: int = 252
    ) -> Dict:
        """
        综合性能分析
        
        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列（可选）
            risk_free_rate: 无风险收益率
            periods_per_year: 年化周期数
            
        Returns:
            综合分析结果字典
        """
        try:
            r = self._to_series(returns)
            if r.empty:
                return {}

            # 基础统计
            total_return = self.calculate_cumulative_returns(r).iloc[-1]
            annual_return = r.mean() * periods_per_year
            volatility = self.calculate_volatility(r, periods_per_year)
            
            # 风险调整指标
            sharpe = self.calculate_sharpe_ratio(r, risk_free_rate, periods_per_year)
            sortino = self.calculate_sortino_ratio(r, risk_free_rate, periods_per_year)
            calmar = self.calculate_calmar_ratio(r, periods_per_year)
            
            # 回撤分析
            drawdown_info = self.calculate_max_drawdown(r)
            
            # 分布特征
            skewness = self.calculate_skewness(returns)
            kurtosis = self.calculate_kurtosis(returns)
            
            # 风险指标
            var_5 = self.calculate_var(returns, 0.05)
            cvar_5 = self.calculate_cvar(returns, 0.05)
            
            # 胜率和盈亏比
            win_rate = self.calculate_win_rate(returns)
            pl_ratio = self.calculate_profit_loss_ratio(returns)
            
            results = {
                'total_return': total_return,
                'annual_return': annual_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe,
                'sortino_ratio': sortino,
                'calmar_ratio': calmar,
                'max_drawdown': drawdown_info.get('max_drawdown', np.nan),
                'max_drawdown_duration': drawdown_info.get('max_drawdown_duration', np.nan),
                'win_rate': win_rate,
                'profit_loss_ratio': pl_ratio,
                'skewness': skewness,
                'kurtosis': kurtosis,
                'var_5pct': var_5,
                'cvar_5pct': cvar_5
            }
            
            # 如果提供了基准，计算相对指标
            if benchmark_returns is not None:
                try:
                    ir = self.calculate_information_ratio(r, benchmark_returns)
                    beta = self.calculate_beta(r, benchmark_returns)
                    
                    results.update({
                        'information_ratio': ir,
                        'beta': beta
                    })
                except Exception as e:
                    self.logger.warning(f"计算相对指标失败: {e}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"综合性能分析失败: {e}")
            return {}
    
    def rolling_analysis(
        self,
        returns: pd.Series,
        window: int = 252,
        metrics: List[str] = None
    ) -> pd.DataFrame:
        """
        滚动性能分析
        
        Args:
            returns: 收益率序列
            window: 滚动窗口大小
            metrics: 需要计算的指标列表
            
        Returns:
            滚动指标DataFrame
        """
        try:
            if metrics is None:
                metrics = ['sharpe_ratio', 'volatility', 'max_drawdown']
            
            rolling_results = pd.DataFrame(index=returns.index)
            
            for metric in metrics:
                if metric == 'sharpe_ratio':
                    rolling_results[metric] = returns.rolling(window).apply(
                        lambda x: self.calculate_sharpe_ratio(x), raw=False
                    )
                elif metric == 'volatility':
                    rolling_results[metric] = returns.rolling(window).apply(
                        lambda x: self.calculate_volatility(x), raw=False
                    )
                elif metric == 'max_drawdown':
                    rolling_results[metric] = returns.rolling(window).apply(
                        lambda x: self.calculate_max_drawdown(x).get('max_drawdown', np.nan), 
                        raw=False
                    )
            
            return rolling_results
            
        except Exception as e:
            self.logger.error(f"滚动分析失败: {e}")
            return pd.DataFrame() 