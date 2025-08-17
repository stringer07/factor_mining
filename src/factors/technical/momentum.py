"""
动量类技术因子
包含各种动量相关的因子计算
"""

import pandas as pd
import numpy as np
from datetime import datetime
import talib as ta
from ..base.factor import TechnicalFactor, FactorMetadata, factor_registry


class MomentumFactor(TechnicalFactor):
    """动量因子 - 价格动量"""
    
    def __init__(self, window: int = 20):
        metadata = FactorMetadata(
            name=f"momentum_{window}",
            description=f"{window}期价格动量因子",
            category="technical",
            sub_category="momentum",
            calculation_window=window + 1,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算动量因子"""
        close = data['close']
        
        # 计算收益率
        returns = close.pct_change(periods=self.window)
        
        return returns.fillna(0)


class RSIMomentumFactor(TechnicalFactor):
    """RSI动量因子"""

    def __init__(self, window: int = 14):
        metadata = FactorMetadata(
            name=f"rsi_momentum_{window}",
            description=f"{window}期RSI动量因子",
            category="technical",
            sub_category="momentum",
            calculation_window=window * 2,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window

    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算RSI动量因子"""
        close = data['close'].values
        rsi = ta.RSI(close, timeperiod=self.window)

        rsi_momentum = np.diff(rsi, prepend=np.nan)

        return pd.Series(rsi_momentum, index=data.index)

class MACDMomentumFactor(TechnicalFactor):
    """MACD动量因子"""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        metadata = FactorMetadata(
            name=f"macd_momentum_{fast}_{slow}_{signal}",
            description=f"MACD动量因子 ({fast},{slow},{signal})",
            category="technical",
            sub_category="momentum",
            calculation_window=slow + signal,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.fast = fast
        self.slow = slow
        self.signal = signal
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算MACD动量因子"""
        close = data['close']
        
        # 计算EMA
        ema_fast = close.ewm(span=self.fast).mean()
        ema_slow = close.ewm(span=self.slow).mean()

        # 计算MACD线
        macd_line = ema_fast - ema_slow
        
        # 计算信号线
        signal_line = macd_line.ewm(span=self.signal).mean()
        
        # MACD柱状图（动量）
        macd_histogram = macd_line - signal_line
        
        return macd_histogram.fillna(0)
    
class MACDMomentumFactorTA(TechnicalFactor):
    """MACD动量因子（使用TA-Lib）"""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        metadata = FactorMetadata(
            name=f"macd_momentum_{fast}_{slow}_{signal}_ta",
            description=f"MACD动量因子 ({fast},{slow},{signal})（使用TA-Lib）",
            category="technical",
            sub_category="momentum",
            calculation_window=slow + signal,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算MACD动量因子（使用TA-Lib）"""
        close = data['close'].values
        macd, signal, hist = ta.MACD(close, fastperiod=self.fast, slowperiod=self.slow, signalperiod=self.signal)

        return pd.Series(hist, index=data.index)


class VolumeMomentumFactor(TechnicalFactor):
    """成交量动量因子"""
    
    def __init__(self, window: int = 20):
        metadata = FactorMetadata(
            name=f"volume_momentum_{window}",
            description=f"{window}期成交量动量因子",
            category="technical",
            sub_category="momentum",
            calculation_window=window + 1,
            update_frequency="1d",
            data_requirements=["volume"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算成交量动量因子"""
        volume = data['volume']
        
        # 计算成交量移动平均
        volume_ma = volume.rolling(window=self.window).mean()
        
        # 成交量相对强度
        volume_momentum = volume / volume_ma - 1
        
        return volume_momentum.fillna(0)


class PriceVolumeMomentumFactor(TechnicalFactor):
    """价量动量因子"""
    
    def __init__(self, window: int = 20):
        metadata = FactorMetadata(
            name=f"price_volume_momentum_{window}",
            description=f"{window}期价量动量因子",
            category="technical",
            sub_category="momentum",
            calculation_window=window + 1,
            update_frequency="1d",
            data_requirements=["close", "volume"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算价量动量因子"""
        close = data['close']
        volume = data['volume']
        
        # 计算价格变化
        price_change = close.pct_change()
        
        # 计算成交量变化
        volume_change = volume.pct_change()
        
        # 价量动量 = 价格动量 * 成交量动量的符号
        pv_momentum = price_change * np.sign(volume_change)
        
        # 滑动平均平滑
        pv_momentum_smooth = pv_momentum.rolling(window=self.window).mean()
        
        return pv_momentum_smooth.fillna(0)


class AccelerationFactor(TechnicalFactor):
    """价格加速度因子"""
    
    def __init__(self, window: int = 10):
        metadata = FactorMetadata(
            name=f"acceleration_{window}",
            description=f"{window}期价格加速度因子",
            category="technical",
            sub_category="momentum",
            calculation_window=window + 2,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算价格加速度因子"""
        close = data['close']
        
        # 计算一阶差分（速度）
        velocity = close.diff()
        
        # 计算二阶差分（加速度）
        acceleration = velocity.diff()
        
        # 平滑处理
        acceleration_smooth = acceleration.rolling(window=self.window).mean()
        
        return acceleration_smooth.fillna(0)


class ROCFactor(TechnicalFactor):
    """变化率因子 (Rate of Change)"""
    
    def __init__(self, window: int = 12):
        metadata = FactorMetadata(
            name=f"roc_{window}",
            description=f"{window}期变化率因子",
            category="technical",
            sub_category="momentum",
            calculation_window=window + 1,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算ROC因子"""
        close = data['close']
        
        # ROC = (当前价格 - N期前价格) / N期前价格 * 100
        roc = ((close - close.shift(self.window)) / close.shift(self.window)) * 100
        
        return roc.fillna(0)


# 注册所有动量因子
def register_momentum_factors():
    """注册所有动量因子"""
    factors = [
        MomentumFactor(10),
        MomentumFactor(20),
        MomentumFactor(60),
        RSIMomentumFactor(14),
        MACDMomentumFactor(),
        MACDMomentumFactorTA(),
        VolumeMomentumFactor(20),
        PriceVolumeMomentumFactor(20),
        AccelerationFactor(10),
        ROCFactor(12),
        ROCFactor(24)
    ]
    
    for factor in factors:
        factor_registry.register(factor)


# 自动注册
register_momentum_factors() 