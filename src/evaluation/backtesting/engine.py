"""
简单回测引擎
用于验证因子和策略的历史表现
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable, Any  # <- 加 Any
from dataclasses import dataclass
from enum import Enum
from src.utils.logger import get_logger
from src.evaluation.metrics.performance import PerformanceAnalyzer


class OrderType(Enum):
    """订单类型"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    size: float
    entry_price: float
    entry_time: pd.Timestamp
    
    
@dataclass
class Trade:
    """交易记录"""
    symbol: str
    order_type: OrderType
    size: float
    price: float
    timestamp: pd.Timestamp
    commission: float = 0.0


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 100000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    max_position_size: float = 0.2  # 单个持仓最大占比
    lookback_days: int = 252
    rebalance_frequency: str = "1D"  # 调仓频率


class BacktestEngine:
    """简单回测引擎"""
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.logger = get_logger("backtest_engine")
        self.performance_analyzer = PerformanceAnalyzer()
        
        # 回测状态
        self.reset()
    
    # 新增：安全提取标量为 float
    @staticmethod
    def _to_float_scalar(x: Any, default: float = np.nan) -> float:
        try:
            # 将标量/数组/Series 安全转为 float
            arr = np.asarray(x)
            if arr.size == 0:
                return default
            val = float(arr.ravel()[0])
            return val
        except Exception:
            return default

    def reset(self):
        """重置回测状态"""
        self.current_cash = self.config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.portfolio_values: List[float] = []
        self.timestamps: List[pd.Timestamp] = []
        self.returns: List[float] = []
    
    def run_factor_backtest(
        self,
        factor_values: pd.Series,
        price_data: pd.DataFrame,
        strategy_func: Optional[Callable] = None
    ) -> Dict:
        """
        运行因子回测
        
        Args:
            factor_values: 因子值序列
            price_data: 价格数据 (包含open, high, low, close, volume)
            strategy_func: 策略函数（可选，默认使用简单因子策略）
            
        Returns:
            回测结果字典
        """
        try:
            if strategy_func is None:
                strategy_func = self._simple_factor_strategy
            
            self.reset()

            # 规范化价格列名（全部小写），确保存在 close
            if 'close' not in price_data.columns:
                price_data = price_data.copy()
                price_data.columns = [str(c).strip().lower() for c in price_data.columns]
            if 'close' not in price_data.columns:
                return {"error": "price_data 缺少 close 列"}

            # 对齐数据，并将因子列强制命名为 factor，避免重名歧义
            factor_series = factor_values.rename('factor')
            aligned = pd.concat([factor_series, price_data], axis=1).dropna(subset=['factor', 'close'])
            if aligned.empty or len(aligned) < 2:
                return {"error": "数据不足进行回测"}
            
            # 逐日回测
            for i, (timestamp, row) in enumerate(aligned.iterrows()):
                if i == 0:
                    self.timestamps.append(timestamp)
                    self.portfolio_values.append(self.config.initial_capital)
                    continue
                
                # 获取当前因子值和价格信息（全部转标量）
                current_factor = self._to_float_scalar(row["factor"])
                current_prices = {
                    # 使用 row.get，避免缺失列抛出 KeyError
                    'open': self._to_float_scalar(row.get('open', np.nan)),
                    'high': self._to_float_scalar(row.get('high', np.nan)),
                    'low': self._to_float_scalar(row.get('low', np.nan)),
                    'close': self._to_float_scalar(row.get('close', np.nan)),
                    'volume': self._to_float_scalar(row.get('volume', 0.0), 0.0),
                }
                if not np.isfinite(current_factor) or not np.isfinite(current_prices['close']):
                    self.timestamps.append(timestamp)
                    self.portfolio_values.append(self.portfolio_values[-1])
                    continue
                
                # 执行策略并强制信号为标量
                raw_signal = strategy_func(current_factor, current_prices, i)
                signal = self._to_float_scalar(raw_signal, 0.0)
                
                # 执行交易
                if signal != 0.0:
                    self._execute_trade("SYMBOL", signal, current_prices['close'], timestamp)
                
                # 更新投资组合价值
                portfolio_value = self._calculate_portfolio_value(current_prices['close'])
                self.portfolio_values.append(portfolio_value)
                self.timestamps.append(timestamp)
                
                # 计算收益率
                if len(self.portfolio_values) > 1:
                    prev_val = self.portfolio_values[-2]
                    daily_return = (portfolio_value - prev_val) / prev_val if prev_val != 0 else 0.0
                    self.returns.append(float(daily_return))
            
            return self._generate_backtest_results()
        except Exception as e:
            self.logger.error(f"因子回测失败: {e}")
            return {"error": str(e)}

    def run_quantile_backtest(
        self,
        factor_values: pd.Series,
        price_data: pd.DataFrame,
        quantiles: int = 5,
        long_short: bool = True
    ) -> Dict:
        """
        分层回测（多空组合）
        
        Args:
            factor_values: 因子值序列
            price_data: 价格数据
            quantiles: 分层数量
            long_short: 是否构建多空组合
            
        Returns:
            分层回测结果
        """
        try:
            # 规范化价格列名（全部小写），确保存在 close
            if 'close' not in price_data.columns:
                price_data = price_data.copy()
                price_data.columns = [str(c).strip().lower() for c in price_data.columns]
            if 'close' not in price_data.columns:
                return {"error": "price_data 缺少 close 列"}

            # 因子命名为 factor，避免与 close 重名导致 rename 冲突
            factor_series = factor_values.rename('factor')
            close_series = price_data['close'].rename('close')

            # 对齐并去 NaN
            aligned = pd.concat([factor_series, close_series], axis=1).dropna()
            if len(aligned) < quantiles * 2:
                return {"error": "数据不足进行分层"}

            # 计算下期收益
            close_ret = aligned["close"].pct_change()
            next_return = close_ret.shift(-1)
            tmp = pd.concat([aligned["factor"], next_return.rename("next_return")], axis=1).dropna()
            if tmp.empty:
                return {"error": "无有效数据"}
            
            # 分层
            tmp['quantile'] = pd.qcut(
                tmp['factor'],
                q=min(quantiles, tmp['factor'].nunique()),  # 防止唯一值过少报错
                labels=False,
                duplicates='drop'
            )
            
            # 计算各层收益率
            quantile_stats = {}
            uniq_q = sorted(tmp['quantile'].dropna().unique().tolist())
            for q in uniq_q:
                q_data = tmp[tmp['quantile'] == q]
                if len(q_data) > 0:
                    q_returns = pd.Series(q_data['next_return'].values, dtype=float)
                    quantile_stats[f'Q{int(q)+1}'] = {
                        'mean_return': float(q_returns.mean()),
                        'std_return': float(q_returns.std(ddof=1)) if len(q_returns) > 1 else 0.0,
                        'sharpe_ratio': self.performance_analyzer.calculate_sharpe_ratio(q_returns),
                        'total_return': float((1 + q_returns).prod() - 1),
                        'count': int(len(q_returns))
                    }
            
            # 多空组合（最高分位 - 最低分位）
            if long_short and len(uniq_q) >= 2:
                try:
                    high_q_val = max(uniq_q)
                    low_q_val = min(uniq_q)
                    high_q = tmp[tmp['quantile'] == high_q_val]
                    low_q = tmp[tmp['quantile'] == low_q_val]
                    if len(high_q) > 0 and len(low_q) > 0:
                        min_len = min(len(high_q), len(low_q))
                        h = pd.Series(high_q['next_return'].values[:min_len], dtype=float)
                        l = pd.Series(low_q['next_return'].values[:min_len], dtype=float)
                        ls_returns = pd.Series(h.values - l.values, dtype=float)
                        quantile_stats['LongShort'] = {
                            'mean_return': float(ls_returns.mean()),
                            'std_return': float(ls_returns.std(ddof=1)) if len(ls_returns) > 1 else 0.0,
                            'sharpe_ratio': self.performance_analyzer.calculate_sharpe_ratio(ls_returns),
                            'total_return': float((1 + ls_returns).prod() - 1),
                            'count': int(len(ls_returns))
                        }
                except Exception as e:
                    self.logger.warning(f"计算多空组合失败: {e}")
            
            return {
                'quantile_stats': quantile_stats,
                'factor_ic': float(tmp[['factor', 'next_return']].corr().iloc[0, 1]) if len(tmp) > 1 else np.nan
            }
        except Exception as e:
            self.logger.error(f"分层回测失败: {e}")
            return {"error": str(e)}

    def _simple_factor_strategy(self, factor_value: float, prices: Dict, day: int) -> float:
        """
        简单因子策略
        
        Args:
            factor_value: 当前因子值
            prices: 当前价格信息
            day: 当前天数
            
        Returns:
            交易信号 (1: 买入, -1: 卖出, 0: 无操作)
        """
        # 强制标量化，避免 Series 比较导致歧义
        fv = self._to_float_scalar(factor_value, np.nan)
        if not np.isfinite(fv):
            return 0.0
        if fv > 0.02:
            return 1.0
        elif fv < -0.02:
            return -1.0
        else:
            return 0.0
    
    def _execute_trade(self, symbol: str, signal: float, price: float, timestamp: pd.Timestamp):
        """执行交易"""
        try:
            # 计算交易成本
            commission = abs(signal) * price * self.config.commission_rate
            slippage = abs(signal) * price * self.config.slippage_rate
            total_cost = commission + slippage
            
            if signal > 0:  # 买入
                # 检查现金是否足够
                required_cash = signal * price + total_cost
                if required_cash <= self.current_cash:
                    # 执行买入
                    self.current_cash -= required_cash
                    
                    if symbol in self.positions:
                        # 更新持仓
                        pos = self.positions[symbol]
                        total_size = pos.size + signal
                        total_value = pos.size * pos.entry_price + signal * price
                        pos.size = total_size
                        pos.entry_price = total_value / total_size if total_size != 0 else price
                    else:
                        # 新建持仓
                        self.positions[symbol] = Position(
                            symbol=symbol,
                            size=signal,
                            entry_price=price,
                            entry_time=timestamp
                        )
                    
                    # 记录交易
                    self.trades.append(Trade(
                        symbol=symbol,
                        order_type=OrderType.BUY,
                        size=signal,
                        price=price,
                        timestamp=timestamp,
                        commission=total_cost
                    ))
            
            elif signal < 0:  # 卖出
                if symbol in self.positions and self.positions[symbol].size > 0:
                    # 执行卖出
                    sell_size = min(abs(signal), self.positions[symbol].size)
                    proceeds = sell_size * price - total_cost
                    self.current_cash += proceeds
                    
                    # 更新持仓
                    self.positions[symbol].size -= sell_size
                    if self.positions[symbol].size <= 0:
                        del self.positions[symbol]
                    
                    # 记录交易
                    self.trades.append(Trade(
                        symbol=symbol,
                        order_type=OrderType.SELL,
                        size=sell_size,
                        price=price,
                        timestamp=timestamp,
                        commission=total_cost
                    ))
                    
        except Exception as e:
            self.logger.error(f"执行交易失败: {e}")
    
    def _calculate_portfolio_value(self, current_price: float) -> float:
        """计算投资组合总价值"""
        try:
            total_value = self.current_cash
            
            for symbol, position in self.positions.items():
                position_value = position.size * current_price
                total_value += position_value
            
            return total_value
            
        except Exception as e:
            self.logger.error(f"计算投资组合价值失败: {e}")
            return self.current_cash
    
    def _generate_backtest_results(self) -> Dict:
        """生成回测结果"""
        try:
            if len(self.returns) == 0:
                return {"error": "无交易数据"}
            
            # 转换为pandas Series
            returns_series = pd.Series(self.returns, index=self.timestamps[1:])
            portfolio_series = pd.Series(self.portfolio_values, index=self.timestamps)
            
            # 计算性能指标
            performance_stats = self.performance_analyzer.comprehensive_analysis(returns_series)
            
            # 交易统计
            trade_stats = self._calculate_trade_stats()
            
            return {
                'performance_stats': performance_stats,
                'trade_stats': trade_stats,
                'portfolio_value': portfolio_series,
                'returns': returns_series,
                'trades': self.trades,
                'final_value': self.portfolio_values[-1] if self.portfolio_values else 0,
                'total_return': (self.portfolio_values[-1] / self.config.initial_capital - 1) if self.portfolio_values else 0
            }
            
        except Exception as e:
            self.logger.error(f"生成回测结果失败: {e}")
            return {"error": str(e)}
    
    def _calculate_trade_stats(self) -> Dict:
        """计算交易统计"""
        try:
            if not self.trades:
                return {}
            
            buy_trades = [t for t in self.trades if t.order_type == OrderType.BUY]
            sell_trades = [t for t in self.trades if t.order_type == OrderType.SELL]
            
            total_commission = sum(t.commission for t in self.trades)
            
            return {
                'total_trades': len(self.trades),
                'buy_trades': len(buy_trades),
                'sell_trades': len(sell_trades),
                'total_commission': total_commission,
                'avg_trade_size': np.mean([t.size for t in self.trades]) if self.trades else 0
            }
            
        except Exception as e:
            self.logger.error(f"计算交易统计失败: {e}")
            return {}