# Institutional-Grade Automated Trading Platform

**An enterprise-ready options and equities trading platform combining AlgoTest features with institutional architecture.**

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER (Streamlit)               │
├─────────────────────────────────────────────────────────────────┤
│  📊 Dashboard    🔍 Screener    📈 Positions    🎯 Options Builder│
│  📊 Backtest     ⏯️ Simulator    📋 History     ⚙️ Settings      │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼──────────┐  ┌──────▼──────────┐  ┌─────▼──────────┐
│  STRATEGY LAYER  │  │  EXECUTION      │  │  RISK MGMT    │
├──────────────────┤  ├─────────────────┤  ├───────────────┤
│ • Strategy Config│  │ • Order Manager │  │ • Greeks      │
│ • JSON Parser    │  │ • Multi-Broker  │  │ • Risk Monitor│
│ • Signal Engine  │  │ • Order Tracking│  │ • Limits      │
└──────────────────┘  └─────────────────┘  └───────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼──────────┐  ┌──────▼──────────┐  ┌─────▼──────────┐
│ BACKTESTING      │  │ LIVE TRADING    │  │ DATA LAYER    │
├──────────────────┤  ├─────────────────┤  ├───────────────┤
│ • C++ Backtest   │  │ • Event Bus     │  │ • ClickHouse  │
│ • Historical Data│  │ • Async Workers │  │ • Cache Layer │
│ • Performance    │  │ • Kafka Workers │  │ • SQLite      │
└──────────────────┘  └─────────────────┘  └───────────────┘
```

## 📦 Core Modules

### 1. **Strategy Configuration** (`strategy_config.py`)
- **Purpose**: JSON-based strategy definition and validation
- **Features**:
  - Multi-leg options strategies
  - Entry/exit conditions
  - Risk management parameters
  - Greeks limits enforcement
- **Usage**: Define strategies once, backtest and live trade with same config

### 2. **Greeks Calculator** (`greeks_calculator.py`)
- **Purpose**: Black-Scholes options pricing and Greeks calculation
- **Features**:
  - Delta, Gamma, Theta, Vega, Rho calculations
  - Implied Volatility estimation
  - Full option chain generation
- **Models**: Black-Scholes with European options

### 3. **Backtesting Engine** (`backtest_engine.py`)
- **Purpose**: High-performance historical strategy validation
- **Features**:
  - Trade-by-trade simulation
  - Risk management enforcement
  - Performance metrics calculation
- **Metrics**: Sharpe ratio, Max DD, Win%, Profit Factor, etc.

### 4. **Live Trading System** (`live_trading_system.py`)
- **Purpose**: Event-driven real-time execution and risk monitoring
- **Components**:
  - **EventBus**: Pub/sub for market data, signals, fills
  - **RiskMonitor**: Real-time Greeks aggregation + limit checks
  - **ExecutionEngine**: Multi-broker order orchestration
- **Architecture**: CQRS-ready with event sourcing

### 5. **Broker Adapter** (`broker.py`)
- **Purpose**: Multi-broker execution with resilience
- **Features**:
  - Retry logic with exponential backoff
  - Paper trading fallback
  - Order tracking and position management
  - Support for market/limit/SL-M orders

### 6. **Database** (`database.py`)
- **Purpose**: Thread-safe trade journal
- **Schema**: Trades, Orders, Daily Stats
- **Features**: Atomic operations, SQLite for simplicity

## 🎯 AlgoTest Feature Parity

| Feature | Status | Module |
|---------|--------|--------|
| Option Chain with Greeks | ✅ Done | `greeks_calculator.py` |
| Payoff Graph Visualization | ✅ Done | `pages/options_builder.py` |
| Strategy Templates | ✅ Done | `pages/options_builder.py` |
| Strategy Simulator | ✅ Done | `pages/simulator.py` |
| Backtest Reports | ✅ Done | `pages/backtest_results.py` |
| Greeks Heatmap | ✅ Done | `pages/simulator.py` |
| Multi-leg Management | ✅ Done | `strategy_config.py` |
| Live Position Greeks | ✅ Done | `live_trading_system.py` |

## 📊 UI Pages

### 1. **Dashboard** (`pages/dashboard.py`)
- KPI metrics (Total trades, Win rate, P&L, Daily loss)
- Open positions with real-time P&L
- Recent closed trades
- System health indicators

### 2. **Screener** (`pages/screener.py`)
- 48+ stock multi-indicator analysis
- RSI, MACD, Bollinger Bands, ATR, ADX
- Momentum scoring algorithm
- Intelligent caching to prevent rate limits

### 3. **Options Builder** (`pages/options_builder.py`)
- **Tab 1**: Option chain with all Greeks
- **Tab 2**: Payoff graph for strategy
- **Tab 3**: Multi-leg strategy builder
- **Tab 4**: Portfolio Greeks monitoring

### 4. **Backtest Results** (`pages/backtest_results.py`)
- Comprehensive performance metrics
- Monthly P&L analysis
- Risk metrics and ratios
- Trade-by-trade history with filtering
- CSV export capability

### 5. **Simulator** (`pages/simulator.py`)
- Timeline scrubber (9:15 AM - 3:30 PM)
- Greeks evolution over time
- Price vs Time sensitivity heatmap
- Position breakdown by leg

### 6. **Positions** (`pages/positions.py`)
- Live open position management
- Per-position Greeks and P&L
- SL/Target management
- Daily loss tracking

### 7. **History** (`pages/history.py`)
- P&L distribution histogram
- Cumulative P&L chart
- Win/Loss ratio pie chart
- Searchable trade log

### 8. **Settings** (`pages/settings.py`)
- Broker connection management
- Screener configuration
- Trading parameters
- Security and data export

## 🔄 Event-Driven Architecture

```
┌─────────────────────┐
│   Market Data       │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │  Event Bus   │
    └──────┬───────┘
           │
    ┌──────┴──────────┬─────────────────┬────────────────┐
    │                 │                 │                │
    ▼                 ▼                 ▼                ▼
┌─────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│Signal   │  │Order Manager │  │Risk Monitor  │  │Analytics     │
│Engine   │  │(Execution)   │  │(Greeks calc) │  │(P&L tracking)│
└─────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

## 🚀 Deployment Architecture

### Local Development
- Python 3.9+ with venv
- Streamlit on port 8504
- SQLite database

### Production (Proposed)
- **Frontend**: Streamlit Cloud or Docker
- **Backtesting**: C++ engine (external service)
- **Data**: ClickHouse + Redis cache
- **Streaming**: Kafka for risk workers
- **Monitoring**: Prometheus + Grafana

## 📈 Strategy Execution Flow

```
1. Strategy Definition (JSON)
   ↓
2. Backtesting Validation
   ├─ Historical data fetch
   ├─ Signal generation
   ├─ Order simulation
   ├─ Risk enforcement
   └─ Performance calculation
   ↓
3. Live Paper Trading
   ├─ Real-time data subscription
   ├─ Signal matching
   ├─ Mock order execution
   └─ Simulated P&L tracking
   ↓
4. Live Trading (with Risk Limits)
   ├─ Order placement
   ├─ Greeks monitoring
   ├─ Risk breach detection
   ├─ Auto-exit on limits
   └─ Trade journal recording
```

## ⚙️ Risk Management Framework

### Hard Limits (Auto-enforced)
- **Max Daily Loss**: ₹25,000 (configurable)
- **Max Open Positions**: 5 (configurable)
- **Max Position Loss**: ₹5,000 per trade
- **Greeks Limits**: Delta < 0.3, Theta > 0.5

### Monitoring & Alerts
- Portfolio Delta/Gamma/Theta/Vega aggregation
- Greeks sensitivity to 1% price/vol changes
- Risk breach warnings
- Automatic position closing on limit breach

## 📊 Performance Metrics Calculated

| Metric | Description |
|--------|-------------|
| Win Rate | % of profitable trades |
| Profit Factor | Gross Profit / Gross Loss |
| Sharpe Ratio | Risk-adjusted returns |
| Max Drawdown | Largest peak-to-trough decline |
| Recovery Factor | Total Return / Max Drawdown |
| Avg Trade Duration | Hours held per trade |
| Expectancy | Average P&L per trade |

## 🔐 Security Features

1. **Credential Management**
   - Environment variables for secrets
   - Masked UI display
   - No hardcoded credentials

2. **Rate Limiting**
   - Cache layer for yfinance data
   - API call deduplication
   - Exponential backoff for retries

3. **Data Isolation**
   - Per-user trade journals (future)
   - SQLite with transaction locks
   - Audit log for all orders

## 🧪 Testing & Validation

### Unit Tests (Implemented)
- Strategy config parsing ✅
- Greeks calculations ✅
- Backtesting engine ✅
- Risk monitoring logic ✅

### Integration Tests (Ready to build)
- End-to-end strategy execution
- Broker integration
- Database operations
- Event bus propagation

## 📚 JSON Strategy Format Example

```json
{
  "metadata": {
    "name": "Iron Condor - NIFTY",
    "version": "1.0"
  },
  "parameters": {
    "strategy_legs": [
      {
        "leg_id": 1,
        "position": "SELL_CALL",
        "strike_offset": 1,
        "expiry_days": 7,
        "quantity": 1
      },
      {
        "leg_id": 2,
        "position": "BUY_CALL",
        "strike_offset": 2,
        "expiry_days": 7,
        "quantity": 1
      }
    ]
  },
  "risk_management": {
    "max_daily_loss": 25000,
    "max_open_positions": 5,
    "Greeks_limits": {
      "delta_max": 0.3,
      "theta_min": 0.5
    }
  }
}
```

## 🎯 Next Steps (Roadmap)

### Phase 1: ✅ Foundation (Complete)
- ✅ JSON strategy configuration
- ✅ Historical backtesting engine
- ✅ Greeks calculator
- ✅ Event-driven architecture
- ✅ All AlgoTest features

### Phase 2: 🚧 Data Layer (In Progress)
- ⏳ ClickHouse schema design
- ⏳ Historical data warehouse
- ⏳ Real-time data aggregation
- ⏳ High-frequency caching

### Phase 3: 🎯 Production
- ⏳ Kafka risk workers
- ⏳ Redis broker adapter
- ⏳ C++ backtesting engine integration
- ⏳ Multi-user support

### Phase 4: 📊 Advanced Features
- ⏳ AI-based strategy optimization
- ⏳ Machine learning signal generation
- ⏳ Portfolio-level Greeks optimization
- ⏳ Real-time risk dashboard

## 📞 Support & Documentation

- **Config**: See `strategy_config.py` for JSON format
- **Greeks**: See `greeks_calculator.py` for Black-Scholes implementation
- **Backtest**: See `backtest_engine.py` for performance metrics
- **UI**: Each page file has docstrings explaining components

## 🏆 Key Differentiators vs AlgoTest

1. **Institutional Architecture**
   - Event-driven design for low-latency execution
   - CQRS-ready for scaling
   - Multi-broker support built-in

2. **Open Source Foundation**
   - Customizable strategy formats
   - Extensible Greeks calculator
   - Pluggable data sources

3. **Production Ready**
   - Risk management enforcement
   - Comprehensive error handling
   - Thread-safe database operations

4. **Developer Friendly**
   - Well-documented Python codebase
   - Clear separation of concerns
   - Easy to test and debug

---

**Built for institutional traders who demand performance, reliability, and flexibility.**
