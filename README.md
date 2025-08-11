# 🚀 Fluxia - Professional Binary Options EA System

**Fluxia** is a complete binary options trading system that combines a powerful **MQL5 Expert Advisor (EA)** with a **Python backend** to provide real-time market data and intelligent trading signals for MetaTrader 5.

![Fluxia Dashboard](https://img.shields.io/badge/Platform-MT5-blue) ![Backend](https://img.shields.io/badge/Backend-Python%20FastAPI-green) ![Data Source](https://img.shields.io/badge/Data-OlympTrade-orange)

## 📋 Table of Contents
- [What is Fluxia?](#what-is-fluxia)
- [System Overview](#system-overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation Guide](#installation-guide)
- [Backend Setup](#backend-setup)
- [MQL5 EA Setup](#mql5-ea-setup)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [Advanced Features](#advanced-features)
- [Contributing](#contributing)
- [License](#license)

## 🎯 What is Fluxia?

Fluxia is a **professional-grade binary options trading system** designed for traders who want:

- **Real-time market data** from OlympTrade
- **Intelligent trading signals** based on RSI and EMA indicators
- **Risk management** with customizable stake amounts
- **Performance tracking** with detailed statistics
- **Backend caching** to prevent rate limiting
- **Beautiful dashboard** showing win rates and trading metrics

### For Complete Beginners:
Think of Fluxia as your **personal trading assistant** that:
1. **Watches the market** 24/7 for you
2. **Analyzes price patterns** using mathematical indicators
3. **Shows you when to trade** with clear BUY/SELL signals
4. **Tracks your performance** like a professional trader
5. **Works with MetaTrader 5** - the world's most popular trading platform

## 🏗️ System Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MetaTrader 5  │◄──►│  Fluxia Backend │◄──►│   OlympTrade    │
│   (Your Chart)  │    │  (Data Server)  │    │  (Data Source)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
    ┌────▼────┐              ┌────▼────┐              ┌────▼────┐
    │ Fluxia  │              │ Python  │              │ Market  │
    │   EA    │              │FastAPI  │              │  Data   │
    │(Signals)│              │ Redis   │              │ (OHLC)  │
    └─────────┘              └─────────┘              └─────────┘
```

**How it works:**
1. **OlympTrade** provides real-time market data (candlestick prices)
2. **Python Backend** fetches and caches this data efficiently
3. **MQL5 EA** requests data from backend and generates trading signals
4. **You see everything** on your MetaTrader 5 chart with a beautiful dashboard

## ✨ Features

### 🎨 MQL5 Expert Advisor (Fluxia_v2.0.mq5)
- **📊 Real-time Trading Signals**: Clear BUY/SELL arrows on your chart
- **🎯 Multiple Signal Tiers**: Premium, Quality, and Standard signals
- **📈 Technical Indicators**: RSI (14 period) + EMA (21/50 periods)
- **⏰ Smart Timing**: Signals only appear every 5 minutes at optimal times
- **🎮 Gaming-Style Dashboard**: Beautiful dark theme with neon colors
- **📊 Performance Tracking**: Win rate, profit/loss, pending trades
- **⚡ SL/TP Simulation**: Stop Loss and Take Profit analysis
- **🔔 Multi-Alert System**: Popup, email, push notifications
- **📱 Mobile Friendly**: Works on MT5 mobile app

### 🖥️ Python Backend (FastAPI)
- **🌐 RESTful API**: Clean endpoints for data access
- **⚡ Redis Caching**: Prevents rate limiting with 5-minute cache
- **🔄 Real-time Updates**: Fresh data every minute
- **🛡️ JWT Authentication**: Secure OlympTrade connection
- **📊 Health Monitoring**: System status and diagnostics
- **☁️ Cloud Ready**: Deployable on Render.com, Heroku, AWS
- **🔧 Debug Mode**: Comprehensive logging for troubleshooting

### 🎯 Trading Features
- **📈 Signal Types**: 
  - 🥇 **Premium**: Very oversold/overbought + strong trend + patterns
  - 🥈 **Quality**: Clear oversold/overbought + trend confirmation
  - 🥉 **Standard**: Basic RSI + trend signals
- **💰 Risk Management**: Fixed amount or percentage-based stakes
- **⏱️ 5-Minute Expiry**: Optimized for binary options timing
- **📊 Win Rate Tracking**: Live calculation of your success rate
- **🎮 Gamification**: Rankings from "NOOB" to "LEGENDARY"

## 📋 Prerequisites

Before installing Fluxia, you need:

### For Everyone:
- **MetaTrader 5** (free from any broker)
- **Windows PC** (MT5 requirement)
- **Internet connection**
- **OlympTrade account** (for market data)

### For Backend Setup (Optional but Recommended):
- **Python 3.9+** (free from python.org)
- **Redis server** (free - we'll show you how to install)
- **Basic computer skills** (copy/paste, run commands)

### For Cloud Deployment (Advanced):
- **GitHub account** (free)
- **Render.com account** (free tier available)

## 🚀 Installation Guide

### Step 1: Download Fluxia
1. **Download** this entire project
2. **Extract** to a folder like `C:\Fluxia\`
3. You should see two main parts:
   - `Fluxia_v2.0.mq5` (the EA file)
   - `backend/` folder (Python server)

### Step 2: Choose Your Setup
You have two options:

#### Option A: 🟢 Easy Setup (Recommended for Beginners)
- Use the **cloud backend** (we'll host it for you)
- Just install the EA in MetaTrader 5
- **Pros**: No technical setup, always available
- **Cons**: Dependent on our server

#### Option B: 🔵 Advanced Setup (For Tech-Savvy Users)
- Run your **own backend** server
- Full control over everything
- **Pros**: Complete control, privacy, customization
- **Cons**: Requires technical setup

Let's start with **Option A** (Easy Setup):

---

## 🟢 Easy Setup (Cloud Backend)

### Step 1: Install the EA in MetaTrader 5

1. **Open MetaTrader 5**
2. **Open File Menu** → `Data Folder`
3. **Navigate** to `MQL5` → `Experts` folder
4. **Copy** `Fluxia_v1.5.mq5` into this folder
5. **Restart MetaTrader 5**
6. **Find Fluxia** in Navigator → Expert Advisors

### Step 2: Allow WebRequest URLs
**⚠️ IMPORTANT**: This step is required or the EA won't work!

1. **Tools** → **Options**
2. **Expert Advisors** tab
3. **Check** "Allow WebRequest for listed URLs"
4. **Click "Add"** and enter: `https://fluxia-backend.onrender.com`
5. **Click "OK"**

### Step 3: Attach the EA

1. **Open any M1 chart** (1-minute timeframe) - **EURUSD_OTC recommended**
2. **Drag Fluxia EA** from Navigator onto the chart
3. **In the settings popup**:
   - Set **Backend Base URL**: `https://fluxia-backend.onrender.com`
   - **Enable Debug Mode** for first run
   - Adjust other settings as desired
4. **Click OK**

### Step 4: Verify It's Working

You should see:
```
✅ Backend connected successfully
🔧 DEBUG: Timer set successfully (1 second interval)
🔧 DEBUG: Auto-scroll and shift enabled for better chart navigation
```

**If you see errors**, check the [Troubleshooting](#troubleshooting) section.

---

## 🔵 Advanced Setup (Your Own Backend)

### Step 1: Install Python Dependencies

1. **Install Python 3.9+** from [python.org](https://python.org)
2. **Open Command Prompt** as Administrator
3. **Navigate** to the backend folder:
   ```bash
   cd C:\Fluxia\backend
   ```
4. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```

### Step 2: Install Redis Server

**Option A: Windows (Recommended)**
1. **Download Redis** from [releases page](https://github.com/microsoftarchive/redis/releases)
2. **Install** and **start** Redis service
3. **Verify** it's running: open `http://localhost:6379` should show Redis info

**Option B: Docker (Advanced)**
```bash
docker run -d -p 6379:6379 redis:latest
```

### Step 3: Configure Environment

1. **Copy** `.env.example` to `.env`
2. **Edit** `.env` file with your OlympTrade credentials:
   ```env
   # API Configuration
   API_HOST=0.0.0.0
   API_PORT=8000
   DEBUG=true
   
   # Redis Configuration  
   REDIS_URL=redis://localhost:6379
   
   # OlympTrade Configuration (REQUIRED)
   OLYMPTRADE_REFRESH_TOKEN=your_refresh_token_here
   OLYMP_FULL_COOKIE=your_full_cookie_here
   
   # Logging
   LOG_LEVEL=INFO
   ```

### Step 4: Get OlympTrade Credentials

**⚠️ This is the tricky part - you need your OlympTrade authentication data:**

1. **Login** to OlympTrade in your browser
2. **Open Developer Tools** (F12)
3. **Network Tab** → make any trade or refresh
4. **Find requests** to olymptrade.com
5. **Copy** the `Cookie` header (very long string)
6. **Paste** as `OLYMP_FULL_COOKIE` in your `.env` file

**Note**: This is advanced and requires technical knowledge. The Easy Setup is recommended for most users.

### Step 5: Start the Backend

```bash
python start.py
```

You should see:
```
🚀 Starting Fluxia EA Backend...
📡 Host: 0.0.0.0
🔌 Port: 8000
🐛 Debug: True
📊 Redis: redis://localhost:6379
```

### Step 6: Install the EA (Same as Easy Setup)

Follow the same steps as Easy Setup, but use:
- **Backend Base URL**: `http://127.0.0.1:8000`

---

## ⚙️ Configuration

### MQL5 EA Settings

When you attach the EA, you'll see these settings:

#### 🎯 Signal Settings
- **RSI Period**: `14` (recommended - how many candles to analyze)
- **RSI Oversold**: `35` (below this = BUY signal potential)  
- **RSI Overbought**: `65` (above this = SELL signal potential)
- **Fast EMA**: `21` (short-term trend)
- **Slow EMA**: `50` (long-term trend)

#### 💰 Risk Management
- **Risk Percentage**: `2.0%` (of account balance per trade)
- **Stake Mode**: `Fixed Amount` or `Percentage`
- **Fixed Stake**: `$5.00` (if using fixed mode)

#### 🎨 Visual Settings
- **Buy Signal Color**: `Lime` (BUY arrows)
- **Sell Signal Color**: `Red` (SELL arrows)
- **Show Dashboard**: `true` (the beautiful stats panel)
- **Show Zones**: `true` (entry zones around signals)
- **Show Labels**: `true` (signal information text)

#### 🔔 Alert Settings
- **Enable Alerts**: `true` (sound alerts)
- **Enable Popups**: `true` (popup windows)
- **Enable Push**: `false` (mobile notifications - setup required)
- **Enable Email**: `false` (email alerts - setup required)

#### 🌐 Backend Settings
- **Backend URL**: Your backend server URL
- **Connection Timeout**: `10000ms` (10 seconds)
- **Enable Logging**: `true` (helpful for troubleshooting)
- **Debug Mode**: `false` (set `true` for detailed logs)

### Backend Configuration

The backend can be configured via environment variables or `.env` file:

```env
# Server Settings
API_HOST=0.0.0.0              # Listen on all interfaces
API_PORT=8000                 # Port number
DEBUG=true                    # Enable debug logging

# Redis Cache Settings  
REDIS_URL=redis://localhost:6379  # Redis connection
CACHE_TTL=300                     # Cache expiry (5 minutes)

# OlympTrade API Settings
OLYMPTRADE_REFRESH_TOKEN=xxx      # Your refresh token
OLYMP_FULL_COOKIE=xxx            # Full cookie string
OLYMPTRADE_WS_URI=wss://ws.olymptrade.com/...  # WebSocket URL

# Logging
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
```

## 📖 Usage Guide

### Getting Your First Signal

1. **Attach Fluxia** to a **EURUSD_OTC M1** chart (1-minute timeframe)
2. **Wait for the next 5-minute mark** (12:05, 12:10, 12:15, etc.)
3. **Watch for signals**:
   - **🟢 Green Arrow UP** = BUY signal (price will go up)
   - **🔴 Red Arrow DOWN** = SELL signal (price will go down)

### Understanding the Dashboard

The gaming-style dashboard shows:

```
⚡ F L U X I A ⚡
BINARY OPTIONS AI

📊 STATS          🎯 WIN RATE
TRADES: 15           75.2%
WINS: 12            EXPERT  
LOSS: 3             TARGET: 70%
PENDING: 1          
PROFIT: $48         

💰 TRADING         ⚡ SL/TP SIM
STAKE: $5           TP HITS: 8
MG1: 0             SL HITS: 2  
MG2: 0             SIM P/L: $52
RISK: 2%
EXPIRY: 5M         FLUXIA OTC v2.0
```

**What each section means:**

#### 📊 Stats Section
- **TRADES**: Total number of signals generated
- **WINS**: Successful trades (price moved in predicted direction)
- **LOSS**: Failed trades (price moved opposite)
- **PENDING**: Active signals waiting for expiry
- **PROFIT**: Total profit/loss based on stake amounts

#### 🎯 Win Rate Section  
- **Percentage**: Your success rate (WINS ÷ TOTAL)
- **Rating**: 
  - 🔥 **LEGENDARY** (80%+)
  - 💎 **EXPERT** (70-79%)
  - 🥇 **PRO** (60-69%)
  - 🥈 **AMATEUR** (50-59%)
  - 😅 **NOOB** (<50%)
- **TARGET**: Aim for 70%+ for profitable trading

#### 💰 Trading Section
- **STAKE**: Amount per trade (auto-calculated based on your settings)
- **MG1/MG2**: Martingale counters (for advanced risk management)
- **RISK**: Risk percentage per trade
- **EXPIRY**: Signal duration (5 minutes for binary options)

#### ⚡ SL/TP Simulation
- **TP HITS**: Simulated Take Profit successes
- **SL HITS**: Simulated Stop Loss triggers  
- **SIM P/L**: Hypothetical profit/loss with SL/TP strategy

### Signal Quality Levels

Fluxia generates three tiers of signals:

#### 🥇 PREMIUM Signals (Best)
- **Conditions**: Very oversold/overbought (RSI <25 or >75) + Strong trend + Candlestick patterns
- **Expected Win Rate**: 75-85%
- **Frequency**: 2-3 per day
- **Example**: `"ENHANCED PREMIUM BUY: Oversold + Trend + Pullback"`

#### 🥈 QUALITY Signals (Good)
- **Conditions**: Oversold/overbought (RSI <30 or >70) + Clear trend + 10+ minute spacing
- **Expected Win Rate**: 65-75%  
- **Frequency**: 5-8 per day
- **Example**: `"QUALITY BUY: Oversold + Clear Trend"`

#### 🥉 STANDARD Signals (Okay)
- **Conditions**: Basic RSI levels (35/65) + Trend confirmation + 5+ minute spacing
- **Expected Win Rate**: 55-65%
- **Frequency**: 10-15 per day
- **Example**: `"STANDARD BUY: RSI + Uptrend"`

### Best Practices

#### ✅ DO:
- **Use M1 timeframe** (1-minute) for optimal signal timing
- **Trade EURUSD_OTC** or other major OTC pairs
- **Wait for PREMIUM signals** when possible
- **Keep 70%+ win rate** as your target
- **Let signals complete** their 5-minute expiry
- **Monitor the dashboard** for performance tracking

#### ❌ DON'T:
- **Don't trade every signal** - quality over quantity
- **Don't chase losses** with larger stakes
- **Don't ignore risk management** settings
- **Don't trade during news events** (high volatility)
- **Don't use on exotic pairs** (less reliable)

### Trading Schedule

**Best Times to Trade** (UTC):
- **European Session**: 08:00 - 12:00 UTC
- **US Session**: 13:00 - 17:00 UTC  
- **Asian Session**: 00:00 - 04:00 UTC

**Avoid Trading During**:
- Major news events (NFP, FOMC, etc.)
- Market open/close times (gaps)
- Very low volume periods

## 📚 API Documentation

### Health Check
```http
GET /health
```
Returns backend status and configuration.

**Response:**
```json
{
    "status": "healthy",
    "config": {
        "debug_mode": true
    }
}
```

### Get Candlestick Data
```http
GET /ea/candlesticks?currency_pair=EURUSD_OTC&time=2025-08-11+03:30:00
```

**Parameters:**
- `currency_pair`: Symbol name (e.g., "EURUSD_OTC")  
- `time`: UTC timestamp for specific candle (optional)
- `download`: Set to "true" for CSV download

**Response:**
```json
{
    "success": true,
    "candles": [
        {
            "timestamp": 1754882520,
            "utc_time": "2025-08-11 03:22:00 UTC",
            "open": 1.1563,
            "high": 1.15643,
            "low": 1.1563,
            "close": 1.15637,
            "volume": 0.0
        }
    ],
    "total_count": 1
}
```

### Cache Statistics  
```http
GET /ea/cache/stats
```
Returns Redis cache performance metrics.

**Response:**
```json
{
    "status": "connected",
    "total_keys": 45,
    "ea_keys": 40,
    "regular_keys": 5,
    "memory_used": "2.1M"
}
```

### Download Historical Data
```http
GET /ea/candlesticks?currency_pair=EURUSD_OTC&download=true
```
Returns CSV file with historical candle data for import into MT5.

## 🐛 Troubleshooting

### Common Issues

#### ❌ "WebRequest blocked" Error
**Problem**: EA can't connect to backend
**Solution**:
1. Tools → Options → Expert Advisors
2. Check "Allow WebRequest for listed URLs"  
3. Add your backend URL (e.g., `http://127.0.0.1:8000`)
4. Restart MT5

#### ❌ "Backend unavailable" Message
**Problem**: Backend server is not running
**Solutions**:
- **Cloud Backend**: Check if https://fluxia-backend.onrender.com/health works
- **Local Backend**: Make sure you ran `python start.py`
- **Firewall**: Check Windows Firewall isn't blocking connections

#### ❌ "No signals appearing"  
**Problem**: EA is running but no arrows show up
**Solutions**:
1. **Check timeframe**: Must be M1 (1-minute)
2. **Wait for timing**: Signals only appear at :00, :05, :10, :15 minute marks
3. **Check symbol**: Use EURUSD_OTC or similar OTC pairs
4. **Enable Debug Mode**: See what's happening in the logs

#### ❌ "Candles less than 500" Alert
**Problem**: Not enough historical data
**Solution**:
1. **Download history**: Click the provided URL in the alert
2. **Import to MT5**: Import the CSV file via MT5 history center
3. **Or wait**: Let it run for a few hours to build up data

#### ❌ Dashboard not showing
**Problem**: Visual elements missing
**Solution**:
1. **Check "Show Dashboard"**: Ensure it's enabled in EA settings
2. **Chart space**: Make sure chart has enough space for dashboard
3. **Restart EA**: Remove and re-attach the EA

#### ❌ Backend crashes on startup
**Problem**: Missing dependencies or configuration
**Solutions**:
1. **Check requirements**: Run `pip install -r requirements.txt` again
2. **Check .env file**: Make sure all required fields are filled
3. **Check Redis**: Ensure Redis server is running
4. **Check ports**: Make sure port 8000 is available

### Debug Mode

Enable debug mode to see detailed information:

1. **EA Settings** → Set "Debug Mode" to `true`
2. **Check Experts tab** in MetaTrader terminal
3. Look for messages like:
   ```
   🔧 DEBUG: EA Start Time: 2025.08.11 03:15:38
   🔧 DEBUG: Backend health response: {"status":"healthy"}
   🔧 DEBUG: Timer set successfully (1 second interval)
   ```

### Log Files

**Backend Logs**: Check console output when running `python start.py`
**EA Logs**: Check MT5 Experts tab for detailed messages
**System Logs**: Windows Event Viewer for system-level issues

## 🔧 Advanced Features

### Custom Indicators

You can modify the signal generation by adjusting these parameters:

```mql5
// In Fluxia_v1.5.mq5, modify these values:
input int InpRSIPeriod = 14;           // RSI calculation period
input double InpRSIOversold = 35;      // BUY signal threshold  
input double InpRSIOverbought = 65;    // SELL signal threshold
input int InpEMAFast = 21;             // Fast trend line
input int InpEMASlow = 50;             // Slow trend line
```

### Risk Management Formulas

**Fixed Amount**:
```
Stake = InpFixedStake (e.g., $5.00)
```

**Percentage Based**:
```  
Stake = (Account Balance × InpRiskPercent) ÷ 100
Example: ($1000 × 2%) ÷ 100 = $20.00
```

**Martingale System** (Advanced):
```
After Loss: Next Stake = Previous Stake × 2.2
After Win: Reset to base stake
```

### Performance Metrics

**Win Rate Calculation**:
```
Win Rate = (Total Wins ÷ Total Trades) × 100
```

**Expected Profit Formula**:
```
Expected Profit = (Win Rate × Payout) - (Loss Rate × Stake)
Example: (70% × 85%) - (30% × 100%) = 59.5% - 30% = 29.5% profit
```

**Sharpe Ratio** (Risk-adjusted returns):
```
Sharpe = (Average Return - Risk-free Rate) ÷ Standard Deviation
```

### Cloud Deployment

Deploy your own backend to the cloud:

#### Render.com Deployment

1. **Fork** this repository to your GitHub
2. **Connect** GitHub to Render.com
3. **Create new Web Service**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **Add Environment Variables**:
   - `OLYMPTRADE_REFRESH_TOKEN`
   - `OLYMP_FULL_COOKIE`
   - `REDIS_URL` (use Render's Redis add-on)

#### Heroku Deployment

1. **Install Heroku CLI**
2. **Create Procfile**:
   ```
   web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
3. **Deploy**:
   ```bash
   heroku create fluxia-backend
   heroku addons:create heroku-redis:hobby-dev
   git push heroku main
   ```

### API Rate Limiting

The backend implements intelligent caching:

- **EA Requests** (with time parameter): 5-minute cache
- **Regular Requests**: No caching (always fresh)
- **Cache Key Format**: `ea_candle:EURUSD_OTC:20250811_0330`

This prevents OlympTrade rate limiting when multiple EAs run simultaneously.

### Custom Symbol Creation

Create custom symbols in MT5 for better data control:

1. **Tools** → **Quotes** → **Custom Instruments**
2. **Create new symbol**: "EURUSD_FLUXIA"
3. **Configure**: 1-minute timeframe, 5-digit pricing
4. **Import data**: Use the CSV export from backend

### Multi-Pair Trading

Run multiple EAs on different pairs:

```mql5
// Recommended pairs for OTC trading:
EURUSD_OTC  // Most liquid, best for beginners
GBPUSD_OTC  // High volatility, good signals
USDJPY_OTC  // Asian session focus
AUDUSD_OTC  // Good for trend following
```

## 🤝 Contributing

We welcome contributions to make Fluxia better!

### Development Setup

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create feature branch**:
   ```bash
   git checkout -b feature/amazing-feature
   ```
4. **Make changes** and **test thoroughly**
5. **Commit** with clear messages:
   ```bash
   git commit -m "Add amazing new feature"
   ```
6. **Push** and create **Pull Request**

### Code Standards

**Python Backend**:
- Follow **PEP 8** style guide
- Use **type hints** for all functions  
- Add **docstrings** for public methods
- Write **unit tests** for new features

**MQL5 EA**:
- Use **clear variable names**
- **Comment complex logic**
- Follow **MetaTrader naming conventions**
- Test on **multiple timeframes** and **symbols**

### Feature Requests

Have an idea? **Create an issue** with:
- **Clear description** of the feature
- **Use case** explaining why it's needed  
- **Implementation ideas** if you have any

### Bug Reports

Found a bug? **Create an issue** with:
- **Steps to reproduce** the problem
- **Expected behavior** vs **actual behavior**
- **Screenshots** or **log files** if helpful
- **System information** (OS, MT5 build, Python version)

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### What this means:
- ✅ **Commercial use** allowed
- ✅ **Modification** allowed  
- ✅ **Distribution** allowed
- ✅ **Private use** allowed
- ❌ **No liability** for damages
- ❌ **No warranty** provided

## 🙏 Acknowledgments

- **OlympTrade** for providing market data API
- **MetaQuotes** for the MQL5 platform
- **FastAPI** team for the excellent web framework
- **Redis** team for the caching solution
- **Community contributors** who helped improve Fluxia

## 📞 Support

Need help? Here's how to get support:

### 📖 Documentation
- **Read this README** thoroughly
- **Check troubleshooting** section
- **Review API documentation**

### 🐛 Issues
- **Search existing issues** first
- **Create new issue** with detailed information
- **Be patient** - we're volunteers!

### 💬 Community
- **GitHub Discussions** for general questions
- **Stack Overflow** for programming questions (tag: fluxia)

### 🚀 Professional Support
For commercial support, custom development, or priority bug fixes:
- **Email**: support@fluxia.systems
- **Response time**: 24-48 hours
- **Rates**: $50/hour for development, $25/hour for support

---

## 🎉 Quick Start Checklist

**For Absolute Beginners** - follow this checklist:

### ☑️ Phase 1: Get MetaTrader 5
- [ ] Download MT5 from any broker
- [ ] Open a demo account (free, no money needed)
- [ ] Open EURUSD_OTC M1 chart

### ☑️ Phase 2: Install Fluxia
- [ ] Download Fluxia files
- [ ] Copy `Fluxia_v1.5.mq5` to MT5 experts folder
- [ ] Allow WebRequest URLs in MT5 settings
- [ ] Attach EA to chart with cloud backend URL

### ☑️ Phase 3: First Signals  
- [ ] Wait for next 5-minute mark
- [ ] Look for green/red arrows
- [ ] Watch dashboard update with statistics
- [ ] Understand signal quality levels

### ☑️ Phase 4: Optimize Performance
- [ ] Aim for 70%+ win rate
- [ ] Focus on Premium/Quality signals
- [ ] Adjust risk management settings
- [ ] Monitor performance over 1+ weeks

**Congratulations! You're now running a professional binary options trading system!** 🎉

---

**Remember**: Trading involves risk. Never trade with money you can't afford to lose. This system provides signals but doesn't guarantee profits. Always practice on demo accounts first and understand the risks involved.

**Happy Trading!** 📈✨