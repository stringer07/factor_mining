"""
配置管理模块
使用Pydantic进行配置验证和类型检查
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Dict, Any, Optional
import os


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    host: str = Field(default="localhost", description="数据库主机")
    port: int = Field(default=5432, description="数据库端口")
    username: str = Field(default="postgres", description="数据库用户名")
    password: str = Field(default="password", description="数据库密码")
    database: str = Field(default="factor_mining", description="数据库名称")
    
    @property
    def url(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    class Config:
        env_prefix = "DB_"


class RedisSettings(BaseSettings):
    """Redis配置"""
    host: str = Field(default="localhost", description="Redis主机")
    port: int = Field(default=6379, description="Redis端口")
    password: Optional[str] = Field(default=None, description="Redis密码")
    db: int = Field(default=0, description="Redis数据库索引")
    
    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"
    
    class Config:
        env_prefix = "REDIS_"


class InfluxDBSettings(BaseSettings):
    """InfluxDB配置"""
    url: str = Field(default="http://localhost:8086", description="InfluxDB URL")
    token: Optional[str] = Field(default=None, description="认证Token")
    org: str = Field(default="factor-mining", description="组织名称")
    bucket: str = Field(default="market-data", description="存储桶名称")
    
    class Config:
        env_prefix = "INFLUXDB_"


class ExchangeSettings(BaseSettings):
    """交易所API配置"""
    binance_api_key: Optional[str] = Field(default=None, description="币安API密钥")
    binance_secret: Optional[str] = Field(default=None, description="币安API密钥")
    okx_api_key: Optional[str] = Field(default=None, description="OKX API密钥")
    okx_secret: Optional[str] = Field(default=None, description="OKX API密钥")
    okx_passphrase: Optional[str] = Field(default=None, description="OKX API密码")
    
    class Config:
        env_prefix = "EXCHANGE_"


class DataSettings(BaseSettings):
    """数据配置"""
    symbols: List[str] = Field(default=["BTC/USDT", "ETH/USDT"], description="交易对列表")
    timeframes: List[str] = Field(default=["1m", "5m", "15m", "1h", "4h", "1d"], description="时间周期")
    max_history_days: int = Field(default=365, description="最大历史数据天数")
    update_interval: int = Field(default=60, description="数据更新间隔(秒)")
    
    class Config:
        env_prefix = "DATA_"


class FactorSettings(BaseSettings):
    """因子配置"""
    calculation_window: int = Field(default=20, description="因子计算窗口")
    min_history_periods: int = Field(default=100, description="最小历史周期数")
    outlier_threshold: float = Field(default=3.0, description="异常值阈值(标准差倍数)")
    missing_threshold: float = Field(default=0.1, description="缺失值阈值")
    
    class Config:
        env_prefix = "FACTOR_"


class BacktestSettings(BaseSettings):
    """回测配置"""
    initial_capital: float = Field(default=100000.0, description="初始资金")
    commission: float = Field(default=0.001, description="手续费率")
    slippage: float = Field(default=0.0005, description="滑点")
    benchmark: str = Field(default="BTC/USDT", description="基准资产")
    
    class Config:
        env_prefix = "BACKTEST_"


class APISettings(BaseSettings):
    """API配置"""
    host: str = Field(default="0.0.0.0", description="API主机")
    port: int = Field(default=8000, description="API端口")
    debug: bool = Field(default=False, description="调试模式")
    cors_origins: List[str] = Field(default=["*"], description="CORS允许的源")
    secret_key: str = Field(default="your-secret-key", description="JWT密钥")
    
    class Config:
        env_prefix = "API_"


class LoggingSettings(BaseSettings):
    """日志配置"""
    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        description="日志格式"
    )
    file_path: str = Field(default="logs/app.log", description="日志文件路径")
    rotation: str = Field(default="10 MB", description="日志轮转大小")
    retention: str = Field(default="30 days", description="日志保留时间")
    
    class Config:
        env_prefix = "LOG_"


class Settings(BaseSettings):
    """主配置类"""
    # 基本信息
    app_name: str = Field(default="Factor Mining System", description="应用名称")
    version: str = Field(default="1.0.0", description="版本号")
    description: str = Field(default="系统化的因子挖掘系统", description="应用描述")
    
    # 子配置
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    influxdb: InfluxDBSettings = InfluxDBSettings()
    exchange: ExchangeSettings = ExchangeSettings()
    data: DataSettings = DataSettings()
    factor: FactorSettings = FactorSettings()
    backtest: BacktestSettings = BacktestSettings()
    api: APISettings = APISettings()
    logging: LoggingSettings = LoggingSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings 