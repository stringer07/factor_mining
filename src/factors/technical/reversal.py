"""
反转类技术因子
包含各种反转相关的因子计算
"""

import pandas as pd
import numpy as np
from datetime import datetime
from ..base.factor import TechnicalFactor, FactorMetadata, factor_registry


class ReversalFactor(TechnicalFactor):
    """短期反转因子"""
    
    def __init__(self, window: int = 5):
        metadata = FactorMetadata(
            name=f"reversal_{window}",
            description=f"{window}期短期反转因子",
            category="technical",
            sub_category="reversal",
            calculation_window=window + 1,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算短期反转因子"""
        close = data['close']
        
        # 计算反转信号（负的收益率）
        returns = close.pct_change(periods=self.window)
        reversal_signal = -returns  # 反转信号与收益率相反
        
        return reversal_signal.fillna(0)


class RSIReversalFactor(TechnicalFactor):
    """RSI反转因子"""
    
    def __init__(self, window: int = 14, oversold: float = 30, overbought: float = 70):
        metadata = FactorMetadata(
            name=f"rsi_reversal_{window}",
            description=f"{window}期RSI反转因子",
            category="technical",
            sub_category="reversal", 
            calculation_window=window * 2,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
        self.oversold = oversold
        self.overbought = overbought
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算RSI反转因子"""
        close = data['close']
        
        # 计算RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=self.window).mean()
        avg_loss = loss.rolling(window=self.window).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # 生成反转信号
        reversal_signal = pd.Series(0, index=rsi.index)
        reversal_signal[rsi < self.oversold] = 1   # 超卖，看涨
        reversal_signal[rsi > self.overbought] = -1  # 超买，看跌
        
        return reversal_signal


class StochasticReversalFactor(TechnicalFactor):
    """随机指标反转因子"""
    
    def __init__(self, k_window: int = 14, d_window: int = 3):
        metadata = FactorMetadata(
            name=f"stochastic_reversal_{k_window}_{d_window}",
            description=f"随机指标反转因子 ({k_window},{d_window})",
            category="technical",
            sub_category="reversal",
            calculation_window=k_window + d_window,
            update_frequency="1d",
            data_requirements=["high", "low", "close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.k_window = k_window
        self.d_window = d_window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算随机指标反转因子"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        # 计算%K
        lowest_low = low.rolling(window=self.k_window).min()
        highest_high = high.rolling(window=self.k_window).max()
        k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
        
        # 计算%D
        d_percent = k_percent.rolling(window=self.d_window).mean()
        
        # 生成反转信号
        reversal_signal = pd.Series(0, index=d_percent.index)
        reversal_signal[d_percent < 20] = 1   # 超卖
        reversal_signal[d_percent > 80] = -1  # 超买
        
        return reversal_signal


class WilliamsRReversalFactor(TechnicalFactor):
    """威廉指标反转因子"""
    
    def __init__(self, window: int = 14):
        metadata = FactorMetadata(
            name=f"williams_r_reversal_{window}",
            description=f"{window}期威廉指标反转因子",
            category="technical",
            sub_category="reversal",
            calculation_window=window,
            update_frequency="1d",
            data_requirements=["high", "low", "close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算威廉指标反转因子"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        # 计算Williams %R
        highest_high = high.rolling(window=self.window).max()
        lowest_low = low.rolling(window=self.window).min()
        williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)
        
        # 生成反转信号
        reversal_signal = pd.Series(0, index=williams_r.index)
        reversal_signal[williams_r > -20] = -1  # 超买
        reversal_signal[williams_r < -80] = 1   # 超卖
        
        return reversal_signal


class BollingerReversalFactor(TechnicalFactor):
    """布林带反转因子"""
    
    def __init__(self, window: int = 20, std_dev: float = 2.0):
        metadata = FactorMetadata(
            name=f"bollinger_reversal_{window}_{std_dev}",
            description=f"{window}期布林带反转因子",
            category="technical",
            sub_category="reversal",
            calculation_window=window,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
        self.std_dev = std_dev
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算布林带反转因子"""
        close = data['close']
        
        # 计算布林带
        sma = close.rolling(window=self.window).mean()
        std = close.rolling(window=self.window).std()
        upper_band = sma + (std * self.std_dev)
        lower_band = sma - (std * self.std_dev)
        
        # 计算价格相对位置
        bb_position = (close - lower_band) / (upper_band - lower_band)
        
        # 生成反转信号
        reversal_signal = pd.Series(0, index=bb_position.index)
        reversal_signal[bb_position > 0.9] = -1  # 接近上轨，看跌
        reversal_signal[bb_position < 0.1] = 1   # 接近下轨，看涨
        
        return reversal_signal


class MeanReversionFactor(TechnicalFactor):
    """均值回归因子"""
    
    def __init__(self, short_window: int = 5, long_window: int = 20):
        metadata = FactorMetadata(
            name=f"mean_reversion_{short_window}_{long_window}",
            description=f"均值回归因子 ({short_window},{long_window})",
            category="technical",
            sub_category="reversal",
            calculation_window=long_window,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.short_window = short_window
        self.long_window = long_window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算均值回归因子"""
        close = data['close']
        
        # 计算短期和长期移动平均
        short_ma = close.rolling(window=self.short_window).mean()
        long_ma = close.rolling(window=self.long_window).mean()
        
        # 计算偏离度
        deviation = (short_ma - long_ma) / long_ma
        
        # 反转信号（与偏离度相反）
        mean_reversion = -deviation
        
        return mean_reversion.fillna(0)


class VolumeReversalFactor(TechnicalFactor):
    """成交量反转因子"""
    
    def __init__(self, window: int = 20):
        metadata = FactorMetadata(
            name=f"volume_reversal_{window}",
            description=f"{window}期成交量反转因子",
            category="technical",
            sub_category="reversal",
            calculation_window=window + 1,
            update_frequency="1d",
            data_requirements=["close", "volume"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算成交量反转因子"""
        close = data['close']
        volume = data['volume']
        
        # 计算价格变化和成交量变化
        price_change = close.pct_change()
        volume_ma = volume.rolling(window=self.window).mean()
        volume_ratio = volume / volume_ma
        
        # 高成交量且价格下跌 -> 反转看涨
        # 高成交量且价格上涨 -> 反转看跌
        reversal_signal = pd.Series(0, index=close.index)
        
        high_volume = volume_ratio > 1.5
        reversal_signal[high_volume & (price_change < -0.02)] = 1   # 大跌后反转
        reversal_signal[high_volume & (price_change > 0.02)] = -1  # 大涨后反转
        
        return reversal_signal


class CommodityChannelReversalFactor(TechnicalFactor):
    """商品通道指数反转因子"""
    
    def __init__(self, window: int = 20):
        metadata = FactorMetadata(
            name=f"cci_reversal_{window}",
            description=f"{window}期CCI反转因子",
            category="technical",
            sub_category="reversal",
            calculation_window=window,
            update_frequency="1d",
            data_requirements=["high", "low", "close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算CCI反转因子"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        # 计算典型价格
        typical_price = (high + low + close) / 3
        
        # 计算CCI
        sma_tp = typical_price.rolling(window=self.window).mean()
        mad = typical_price.rolling(window=self.window).apply(
            lambda x: np.mean(np.abs(x - x.mean()))
        )
        cci = (typical_price - sma_tp) / (0.015 * mad)
        
        # 生成反转信号
        reversal_signal = pd.Series(0, index=cci.index)
        reversal_signal[cci > 100] = -1  # 超买
        reversal_signal[cci < -100] = 1  # 超卖
        
        return reversal_signal


# 注册所有反转因子
def register_reversal_factors():
    """注册所有反转因子"""
    factors = [
        ReversalFactor(3),
        ReversalFactor(5),
        ReversalFactor(10),
        RSIReversalFactor(14),
        StochasticReversalFactor(14, 3),
        WilliamsRReversalFactor(14),
        BollingerReversalFactor(20, 2.0),
        MeanReversionFactor(5, 20),
        VolumeReversalFactor(20),
        CommodityChannelReversalFactor(20)
    ]
    
    for factor in factors:
        factor_registry.register(factor)


# 自动注册
register_reversal_factors() 