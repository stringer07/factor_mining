"""
波动率类技术因子
包含各种波动率相关的因子计算
"""

import pandas as pd
import numpy as np
from datetime import datetime
from ..base.factor import TechnicalFactor, FactorMetadata, factor_registry


class VolatilityFactor(TechnicalFactor):
    """历史波动率因子"""
    
    def __init__(self, window: int = 20):
        metadata = FactorMetadata(
            name=f"volatility_{window}",
            description=f"{window}期历史波动率因子",
            category="technical",
            sub_category="volatility",
            calculation_window=window + 1,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算历史波动率"""
        close = data['close']
        
        # 计算对数收益率
        returns = np.log(close / close.shift(1))
        
        # 计算滚动标准差（年化）
        volatility = returns.rolling(window=self.window).std() * np.sqrt(252)
        
        return volatility.fillna(0)


class ATRFactor(TechnicalFactor):
    """真实波幅因子 (Average True Range)"""
    
    def __init__(self, window: int = 14):
        metadata = FactorMetadata(
            name=f"atr_{window}",
            description=f"{window}期真实波幅因子",
            category="technical", 
            sub_category="volatility",
            calculation_window=window + 1,
            update_frequency="1d",
            data_requirements=["high", "low", "close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算ATR"""
        high = data['high']
        low = data['low']
        close = data['close']
        prev_close = close.shift(1)
        
        # 计算真实波幅
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 计算ATR
        atr = true_range.rolling(window=self.window).mean()
        
        return atr.fillna(0)


class BollingerVolatilityFactor(TechnicalFactor):
    """布林带波动率因子"""
    
    def __init__(self, window: int = 20, std_dev: float = 2.0):
        metadata = FactorMetadata(
            name=f"bollinger_volatility_{window}_{std_dev}",
            description=f"{window}期布林带波动率因子",
            category="technical",
            sub_category="volatility",
            calculation_window=window,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
        self.std_dev = std_dev
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算布林带波动率"""
        close = data['close']
        
        # 计算移动平均和标准差
        sma = close.rolling(window=self.window).mean()
        std = close.rolling(window=self.window).std()
        
        # 布林带宽度（标准化波动率）
        bb_width = (std * self.std_dev * 2) / sma
        
        return bb_width.fillna(0)


class GARCHVolatilityFactor(TechnicalFactor):
    """GARCH波动率因子（简化版）"""
    
    def __init__(self, window: int = 30, alpha: float = 0.1, beta: float = 0.85):
        metadata = FactorMetadata(
            name=f"garch_volatility_{window}",
            description=f"{window}期GARCH波动率因子",
            category="technical",
            sub_category="volatility",
            calculation_window=window + 1,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
        self.alpha = alpha
        self.beta = beta
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算GARCH波动率"""
        close = data['close']
        
        # 计算收益率
        returns = close.pct_change().fillna(0)
        
        # 初始化方差序列
        variance = pd.Series(index=returns.index, dtype=float)
        
        # 计算初始方差
        initial_var = returns.head(self.window).var()
        variance.iloc[:self.window] = initial_var
        
        # GARCH(1,1)模型
        for i in range(self.window, len(returns)):
            if i > 0:
                variance.iloc[i] = (
                    (1 - self.alpha - self.beta) * returns.iloc[:i].var() +
                    self.alpha * returns.iloc[i-1]**2 +
                    self.beta * variance.iloc[i-1]
                )
        
        # 返回波动率（方差的平方根）
        volatility = np.sqrt(variance)
        
        return volatility.fillna(0)


class VolatilitySkewFactor(TechnicalFactor):
    """波动率偏度因子"""
    
    def __init__(self, window: int = 20):
        metadata = FactorMetadata(
            name=f"volatility_skew_{window}",
            description=f"{window}期波动率偏度因子",
            category="technical",
            sub_category="volatility",
            calculation_window=window + 1,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算波动率偏度"""
        close = data['close']
        
        # 计算收益率
        returns = close.pct_change()
        
        # 计算滚动偏度
        skewness = returns.rolling(window=self.window).skew()
        
        return skewness.fillna(0)


class VolatilityKurtosisFactor(TechnicalFactor):
    """波动率峰度因子"""
    
    def __init__(self, window: int = 20):
        metadata = FactorMetadata(
            name=f"volatility_kurtosis_{window}",
            description=f"{window}期波动率峰度因子",
            category="technical",
            sub_category="volatility",
            calculation_window=window + 1,
            update_frequency="1d",
            data_requirements=["close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算波动率峰度"""
        close = data['close']
        
        # 计算收益率
        returns = close.pct_change()
        
        # 计算滚动峰度
        kurtosis = returns.rolling(window=self.window).kurt()
        
        return kurtosis.fillna(0)


class RealizedVolatilityFactor(TechnicalFactor):
    """已实现波动率因子"""
    
    def __init__(self, window: int = 20):
        metadata = FactorMetadata(
            name=f"realized_volatility_{window}",
            description=f"{window}期已实现波动率因子",
            category="technical",
            sub_category="volatility",
            calculation_window=window + 1,
            update_frequency="1d",
            data_requirements=["high", "low", "close"],
            author="Factor Mining System"
        )
        super().__init__(metadata)
        self.window = window
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算已实现波动率"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        # Garman-Klass估计器
        gk_volatility = np.log(high/low) * np.log(high/close) + np.log(low/close) * np.log(low/close)
        
        # 滚动求和并年化
        realized_vol = np.sqrt(gk_volatility.rolling(window=self.window).sum() * 252)
        
        return realized_vol.fillna(0)


# 注册所有波动率因子
def register_volatility_factors():
    """注册所有波动率因子"""
    factors = [
        VolatilityFactor(10),
        VolatilityFactor(20),
        VolatilityFactor(60),
        ATRFactor(14),
        ATRFactor(20),
        BollingerVolatilityFactor(20, 2.0),
        GARCHVolatilityFactor(30),
        VolatilitySkewFactor(20),
        VolatilityKurtosisFactor(20),
        RealizedVolatilityFactor(20)
    ]
    
    for factor in factors:
        factor_registry.register(factor)


# 自动注册
register_volatility_factors() 