---
title: "Freqtrade vs Jesse vs Hummingbot: Self-Hosted Algorithmic Trading Guide 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "trading", "crypto", "automation"]
draft: false
description: "Compare the top open-source algorithmic trading bots — Freqtrade, Jesse, and Hummingbot. Learn how to self-host, configure, and deploy automated trading strategies with Docker."
---

Running a trading bot on someone else's cloud platform means your API keys, strategies, and trading data live on infrastructure you don't control. Self-hosting your algorithmic trading stack gives you full custody of everything — from your exchange API credentials to your backtest results and live trade logs.

In this guide, we compare three of the most popular open-source algorithmic trading frameworks: **Freqtrade**, **Jesse**, and **Hummingbot**. Each takes a different approach to automated trading, and the right choice depends on whether you want a ready-to-trade bot, a backtesting-first research framework, or a market-making engine.

## Why Self-Host Your Trading Bot?

Using a hosted trading service introduces several risks and limitations:

- **API key exposure**: Cloud platforms store your exchange credentials. A breach compromises your funds.
- **Strategy leakage**: Proprietary strategies live on servers owned by third parties.
- **Rate limits and latency**: Shared infrastructure adds network hops between your bot and the exchange.
- **Vendor lock-in**: Strategies and configurations are often tied to a specific platform's format.
- **Cost**: Hosted services charge monthly fees or take a percentage of profits.

Self-hosting eliminates these concerns. Your bot runs on your own hardware or VPS, communicates directly with exchange APIs, and stores all data locally. You can run 24/7 with minimal cost — a $5/month VPS is sufficient for most single-exchange bots.

## Freqtrade vs Jesse vs Hummingbot at a Glance

| Feature | Freqtrade | Jesse | Hummingbot |
|---|---|---|---|
| **GitHub Stars** | 49,426 | 7,795 | 18,363 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Primary Language** | Python | Python (backend) + JS (UI) | Python (core) + TypeScript (gateway) |
| **Trading Focus** | Spot trading with technical strategies | Research-driven backtesting + live trading | Market making + arbitrage |
| **Backtesting Engine** | Built-in with detailed metrics | Built-in with candle-based backtesting | Limited — focused on live execution |
| **Web UI** | FreqUI (built-in dashboard) | Jesse Trading (commercial UI available) | Hummingbot Gateway + Dashboard |
| **Exchange Support** | 20+ exchanges via CCXT | Binance, Bybit, dYdX, Bitget, more | 30+ connectors including CEX and DEX |
| **Docker Support** | Official image with docker-compose | Dockerfile (compose must be written manually) | Official image with docker-compose |
| **Strategy Format** | Python class with indicator methods | Python class with should_long/should_cancel | YAML controller configs + Python scripts |
| **Risk Management** | Stop-loss, ROI, trailing stop, custom | Stop-loss, take-profit, trailing stop | Inventory skew, order spread controls |
| **Paper Trading** | Yes (dry-run mode) | Yes (paper trading mode) | Yes (paper trading mode) |
| **License** | GPLv3 | LGPL-3.0 | Apache 2.0 |

## Freqtrade — The Ready-to-Trade Bot

**Freqtrade** is the most widely used open-source crypto trading bot, with nearly 50,000 GitHub stars. It ships with a complete out-of-the-box experience: backtesting, hyperparameter optimization (hyperopt), dry-run paper trading, and live trading — all accessible via a built-in REST API and web UI.

### Key Features

- **Strategy optimization**: Hyperopt uses machine learning (scikit-optimize) to find optimal strategy parameters against historical data.
- **FreqUI**: A modern web dashboard for monitoring trades, performance charts, and strategy analysis.
- **Telegram integration**: Control your bot, get trade notifications, and monitor performance via Telegram.
- **Custom indicators**: Full access to the TA-Lib and pandas-ta libraries for building custom technical indicators.
- **Dry-run mode**: Test strategies with real-time market data without risking real funds.

### Docker Compose Setup

Freqtrade provides an official `docker-compose.yml` that makes deployment straightforward:

```yaml
services:
  freqtrade:
    image: freqtradeorg/freqtrade:stable
    restart: unless-stopped
    container_name: freqtrade
    volumes:
      - "./user_data:/freqtrade/user_data"
    ports:
      - "127.0.0.1:8080:8080"
    command: >
      trade
      --logfile /freqtrade/user_data/logs/freqtrade.log
      --db-url sqlite:////freqtrade/user_data/tradesv3.sqlite
      --config /freqtrade/user_data/config.json
      --strategy SampleStrategy
```

Configuration lives in `user_data/config.json`. A minimal setup:

```json
{
    "trading_mode": "spot",
    "stake_currency": "USDT",
    "stake_amount": 100,
    "dry_run": true,
    "exchange": {
        "name": "binance",
        "key": "your-api-key",
        "secret": "your-api-secret"
    },
    "api_server": {
        "enabled": true,
        "listen_ip_address": "0.0.0.0",
        "listen_port": 8080,
        "username": "freqtrader",
        "password": "your-secure-password"
    }
}
```

Start the bot with `docker compose up -d` and access FreqUI at `http://localhost:8080`.

### Strategy Example

A basic Freqtrade strategy inherits from `IStrategy` and defines entry/exit conditions:

```python
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class MyStrategy(IStrategy):
    minimal_roi = {"0": 0.10}
    stoploss = -0.05
    timeframe = "5m"

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["sma_20"] = ta.SMA(dataframe, timeperiod=20)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["rsi"] < 30) & (dataframe["close"] > dataframe["sma_20"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["rsi"] > 70),
            "exit_long",
        ] = 1
        return dataframe
```

## Jesse — The Research-First Framework

**Jesse** takes a different philosophy: it is designed primarily as a research and backtesting framework. Its backtesting engine is exceptionally thorough, providing candle-by-candle simulation that closely mirrors live trading conditions. Once a strategy is validated through backtesting, Jesse can execute it live on supported exchanges.

### Key Features

- **Candle-based backtesting**: Simulates every candle individually for realistic results, including slippage and fee modeling.
- **Walk-forward optimization**: Built-in support for walk-forward analysis to avoid overfitting.
- **Import candles**: Download and store historical candle data for any supported exchange.
- **Portfolio-level backtesting**: Test strategies across multiple trading pairs simultaneously.
- **Plugin system**: Extend functionality with custom routes, exchanges, and indicators.

### Docker Setup

Jesse provides a Dockerfile but no official docker-compose file. Here is a production-ready compose configuration:

```yaml
services:
  jesse:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    container_name: jesse
    volumes:
      - "./strategies:/home/jesse/strategies"
      - "./storage:/home/jesse/storage"
      - ".env:/home/jesse/.env"
    ports:
      - "127.0.0.1:5000:5000"
    command: Jesse run --live
```

You can also use the pre-built image:

```yaml
services:
  jesse:
    image: jesseai/jesse:latest
    restart: unless-stopped
    container_name: jesse
    volumes:
      - "./strategies:/home/jesse/strategies"
      - "./storage:/home/jesse/storage"
    environment:
      - EXCHANGE_NAME=binance
      - API_KEY=your-api-key
      - API_SECRET=your-api-secret
    command: Jesse run --live
```

Configuration is managed through `.env` files and route definitions in `routes.py`:

```python
from jesse.routes import router

router.set_routes([
    {"exchange": "Binance", "symbol": "BTC-USDT", "timeframe": "4h", "strategy": "TrendFollowing"},
    {"exchange": "Binance", "symbol": "ETH-USDT", "timeframe": "4h", "strategy": "TrendFollowing"},
])

router.set_candles("1m")
router.set_initial_portfolio(10000, "USDT")
```

### Strategy Example

Jesse strategies define clear entry and exit logic:

```python
from jesse.strategies import Strategy
from jesse.indicators import sma, rsi

class TrendFollowing(Strategy):
    def should_long(self) -> bool:
        return rsi(self.candles, 14) < 30 and sma(self.candles, 20) < self.price

    def should_cancel(self) -> bool:
        return rsi(self.candles, 14) > 50

    def go_long(self):
        self.buy = 1, self.price
        self.stop_loss = 0.05
        self.take_profit = 0.10
```

## Hummingbot — The Market-Making Engine

**Hummingbot** is purpose-built for market making and arbitrage strategies. Unlike Freqtrade and Jesse, which focus on directional trading based on technical indicators, Hummingbot provides liquidity by placing simultaneous buy and sell orders around a reference price.

### Key Features

- **Market making**: Automated bid-ask spread management with inventory skew to balance positions.
- **Arbitrage**: Cross-exchange and triangular arbitrage strategies.
- **30+ connectors**: Supports centralized exchanges (Binance, Coinbase, KuCoin), DEXs (Uniswap, PancakeSwap), and derivatives (dYdX, GMX).
- **Gateway API**: A TypeScript-based gateway provides unified REST/WebSocket access to all connectors.
- **Scripting**: Python scripts for custom logic and controllers for composable strategy building.

### Docker Compose Setup

Hummingbot's official `docker-compose.yml` includes both the bot and the Gateway service:

```yaml
services:
  hummingbot:
    container_name: hummingbot
    image: hummingbot/hummingbot:latest
    volumes:
      - ./conf:/home/hummingbot/conf
      - ./conf/connectors:/home/hummingbot/conf/connectors
      - ./conf/strategies:/home/hummingbot/conf/strategies
      - ./logs:/home/hummingbot/logs
      - ./data:/home/hummingbot/data
      - ./scripts:/home/hummingbot/scripts
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
    tty: true
    stdin_open: true
    network_mode: host

  gateway:
    profiles: ["gateway"]
    restart: always
    container_name: gateway
    image: hummingbot/gateway:latest
    ports:
      - "15888:15888"
    volumes:
      - ./gateway-files/conf:/home/gateway/conf
```

### Pure Market Making Configuration

Hummingbot uses YAML-based strategy configs. A basic pure market making setup:

```yaml
total_amount_quote: 1000
order_amount_quote: 50
bid_spread: 0.01
ask_spread: 0.01
order_levels: 3
order_level_spread: 0.005
order_level_amount: 50
inventory_target_base_pct: 0.5
```

This config places 3 bid and 3 ask levels with a 1% spread around the mid-price, each order sized at 50 USDT, targeting a 50/50 base/quote inventory balance.

## Comparison: Which Bot Is Right for You?

| Criteria | Choose Freqtrade if... | Choose Jesse if... | Choose Hummingbot if... |
|---|---|---|---|
| **Experience Level** | Beginner to intermediate | Intermediate to advanced | Intermediate to advanced |
| **Primary Goal** | Automated directional trading | Strategy research + validation | Market making + liquidity provision |
| **Backtesting** | Good with hyperopt optimization | Excellent candle-by-candle detail | Limited, live-focused |
| **Exchange Support** | 20+ via CCXT | Major CEXs + some DEXs | 30+ CEX, DEX, and derivatives |
| **UI Experience** | Built-in FreqUI dashboard | Commercial UI available | Gateway + community dashboards |
| **Community** | Largest (Discord, docs, tutorials) | Smaller, research-focused | Active market-making community |
| **Strategy Complexity** | Python classes with indicators | Python classes with research tools | YAML configs + Python scripts |
| **Best For** | Running proven strategies live | Developing and testing new strategies | Providing liquidity and earning spread |

## Deployment Architecture

For a production self-hosted trading setup, consider this architecture:

```
┌─────────────────────────────────────────┐
│              Your VPS / Server           │
│                                          │
│  ┌─────────────┐    ┌─────────────────┐  │
│  │  Trading    │───▶│   SQLite /      │  │
│  │  Bot        │    │   PostgreSQL    │  │
│  │  Container  │    │                 │  │
│  └──────┬──────┘    └─────────────────┘  │
│         │                                 │
│         ▼                                 │
│  ┌─────────────┐    ┌─────────────────┐  │
│  │  Reverse    │    │   Monitoring    │  │
│  │  Proxy      │    │   (Grafana +    │  │
│  │  (Caddy/    │    │    Prometheus)  │  │
│  │   Nginx)    │    │                 │  │
│  └──────┬──────┘    └─────────────────┘  │
│         │                                 │
└─────────┼─────────────────────────────────┘
          │ TLS
          ▼
   ┌──────────────┐
   │  Exchange    │
   │  API (Binance│
   │  / Bybit /   │
   │  Coinbase)   │
   └──────────────┘
```

Key deployment considerations:

- **Network latency**: Choose a VPS geographically close to your exchange's API servers.
- **Persistence**: Mount Docker volumes for configs, logs, and trade databases.
- **Monitoring**: Use tools like [Gatus or Prometheus](../gatus-vs-blackbox-exporter-vs-smokeping-self-hosted-endpoint-monitoring-2026/) to monitor bot health and API connectivity.
- **Security**: Store API keys in Docker secrets or environment files with restricted permissions. Never commit them to version control.

## Risk Management Best Practices

No trading bot is foolproof. Always implement these safeguards:

1. **Start with paper trading**: Run in dry-run mode for at least 2 weeks before going live.
2. **Set strict stop-losses**: Never risk more than 1-2% of your portfolio on a single trade.
3. **Use API key restrictions**: Create exchange API keys with trading-only permissions — no withdrawal access.
4. **Monitor regularly**: Set up alerts for unusual behavior, connection failures, or unexpected drawdowns.
5. **Version control your strategies**: Keep all strategy code in Git so you can audit changes and roll back if needed.
6. **Backup your data**: Regularly back up trade databases, configuration files, and strategy files. Consider using a dedicated [backup solution](../restic-vs-borg-vs-kopia-backup-guide/) for your trading data.

For those interested in personal finance tracking alongside trading activity, tools like [Firefly III](../actual-budget-vs-firefly-iii-vs-beancount-self-hosted-personal-finance-2026/) can help consolidate and analyze your overall financial picture.

## FAQ

### Is algorithmic trading legal?

Yes, algorithmic trading is legal in most jurisdictions for personal use. However, regulations vary by country and exchange. Always check local laws and your exchange's terms of service. Some exchanges require explicit permission for API-based automated trading.

### How much money do I need to start?

Most bots allow you to start with as little as $50-100 in trading capital. However, meaningful returns require larger positions to overcome exchange fees and minimum order sizes. A recommended starting point is $500-1000 for a single trading pair.

### Can I run multiple trading bots on the same server?

Yes. Each bot can run in its own Docker container with separate configurations. A typical $5-10/month VPS can comfortably run 2-3 trading bots simultaneously, provided they are not running CPU-intensive backtests at the same time.

### How do I keep my trading strategies private?

Self-hosting ensures your strategies never leave your server. Store strategy files on encrypted volumes, use SSH for remote access, and never push strategy code to public repositories. All three tools support local-only operation with no telemetry.

### What happens if my bot loses connection to the exchange?

All three bots handle reconnection automatically. Freqtrade and Jesse will resume trading once connectivity is restored. Hummingbot cancels open orders during disconnections to prevent stale orders. Always set up monitoring alerts to detect and investigate connection failures promptly.

### Which bot has the best backtesting?

Jesse has the most thorough backtesting engine with candle-by-candle simulation and walk-forward optimization. Freqtrade offers strong backtesting with hyperopt for parameter optimization. Hummingbot's backtesting is more limited — it is primarily designed for live market making rather than historical analysis.

### Do I need programming experience?

Freqtrade and Jesse require Python knowledge to write custom strategies, though both provide template strategies to start from. Hummingbot can be configured with YAML alone for basic market making, but Python is needed for custom scripts and advanced strategies.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Freqtrade vs Jesse vs Hummingbot: Self-Hosted Algorithmic Trading Guide 2026",
  "description": "Compare the top open-source algorithmic trading bots — Freqtrade, Jesse, and Hummingbot. Learn how to self-host, configure, and deploy automated trading strategies with Docker.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>
