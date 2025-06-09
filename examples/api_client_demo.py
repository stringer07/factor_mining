#!/usr/bin/env python3
"""
API客户端使用示例
演示如何通过HTTP API使用因子挖掘系统
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

# API基础URL
BASE_URL = "http://localhost:8000"


async def test_api_endpoints():
    """测试API端点"""
    
    async with aiohttp.ClientSession() as session:
        
        print("=== 测试系统健康状态 ===")
        async with session.get(f"{BASE_URL}/health") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"系统状态: {data}")
            else:
                print(f"健康检查失败: {resp.status}")
        
        print("\n=== 测试交易所健康状态 ===")
        async with session.get(f"{BASE_URL}/api/v1/data/exchanges/health") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"交易所状态: {json.dumps(data, indent=2, default=str)}")
            else:
                print(f"交易所健康检查失败: {resp.status}")
        
        print("\n=== 测试获取交易对列表 ===")
        async with session.get(f"{BASE_URL}/api/v1/data/symbols?exchange=binance") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"Binance交易对数量: {data.get('count', 0)}")
                if data.get('symbols'):
                    print(f"前10个交易对: {data['symbols'][:10]}")
            else:
                print(f"获取交易对失败: {resp.status}")
        
        print("\n=== 测试获取OHLCV数据 ===")
        ohlcv_request = {
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "limit": 50
        }
        
        async with session.post(
            f"{BASE_URL}/api/v1/data/ohlcv", 
            json=ohlcv_request
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"获取到 {data['count']} 条OHLCV数据")
                if data['data']:
                    latest = data['data'][-1]
                    print(f"最新数据: {latest}")
            else:
                error = await resp.text()
                print(f"获取OHLCV数据失败: {resp.status} - {error}")
        
        print("\n=== 测试获取因子列表 ===")
        async with session.get(f"{BASE_URL}/api/v1/factors/list") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"可用因子数量: {data['count']}")
                for factor in data['factors'][:5]:  # 显示前5个
                    print(f"  - {factor['name']}: {factor['description']}")
            else:
                print(f"获取因子列表失败: {resp.status}")
        
        print("\n=== 测试因子分类 ===")
        async with session.get(f"{BASE_URL}/api/v1/factors/categories") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"因子分类: {data['categories']}")
            else:
                print(f"获取因子分类失败: {resp.status}")
        
        print("\n=== 测试计算单个因子 ===")
        params = {
            "symbol": "BTC/USDT",
            "timeframe": "1h", 
            "limit": 100
        }
        
        async with session.post(
            f"{BASE_URL}/api/v1/factors/calculate/momentum_20",
            params=params
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"因子 {data['factor_name']} 计算结果:")
                print(f"  数据点数量: {data['count']}")
                print(f"  统计信息: {data['statistics']}")
                if data['data']:
                    print(f"  最新值: {data['data'][-1]}")
            else:
                error = await resp.text()
                print(f"计算因子失败: {resp.status} - {error}")
        
        print("\n=== 测试批量计算因子 ===")
        factor_names = ["momentum_10", "momentum_20", "rsi_momentum_14"]
        params = {
            "symbol": "ETH/USDT",
            "timeframe": "1h",
            "limit": 100
        }
        
        async with session.post(
            f"{BASE_URL}/api/v1/factors/calculate/batch",
            json=factor_names,
            params=params
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"批量计算结果 - 成功: {data['successful']}/{data['total_factors']}")
                for factor_name, result in data['factors'].items():
                    if 'error' in result:
                        print(f"  {factor_name}: 失败 - {result['error']}")
                    else:
                        stats = result.get('statistics', {})
                        print(f"  {factor_name}: 成功 - 均值: {stats.get('mean', 'N/A'):.6f}")
            else:
                error = await resp.text()
                print(f"批量计算因子失败: {resp.status} - {error}")


async def test_realtime_data():
    """测试实时数据获取"""
    print("\n=== 测试实时数据 ===")
    
    async with aiohttp.ClientSession() as session:
        
        # 获取实时行情
        async with session.get(f"{BASE_URL}/api/v1/data/ticker/BTC/USDT?exchange=binance") as resp:
            if resp.status == 200:
                data = await resp.json()
                ticker = data.get('ticker', {})
                print(f"BTC/USDT 实时行情:")
                print(f"  价格: ${ticker.get('last', 'N/A')}")
                print(f"  24h变化: {ticker.get('percentage', 'N/A')}%")
                print(f"  24h成交量: {ticker.get('baseVolume', 'N/A')}")
            else:
                error = await resp.text()
                print(f"获取实时行情失败: {resp.status} - {error}")
        
        # 获取24小时统计
        async with session.get(f"{BASE_URL}/api/v1/data/stats/ETH/USDT?exchange=binance") as resp:
            if resp.status == 200:
                data = await resp.json()
                stats = data.get('stats', {})
                print(f"ETH/USDT 24小时统计:")
                print(f"  开盘: ${stats.get('open', 'N/A')}")
                print(f"  最高: ${stats.get('high', 'N/A')}")
                print(f"  最低: ${stats.get('low', 'N/A')}")
                print(f"  收盘: ${stats.get('close', 'N/A')}")
            else:
                error = await resp.text()
                print(f"获取24小时统计失败: {resp.status} - {error}")


async def main():
    """主函数"""
    print("开始API客户端测试")
    print("确保服务已启动: python run.py")
    print("-" * 50)
    
    try:
        await test_api_endpoints()
        await test_realtime_data()
        
        print("\n" + "=" * 50)
        print("API测试完成！")
        print("更多API文档请访问: http://localhost:8000/docs")
        
    except aiohttp.ClientError as e:
        print(f"网络连接错误: {e}")
        print("请确保API服务正在运行 (python run.py)")
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 