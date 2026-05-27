# 🤖 Groww AutoTrader Pro - User Guide

## What is this tool for?

This is an **Automated Trading Platform** that helps you:
- 🔍 **Find trading opportunities** using technical analysis
- 📊 **Analyze options strategies** with Greeks and payoff analysis
- 💰 **Manage your portfolio** with optimization and rebalancing
- 📈 **Backtest strategies** on historical data before trading
- ⚡ **Execute trades** in paper (simulated) or live mode on Groww broker

**Think of it like a 3-step process:**
1. **Find Opportunities** → Use Screener to find good stocks to trade
2. **Analyze** → Use Options Builder or Greeks Sensitivity to understand the setup
3. **Trade** → Place orders on Trade page to actually execute the trade

---

## 🚀 Quick Start - How to Place Your First Trade

### Step 1: Go to the Trade Page
When you first open the app, you should now see **"⚡ Trade"** as the first page in the navigation menu. Click it.

### Step 2: Fill in Order Details
The page has a simple form with:
- **Stock Symbol** → Pick from NIFTY50 stocks or enter custom (e.g., RELIANCE)
- **Order Side** → BUY or SELL
- **Quantity** → How many shares
- **Order Type** → MARKET (instant) or LIMIT (at specific price)

### Step 3: Check Price & Amount
The page shows:
- **Current LTP** (Last Traded Price) - refreshed in real-time
- **Total Amount** - how much money will be needed
- **Available Margin** - whether you have enough balance

### Step 4: Place the Order
Click **"✅ PLACE ORDER"** button. That's it! Your trade is now placed.

---

## 📍 Page-by-Page Guide

### ⚡ Trade Page (NEW!)
**What it does:** Place actual BUY/SELL orders on Groww broker

**When to use:**
- When you want to execute a trade you've already analyzed
- To enter new positions
- To exit existing trades

**Key features:**
- Simple, clean interface
- Real-time price updates
- Margin check before placing order
- Order confirmation with order ID
- Shows your recent open positions

**Example workflow:**
```
1. Select Symbol: RELIANCE
2. Choose Side: BUY
3. Enter Quantity: 1 share
4. Choose Type: MARKET (buy at current price)
5. Click PLACE ORDER
6. See confirmation with Order ID
```

---

### 📊 Dashboard
**What it does:** Show your overall account health and recent activity

**You'll see:**
- **KPIs** (Key metrics): Total trades, Win rate, P&L, Wins/Losses
- **Open Positions** → All active trades with P&L
- **Recent Closed Trades** → Your trading history
- **System Status** → Are you connected to Groww? Margin available?

**When to use:**
- When you first login to see overall performance
- To track open positions
- To monitor daily/monthly P&L

**This is your "home page"** that shows everything at a glance.

---

### 🔍 Screener
**What it does:** Scan 50+ stocks and find trading opportunities using technical indicators

**You'll analyze:**
- **RSI** (Relative Strength Index) - Find oversold/overbought stocks
- **Moving Averages** - Identify trends
- **Momentum** - Find fast-moving stocks
- **Volume** - Spot unusual activity

**When to use:**
- You want to find NEW stocks to trade
- You want systematic, rules-based scanning
- You want to avoid emotional decisions

**Example workflow:**
```
1. Select Universe: NIFTY50 or custom stocks
2. Set RSI range: 25-75 (oversold to overbought)
3. Set Momentum threshold: 50+
4. Click SCAN
5. See list of matching stocks with signals
6. Click on a stock to see charts
7. If interested, go to Trade page and place order
```

---

### 📈 Positions
**What it does:** Manage all your open positions (active trades)

**You'll see:**
- All open trades with entry price, current price, P&L
- Option to close individual trades
- Update stop loss / take profit levels
- Track each trade's performance

**When to use:**
- You want to close a winning/losing trade
- You want to modify stop loss on a position
- You want to see detailed P&L per trade

---

### 🎯 Options Builder
**What it does:** Build and analyze options strategies (Calls, Puts, Spreads, etc.)

**Features:**
- **Option Chain** → See all available strikes with prices and Greeks
- **Payoff Graph** → Visual diagram of profit/loss at different price levels
- **Strategy Templates** → Pre-built strategies (Bull Call Spread, Iron Condor, etc.)
- **Greeks Analysis** → Delta, Gamma, Theta, Vega risk metrics

**When to use:**
- You want to trade options instead of stocks
- You want to understand options risk (Greeks)
- You want to build multi-leg strategies
- You want to see payoff diagrams before trading

**Example:**
```
If RELIANCE is at ₹2389:
- Buy 2400 Call @ ₹50
- Sell 2450 Call @ ₹20
Result: Bull Call Spread with limited profit/loss
```

---

### 📊 Greeks Sensitivity (Interactive)
**What it does:** Study how options prices change with price, volatility, and time

**Visualizations:**
- **Price Sensitivity** → What happens if stock price goes up/down?
- **IV Sensitivity** → What if volatility increases?
- **Time Decay** → How much value is lost each day?
- **2D Heatmap** → See all effects at once

**When to use:**
- You want to understand options risk deeply
- You want to learn how Greeks work
- You want to see sensitivity before trading

---

### 📊 Strategy Comparison
**What it does:** Compare multiple backtested strategies side-by-side

**Metrics compared:**
- Returns, Sharpe Ratio, Max Drawdown
- Win Rate, Profit Factor
- Best/Worst Trades
- Consecutive wins/losses

**When to use:**
- You have multiple strategies and want to choose the best one
- You want to rank strategies by different metrics
- You want to see equity curves compared

---

### 💼 Portfolio Optimization
**What it does:** Find the best allocation for your stocks

**Methods:**
- **Markowitz** → Maximize Sharpe ratio (best risk-adjusted returns)
- **Risk Parity** → Equal risk contribution per stock
- **Equal Weight** → Simple 1/N allocation

**When to use:**
- You have ₹500k and want to allocate across 5-10 stocks
- You want optimized weights based on risk
- You want to compare different allocation strategies

---

### ⚙️ Rebalancing Settings
**What it does:** Automatically rebalance your portfolio when allocations drift

**Triggers:**
- **Threshold** → Rebalance if any position drifts >5%
- **Time-based** → Rebalance weekly/monthly/quarterly
- **Momentum** → Rebalance based on recent performance

**When to use:**
- You want to maintain your target allocation
- You don't want to manually rebalance
- You want to see rebalancing costs

---

### 📊 Backtest
**What it does:** Test your strategy on historical data before trading real money

**You can:**
- Run strategies on 5+ years of historical data
- See equity curves (profit/loss over time)
- Calculate Sharpe ratio, Max drawdown, Win rate
- Export detailed trade-by-trade results

**When to use:**
- You have a new trading idea and want to test it
- You want to know how it would have performed
- You want to estimate realistic returns and drawdowns

**Example:**
```
Test "Buy RSI<30" strategy on NIFTY50 for 5 years:
Result: 45% returns, 15% max drawdown, 65% win rate
→ Decide: Is this good enough to trade with real money?
```

---

### ⏯️ Simulator
**What it does:** Paper trade (simulated) with fake money to practice

**Benefits:**
- No real money at risk
- Practice your trading without fear
- See how your decision-making is
- Build confidence before going live

**When to use:**
- You're new to trading
- You want to test a strategy with paper trades first
- You want to practice without risking real money

---

### 📋 History
**What it does:** View complete trading history with filters and statistics

**You'll see:**
- All trades (open and closed)
- Win/Loss breakdown
- Best/Worst trades
- Performance by symbol, time period, etc.

**When to use:**
- You want to review your trading performance
- You want to learn from past mistakes
- You want to analyze patterns in your trades

---

### 🔐 User Management
**What it does:** Multi-user authentication and role-based access

**Roles:**
- **ADMIN** → Full access to everything
- **TRADER** → Can place orders and trade
- **ANALYST** → View-only, can see analysis
- **VIEWER** → Read-only dashboard access

**When to use:**
- Multiple people using the same platform
- You want to restrict access (e.g., analyst can't trade)
- You want audit trails of who did what

---

## 🎯 Real-World Trading Workflows

### Workflow 1: Quick Day Trade
```
1. Open Screener → Find momentum stocks
2. Click on stock to see chart
3. Go to Trade page → Place MARKET order
4. Watch on Dashboard
5. Close trade when target hit or SL breached
```

### Workflow 2: Options Income Strategy
```
1. Go to Options Builder
2. Pick a stock (e.g., NIFTY)
3. Select "Sell Put Spread" strategy
4. See payoff diagram
5. Go to Trade page → Place the orders
6. Monitor Greeks on Dashboard
7. Exit when profit target hit (theta decay)
```

### Workflow 3: Long-term Portfolio Allocation
```
1. Go to Portfolio Optimization
2. Input 5 stocks (e.g., RELIANCE, TCS, INFY, SBIN, HDFCBANK)
3. See optimal allocation (e.g., 30% RELIANCE, 20% TCS, ...)
4. Go to Trade page → Place multiple orders
5. Set up Rebalancing (threshold = 5%)
6. System auto-rebalances when needed
```

### Workflow 4: Strategy Development & Testing
```
1. Go to Backtest
2. Code a strategy (e.g., "Buy RSI<30, Sell RSI>70")
3. Run on 5 years of data
4. See results (returns, Sharpe, drawdown)
5. If good → Go to Simulator for paper trading
6. If results are consistent → Switch to live Trading
```

---

## 🔴 Paper Mode vs 🟢 Live Mode

### 🔵 PAPER MODE (Default - Safe for learning)
- Orders are **simulated** with fake money
- No real Groww connection needed
- Perfect for testing and learning
- Your Dashboard shows simulated P&L

### 🟢 LIVE MODE (Real money - Be careful!)
- Orders execute on **REAL Groww account**
- Real money is at risk
- Need valid Groww credentials
- Dashboard shows real P&L

**How to switch:** Check the mode badge in the sidebar (🟢 LIVE or 🔵 PAPER)

---

## ⚠️ Important: Risk Management Tips

1. **Start small** → Place 1-2 share orders, not 100 shares
2. **Use stop losses** → Always set a maximum loss level
3. **Don't over-leverage** → Don't use all your margin on one trade
4. **Paper trade first** → Test in simulator before going live
5. **Backtest first** → Test strategy on historical data before trading
6. **Monitor daily** → Check Dashboard at market close
7. **Scale up slowly** → Increase position size as you gain confidence

---

## 🚨 Common Issues & Solutions

**Q: "I placed an order but can't see it"**
A: Check Dashboard → Open Positions. Orders may take a few seconds to appear.

**Q: "Why is my margin showing ₹0?"**
A: You're in PAPER mode. It shows ₹100k default. In LIVE mode, it fetches real margin from Groww.

**Q: "Options Builder shows 'divide by zero' error"**
A: Make sure spot price is > 0. Try changing the spot price and clicking the page again.

**Q: "I want to backtest my idea but it takes too long"**
A: Backtests can take 30-60 seconds for 5 years of data. Be patient or reduce universe size.

**Q: "How do I connect to my real Groww account?"**
A: Go to Settings page, fill in Groww credentials (client_id, secret, username, password). Then switch mode to 🟢 LIVE.

---

## 💡 Best Practices

1. **Use Screener regularly** → Find opportunities systematically
2. **Backtest before trading** → Don't trade ideas without testing
3. **Review Dashboard daily** → Monitor your P&L
4. **Keep trade history clean** → Archive old trades
5. **Use Rebalancing** → Keep portfolio allocation on target
6. **Study Greeks** → Understand options risk before trading them
7. **Compare strategies** → Use Strategy Comparison to find winners

---

## 📞 Need Help?

- Check the Dashboard for live account status
- Use Backtest to validate ideas
- Review History to learn from past trades
- Consult Greeks Sensitivity for options education

Happy trading! 🚀
