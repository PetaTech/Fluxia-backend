//+------------------------------------------------------------------+
//|                                                      Fluxia.mq5 |
//|                                    Professional Binary Options Tool |
//|                                                        Version 2.0 |
//+------------------------------------------------------------------+
#property copyright "Fluxia Systems"
#property link      "https://fluxia.systems"
#property version   "2.00"
#property description "Advanced Binary Options Indicator for OTC Markets with Backend Integration"

// IMPORTANT: Add your backend URL to WebRequest allowed URLs in MetaTrader 5
// Tools -> Options -> Expert Advisors -> Allow WebRequest for listed URLs
// Add: 127.0.0.1:8000
// Converted from indicator to Expert Advisor to enable WebRequest
// All visual features preserved using chart objects instead of indicator buffers

//--- Enumerations (must be declared before inputs)
enum ENUM_STAKE_MODE
{
   STAKE_FIXED,        // Fixed Amount
   STAKE_PERCENT       // Percentage of Balance
};

//--- Input parameters
input group "=== SIGNAL SETTINGS ==="
input int InpRSIPeriod = 14;                   // RSI Period (changed from 7 to 14)
input double InpRSIOversold = 35;              // RSI Oversold Level (relaxed from 30 to 35)
input double InpRSIOverbought = 65;            // RSI Overbought Level (relaxed from 70 to 65)
input int InpEMAFast = 21;                     // Fast EMA Period (changed from 50 to 21)
input int InpEMASlow = 50;                     // Slow EMA Period (changed from 200 to 50)

input group "=== RISK MANAGEMENT ==="
input double InpRiskPercent = 2.0;             // Risk Percentage per Trade
input ENUM_STAKE_MODE InpStakeMode = STAKE_FIXED; // Stake Mode
input double InpFixedStake = 5.0;              // Fixed Stake Amount

input group "=== VISUAL SETTINGS ==="
input color InpBuyColor = clrLime;             // Buy Signal Color
input color InpSellColor = clrRed;             // Sell Signal Color
input color InpBuyZoneColor = clrBlue;         // Buy Zone Color
input color InpSellZoneColor = clrMagenta;     // Sell Zone Color
input bool InpShowDashboard = true;            // Show Dashboard
input bool InpShowZones = true;                // Show Entry Zones
input bool InpShowLabels = true;               // Show Signal Labels

input group "=== ALERT SETTINGS ==="
input bool InpEnableAlerts = true;             // Enable Alerts
input bool InpEnablePopups = true;             // Enable Popup Alerts
input bool InpEnablePushNotifications = false; // Enable Push Notifications
input bool InpEnableEmailAlerts = false;       // Enable Email Alerts

input group "=== BACKEND INTEGRATION ==="
input string InpBackendURL = "http://127.0.0.1:8000";  // Backend Base URL
input int InpConnectionTimeout = 10000;                // Connection Timeout (ms)
input bool InpEnableBackendLogging = true;             // Enable Backend Logging
input bool InpDebugMode = false;                       // Enable Debug Mode (Verbose Logging)

//--- Global variables (converted from indicator buffers to chart objects)
// double BuyBuffer[], SellBuffer[], EmptyBuffer1[], EmptyBuffer2[]; // Not needed in EA
int rsi_handle, ema_fast_handle, ema_slow_handle;
datetime last_signal_time = 0;
datetime next_signal_time = 0;
datetime last_advance_alert_time = 0; // Prevent advance alert spam

//--- Backend Integration Variables
bool backend_subscribed = false;
bool backend_connected = false;
int available_candles_count = 0;
datetime last_backend_request = 0;
datetime ea_start_time = 0;
string current_symbol_pair = "";
bool low_candles_warning_shown = false;
string historical_data_url = "";

//--- Dashboard Layout Configuration (easily customizable)
int DASH_X = 10;           // Dashboard X position
int DASH_Y = 30;           // Dashboard Y position  
int DASH_WIDTH = 380;      // Dashboard width
int DASH_HEIGHT = 277;     // Dashboard height

// Column positions
int COL1_X = 30;           // Left column X
int COL2_X = 100;          // Center column X  
int COL3_X = 100;          // Right column X
int COL4_X = 290;          // Far right column X

// Row positions
int ROW1_Y = 45;           // Title row
int ROW2_Y = 67;           // Subtitle row
int ROW3_Y = 95;           // Section headers
int ROW4_Y = 125;          // First stats row
int ROW5_Y = 135;          // Second stats row (WINS LOSS)
int ROW6_Y = 160;          // Third stats row (PENDING)
int ROW7_Y = 177;          // Fourth stats row (PROFIT)
int ROW8_Y = 210;          // Fifth stats row (SL/LP)
int ROW9_Y = 210;          // Sixth stats row (TRADING)
int ROW10_Y = 235;         // Seventh stats row (STAKE)
int ROW10_1_Y = 230;         // Seventh stats row (HITS)
int ROW11_Y = 245;         // Eighth stats row (MG)
int ROW11_1_Y = 255;         // Eighth stats row (SIM)
int ROW12_Y = 275;         // Ninth stats row (RISK)
int ROW12_1_Y = 275;         // Ninth stats row (DASHBOARD_TIME)
int ROW13_Y = 295;         // Bottom row (EXPIRY)
int ROW13_1_Y = 295;         // Bottom row (Dashboard_Version)

// Specialized positions
int PERF_TITLE_X = 100;    // Performance title X
int WINRATE_TITLE_X = 300; // Win rate title X
int TRADE_TITLE_X = 110;   // Trading title X
int SLTP_TITLE_X = 290;    // SL/TP title X

// Stats section spacing and sizing
int STATS_HEIGHT = 110;    // Height of stats sections

// Fine-tuning offsets
int TITLE_HEIGHT_EXTRA = -15; // Extra height for title background
int WINRATE_Y_OFFSET = 5;   // Extra Y offset for win rate display
int TP_X_OFFSET = 70;        // X offset for TP hits (left)
int SL_X_OFFSET = 10;        // X offset for SL hits (right)
int INDICATOR_X_OFFSET = 15; // X offset for animated indicator
int INDICATOR_Y_OFFSET = 5;  // Y offset for animated indicator
int INDICATOR_SIZE = 10;     // Size of animated indicator

//--- Dashboard variables
struct DashboardData
{
   int total_trades;
   int wins;
   int losses;
   int pending;
   double win_rate;
   int mg1_count;
   int mg2_count;
   double suggested_stake;
   datetime last_update;
   
   // SL/TP simulation metrics
   double simulated_sl_profit;
   double simulated_tp_profit;
   int sl_hits;
   int tp_hits;
   double avg_profit_per_trade;
   double max_drawdown;
   double sharpe_ratio;
   
   // Backend status
   bool backend_status;
   int backend_candles;
   string backend_message;
};
DashboardData dashboard;

//--- Signal tracking
struct SignalData
{
   datetime signal_time;
   datetime expiry_time;
   int signal_type; // 1 = Buy, -1 = Sell
   double entry_price;
   double stake_amount;
   int status; // 0 = Pending, 1 = Win, -1 = Loss
   
   // SL/TP simulation
   double sl_level;
   double tp_level;
   bool sl_hit;
   bool tp_hit;
   double exit_price;
   double profit_loss;
};
SignalData signal_history[];

//+------------------------------------------------------------------+
//| Expert Advisor initialization function                          |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Check timeframe
   if(Period() != PERIOD_M1)
   {
      Alert("Fluxia works only on M1 timeframe!");
      return(INIT_FAILED);
   }
   
   //--- EA doesn't use indicator buffers - signals drawn as chart objects
   //--- All visual elements handled by chart objects in signal generation functions
   
   //--- Create technical indicators
   rsi_handle = iRSI(_Symbol, PERIOD_M1, InpRSIPeriod, PRICE_CLOSE);
   ema_fast_handle = iMA(_Symbol, PERIOD_M1, InpEMAFast, 0, MODE_EMA, PRICE_CLOSE);
   ema_slow_handle = iMA(_Symbol, PERIOD_M1, InpEMASlow, 0, MODE_EMA, PRICE_CLOSE);
   
   if(rsi_handle == INVALID_HANDLE || ema_fast_handle == INVALID_HANDLE || ema_slow_handle == INVALID_HANDLE)
   {
      Print("Failed to create indicator handles");
      return(INIT_FAILED);
   }
   
   //--- Initialize dashboard
   InitializeDashboard();
   
   //--- Set EA name (no indicator-specific functions needed)
   // IndicatorSetString not needed for EA
   
   //--- No buffer initialization needed for EA
   
   //--- Calculate next signal time
   CalculateNextSignalTime();
   
   //--- Store EA start time and extract currency pair
   ea_start_time = TimeLocal(); // Use local time instead of TimeCurrent in OnInit
   current_symbol_pair = GetCurrencyPairFromSymbol();
   
   if(InpDebugMode)
      Print("🔧 DEBUG: EA Start Time: ", ea_start_time, " (", TimeToString(ea_start_time), ")");
   
   if(current_symbol_pair == "")
   {
      Alert("Unable to extract currency pair from symbol: " + Symbol() + ". Use format: EURUSD_OTC");
      return(INIT_FAILED);
   }
   
   //--- Try to check backend health
   if(InpDebugMode)
      Print("🔧 DEBUG: Checking backend health for ", current_symbol_pair);
   if(!SubscribeToBackend())
   {
      Print("⚠️ Running in offline mode (backend unavailable)");
      // Create download URL for historical data using exact format requested
      historical_data_url = InpBackendURL + "/ea/candlesticks?currency_pair=" + current_symbol_pair + "&count=5&download=true";
      if(InpEnableBackendLogging)
         Print("📊 Historical data: ", historical_data_url);
   }
   
   Print("🚀 Fluxia EA v2.0 initialized for ", current_symbol_pair);
   if(InpDebugMode)
      Print("🔧 DEBUG: Initialization complete - Backend Connected: ", backend_connected, ", Available Candles: ", available_candles_count);
   if(backend_connected)
   {
      Print("✅ Backend connected successfully");
      // Make initial candle request immediately after successful connection
      if(InpDebugMode)
         Print("🔧 DEBUG: Making initial candle request after successful connection");
      RequestLatestCandles();
   }
   else
      Print("⚠️ Running in offline mode (signals only)");
   
   //--- Enable auto-scroll for better chart navigation
   ChartSetInteger(0, CHART_AUTOSCROLL, 1);
   ChartSetInteger(0, CHART_SHIFT, 1);
   
   if(InpDebugMode)
      Print("🔧 DEBUG: Auto-scroll and shift enabled for better chart navigation");
   
   //--- Set timer for regular backend updates (every 1 second to check for :03 second trigger)
   if(EventSetTimer(1))
   {
      if(InpDebugMode)
         Print("🔧 DEBUG: Timer set successfully (1 second interval)");
   }
   else
   {
      Print("❌ ERROR: Failed to set timer!");
   }
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert Advisor deinitialization function                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   //--- Kill timer
   EventKillTimer();
   
   //--- Clean up dashboard objects
   CleanupDashboard();
   
   //--- Clean up signal objects
   CleanupSignalObjects();
   
   //--- Release indicator handles
   if(rsi_handle != INVALID_HANDLE) IndicatorRelease(rsi_handle);
   if(ema_fast_handle != INVALID_HANDLE) IndicatorRelease(ema_fast_handle);
   if(ema_slow_handle != INVALID_HANDLE) IndicatorRelease(ema_slow_handle);
   
   // Print("Fluxia Indicator deinitialized"); // Too verbose
}

//+------------------------------------------------------------------+
//| Expert Advisor tick function (replaces OnCalculate)            |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- Get current chart data
   int rates_total = Bars(_Symbol, PERIOD_M1);
   
   //--- Check for sufficient data
   if(rates_total < InpEMASlow + 10) return;
   
   //--- Candle requests moved to OnTimer() for custom symbols
   
   //--- Check candle count and show warning if needed
   CheckCandleCount();
   
   //--- Get price arrays
   datetime time[];
   double open[], high[], low[], close[];
   ArraySetAsSeries(time, true);
   ArraySetAsSeries(open, true);
   ArraySetAsSeries(high, true);
   ArraySetAsSeries(low, true);
   ArraySetAsSeries(close, true);
   
   int copy_count = MathMin(rates_total, 100);
   if(CopyTime(_Symbol, PERIOD_M1, 0, copy_count, time) <= 0) return;
   if(CopyOpen(_Symbol, PERIOD_M1, 0, copy_count, open) <= 0) return;
   if(CopyHigh(_Symbol, PERIOD_M1, 0, copy_count, high) <= 0) return;
   if(CopyLow(_Symbol, PERIOD_M1, 0, copy_count, low) <= 0) return;
   if(CopyClose(_Symbol, PERIOD_M1, 0, copy_count, close) <= 0) return;
   
   //--- Get indicator data
   double rsi[], ema_fast[], ema_slow[];
   ArraySetAsSeries(rsi, true);
   ArraySetAsSeries(ema_fast, true);
   ArraySetAsSeries(ema_slow, true);
   
   if(CopyBuffer(rsi_handle, 0, 0, copy_count, rsi) <= 0) return;
   if(CopyBuffer(ema_fast_handle, 0, 0, copy_count, ema_fast) <= 0) return;
   if(CopyBuffer(ema_slow_handle, 0, 0, copy_count, ema_slow) <= 0) return;
   
   //--- Check array sizes before calling functions
   if(ArraySize(time) == 0 || ArraySize(close) == 0 || ArraySize(rsi) == 0) return;
   
   //--- Check for new signals on current bar (index 0)
   CheckForSignals(0, time, open, high, low, close, rsi, ema_fast, ema_slow);
   
   //--- Update dashboard
   if(InpShowDashboard)
   {
      UpdateDashboard();
      ChartRedraw(); // Force chart redraw to show updated dashboard
   }
   
   //--- Update signal status
   UpdateSignalStatus(close);
}

//+------------------------------------------------------------------+
//| Check for trading signals                                        |
//+------------------------------------------------------------------+
void CheckForSignals(int idx, const datetime &time[], const double &open[], 
                    const double &high[], const double &low[], const double &close[],
                    const double &rsi[], const double &ema_fast[], const double &ema_slow[])
{
   //--- Simplified safety checks
   if(idx < 0 || idx >= ArraySize(rsi)) return;
   
   //--- Avoid duplicate signals
   if(time[idx] <= last_signal_time) return;
   
   //--- Get trend direction
   int trend = GetTrendDirection(ema_fast[idx], ema_slow[idx]);
   
   //--- Check timing for signals and advance warnings
   MqlDateTime dt;
   TimeToStruct(time[idx], dt);
   bool is_signal_time = (dt.min % 5 == 0);
   bool is_advance_warning_time = (dt.min % 5 == 4); // 1 minute before signal time
   
   //--- OPTIMIZED WIN RATE CONDITIONS: Balanced approach
   
   //--- Check candlestick patterns
   bool bullish_engulfing = IsBullishEngulfing(idx, open, high, low, close);
   bool bearish_engulfing = IsBearishEngulfing(idx, open, high, low, close);
   
   //--- Tier 1: Premium signals (Highest win rate) with pattern confirmation
   bool tier1_buy = (rsi[idx] < 25) && (trend > 0) && (ema_fast[idx] > ema_slow[idx] * 1.002) && bullish_engulfing;
   bool tier1_sell = (rsi[idx] > 75) && (trend < 0) && (ema_fast[idx] < ema_slow[idx] * 0.998) && bearish_engulfing;
   
   //--- Tier 2: Quality signals (Good win rate)
   bool tier2_buy = (rsi[idx] < 30) && (trend > 0) && (time[idx] - last_signal_time > 600); // 10+ min spacing
   bool tier2_sell = (rsi[idx] > 70) && (trend < 0) && (time[idx] - last_signal_time > 600);
   
   //--- Tier 3: Standard signals (Only with clear trend)
   bool tier3_buy = (rsi[idx] < InpRSIOversold) && (trend > 0) && (time[idx] - last_signal_time > 300); // 5+ min spacing
   bool tier3_sell = (rsi[idx] > InpRSIOverbought) && (trend < 0) && (time[idx] - last_signal_time > 300);
   
   //--- Add pullback detection as optional enhancement for premium signals
   bool pullback_detected = DetectPullback(idx, close, ema_fast);
   
   //--- Enhanced tier 1 signals with pullback (highest quality)
   bool enhanced_tier1_buy = tier1_buy && pullback_detected;
   bool enhanced_tier1_sell = tier1_sell && pullback_detected;
   
   //--- Final decision: Prioritize higher tiers, pullback optional for tier1 enhancement
   bool buy_signal = enhanced_tier1_buy || tier1_buy || tier2_buy || tier3_buy;
   bool sell_signal = enhanced_tier1_sell || tier1_sell || tier2_sell || tier3_sell;
   
   //--- Generate signals with tier identification
   if(is_signal_time && buy_signal)
   {
      string signal_type = "Standard Buy";
      if(enhanced_tier1_buy) signal_type = "ENHANCED PREMIUM BUY: Oversold + Trend + Pullback";
      else if(tier1_buy) signal_type = "PREMIUM BUY: Very Oversold + Strong Trend";
      else if(tier2_buy) signal_type = "QUALITY BUY: Oversold + Clear Trend";
      else if(tier3_buy) signal_type = "STANDARD BUY: RSI + Uptrend";
      
      GenerateBuySignal(idx, time[idx], close[idx], signal_type);
      last_signal_time = time[idx];
      if(InpDebugMode)
         Print("🔧 DEBUG: BUY SIGNAL - RSI=", DoubleToString(rsi[idx], 2), " Trend=", trend, " Type: ", signal_type);
   }
   else if(is_signal_time && sell_signal)
   {
      string signal_type = "Standard Sell";
      if(enhanced_tier1_sell) signal_type = "ENHANCED PREMIUM SELL: Overbought + Trend + Pullback";
      else if(tier1_sell) signal_type = "PREMIUM SELL: Very Overbought + Strong Trend";
      else if(tier2_sell) signal_type = "QUALITY SELL: Overbought + Clear Trend";
      else if(tier3_sell) signal_type = "STANDARD SELL: RSI + Downtrend";
      
      GenerateSellSignal(idx, time[idx], close[idx], signal_type);
      last_signal_time = time[idx];
      if(InpDebugMode)
         Print("🔧 DEBUG: SELL SIGNAL - RSI=", DoubleToString(rsi[idx], 2), " Trend=", trend, " Type: ", signal_type);
   }
   
   //--- Generate advance warning alerts (1 minute before potential signals)
   if(is_advance_warning_time && InpEnableAlerts)
   {
      //--- Prevent alert spam (only one advance alert per 5-minute cycle)
      if(time[idx] - last_advance_alert_time < 240) return; // At least 4 minutes between advance alerts
      
      //--- Check if conditions are building up for potential signals
      bool potential_buy = (tier1_buy || tier2_buy || tier3_buy) && (time[idx] - last_signal_time > 240); // At least 4 min since last
      bool potential_sell = (tier1_sell || tier2_sell || tier3_sell) && (time[idx] - last_signal_time > 240);
      
      if(potential_buy)
      {
         string advance_message = StringFormat("ADVANCE WARNING: BUY signal possible in 1 minute - RSI: %.1f - Trend: %s", 
                                              rsi[idx], trend > 0 ? "UP" : "DOWN");
         SendAdvanceAlert(advance_message);
         last_advance_alert_time = time[idx];
      }
      else if(potential_sell)
      {
         string advance_message = StringFormat("ADVANCE WARNING: SELL signal possible in 1 minute - RSI: %.1f - Trend: %s", 
                                              rsi[idx], trend > 0 ? "UP" : "DOWN");
         SendAdvanceAlert(advance_message);
         last_advance_alert_time = time[idx];
      }
   }
}

//+------------------------------------------------------------------+
//| Get trend direction                                              |
//+------------------------------------------------------------------+
int GetTrendDirection(double ema_fast, double ema_slow)
{
   double diff_percent = (ema_fast - ema_slow) / ema_slow * 100;
   
   if(diff_percent > 0.05) return 1;   // Bullish trend (balanced: 0.05% difference)
   if(diff_percent < -0.05) return -1; // Bearish trend (balanced: 0.05% difference)
   return 0; // Neutral/sideways
}

bool DetectPullback(int idx, const double &close[], const double &ema_fast[])
{
   //--- Simple pullback detection: price moved away from EMA and is coming back
   if(idx < 3) return false;
   
   //--- Safety check for array bounds
   if(idx+2 >= ArraySize(close) || idx+2 >= ArraySize(ema_fast)) return false;
   
   double current_distance = MathAbs(close[idx] - ema_fast[idx]);
   double prev_distance = MathAbs(close[idx+1] - ema_fast[idx+1]);
   double prev2_distance = MathAbs(close[idx+2] - ema_fast[idx+2]);
   
   //--- Check if we're moving back towards the EMA after moving away
   return (prev2_distance < prev_distance && prev_distance > current_distance);
}

//+------------------------------------------------------------------+
//| Check for bullish engulfing pattern                             |
//+------------------------------------------------------------------+
bool IsBullishEngulfing(int idx, const double &open[], const double &high[], 
                       const double &low[], const double &close[])
{
   if(idx < 1) return false;
   
   //--- Current candle is bullish
   bool current_bullish = close[idx] > open[idx];
   //--- Previous candle is bearish
   bool prev_bearish = close[idx+1] < open[idx+1];
   //--- Current candle engulfs previous
   bool engulfs = open[idx] < close[idx+1] && close[idx] > open[idx+1];
   
   return current_bullish && prev_bearish && engulfs;
}

//+------------------------------------------------------------------+
//| Check for bearish engulfing pattern                             |
//+------------------------------------------------------------------+
bool IsBearishEngulfing(int idx, const double &open[], const double &high[], 
                       const double &low[], const double &close[])
{
   if(idx < 1) return false;
   
   //--- Current candle is bearish
   bool current_bearish = close[idx] < open[idx];
   //--- Previous candle is bullish
   bool prev_bullish = close[idx+1] > open[idx+1];
   //--- Current candle engulfs previous
   bool engulfs = open[idx] > close[idx+1] && close[idx] < open[idx+1];
   
   return current_bearish && prev_bullish && engulfs;
}

//+------------------------------------------------------------------+
//| Generate buy signal                                              |
//+------------------------------------------------------------------+
void GenerateBuySignal(int idx, datetime signal_time, double price, string pattern)
{
   //--- Draw buy arrow as chart object instead of buffer
   DrawSignalArrow(signal_time, price - 10 * _Point, true);
   
   //--- Calculate stake
   double stake = CalculateStake();
   
   //--- Create signal record
   AddSignalToHistory(signal_time, signal_time + 300, 1, price, stake); // 5-minute expiry
   
   //--- Draw visual elements
   if(InpShowZones) DrawEntryZone(signal_time, price, true);
   if(InpShowLabels) DrawSignalLabel(signal_time, price, true, stake, pattern);
   
   //--- Send alerts only for actual signals (not general preparation alerts)
   if(InpEnableAlerts)
   {
      string message = StringFormat("BUY Signal Generated - %s - Entry: %.5f - Stake: %.2f - Expires: %s", 
                                   pattern, price, stake, TimeToString(signal_time + 300));
      SendAlert(message);
   }
   
   //--- Update dashboard counters immediately
   dashboard.total_trades++;
   dashboard.pending++;
   dashboard.suggested_stake = stake;
   
   //--- Force dashboard update
   if(InpShowDashboard)
      UpdateDashboard();
   
   if(InpDebugMode)
      Print("🔧 DEBUG: BUY signal generated - Time: ", TimeToString(signal_time), ", Price: ", DoubleToString(price, _Digits), ", Stake: $", stake);
}

//+------------------------------------------------------------------+
//| Generate sell signal                                             |
//+------------------------------------------------------------------+
void GenerateSellSignal(int idx, datetime signal_time, double price, string pattern)
{
   //--- Draw sell arrow as chart object instead of buffer
   DrawSignalArrow(signal_time, price + 10 * _Point, false);
   
   //--- Calculate stake
   double stake = CalculateStake();
   
   //--- Create signal record
   AddSignalToHistory(signal_time, signal_time + 300, -1, price, stake); // 5-minute expiry
   
   //--- Draw visual elements
   if(InpShowZones) DrawEntryZone(signal_time, price, false);
   if(InpShowLabels) DrawSignalLabel(signal_time, price, false, stake, pattern);
   
   //--- Send alerts only for actual signals (not general preparation alerts)
   if(InpEnableAlerts)
   {
      string message = StringFormat("SELL Signal Generated - %s - Entry: %.5f - Stake: %.2f - Expires: %s", 
                                   pattern, price, stake, TimeToString(signal_time + 300));
      SendAlert(message);
   }
   
   //--- Update dashboard counters immediately
   dashboard.total_trades++;
   dashboard.pending++;
   dashboard.suggested_stake = stake;
   
   //--- Force dashboard update
   if(InpShowDashboard)
      UpdateDashboard();
   
   if(InpDebugMode)
      Print("🔧 DEBUG: SELL signal generated - Time: ", TimeToString(signal_time), ", Price: ", DoubleToString(price, _Digits), ", Stake: $", stake);
}

//+------------------------------------------------------------------+
//| Calculate stake amount                                           |
//+------------------------------------------------------------------+
double CalculateStake()
{
   if(InpStakeMode == STAKE_FIXED)
      return InpFixedStake;
   else
   {
      double balance = AccountInfoDouble(ACCOUNT_BALANCE);
      return balance * InpRiskPercent / 100.0;
   }
}

//+------------------------------------------------------------------+
//| Add signal to history                                            |
//+------------------------------------------------------------------+
void AddSignalToHistory(datetime signal_time, datetime expiry_time, int type, 
                       double price, double stake)
{
   int size = ArraySize(signal_history);
   ArrayResize(signal_history, size + 1);
   
   signal_history[size].signal_time = signal_time;
   signal_history[size].expiry_time = expiry_time;
   signal_history[size].signal_type = type;
   signal_history[size].entry_price = price;
   signal_history[size].stake_amount = stake;
   signal_history[size].status = 0; // Pending
   
   // Initialize SL/TP simulation levels (for binary options: simulate 80% payout vs 100% loss)
   double sl_distance = price * 0.001; // 0.1% SL
   double tp_distance = price * 0.008; // 0.8% TP
   
   if(type == 1) // Buy signal
   {
      signal_history[size].sl_level = price - sl_distance;
      signal_history[size].tp_level = price + tp_distance;
   }
   else // Sell signal
   {
      signal_history[size].sl_level = price + sl_distance;
      signal_history[size].tp_level = price - tp_distance;
   }
   
   signal_history[size].sl_hit = false;
   signal_history[size].tp_hit = false;
   signal_history[size].exit_price = 0;
   signal_history[size].profit_loss = 0;
}

//+------------------------------------------------------------------+
//| Draw signal arrow (replaces indicator buffer)                   |
//+------------------------------------------------------------------+
void DrawSignalArrow(datetime time, double price, bool is_buy)
{
   string name = "Arrow_" + TimeToString(time);
   color arrow_color = is_buy ? InpBuyColor : InpSellColor;
   int arrow_code = is_buy ? 233 : 234; // Up arrow : Down arrow
   
   if(!ObjectCreate(0, name, OBJ_ARROW, 0, time, price))
   {
      Print("Failed to create signal arrow");
      return;
   }
   
   ObjectSetInteger(0, name, OBJPROP_ARROWCODE, arrow_code);
   ObjectSetInteger(0, name, OBJPROP_COLOR, arrow_color);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 3);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, false);
}

//+------------------------------------------------------------------+
//| Draw entry zone                                                  |
//+------------------------------------------------------------------+
void DrawEntryZone(datetime time, double price, bool is_buy)
{
   string name = "Zone_" + TimeToString(time);
   color zone_color = is_buy ? InpBuyZoneColor : InpSellZoneColor;
   
   //--- Create rectangle
   if(!ObjectCreate(0, name, OBJ_RECTANGLE, 0, time, price - 5*_Point, time + 300, price + 5*_Point))
   {
      Print("Failed to create zone rectangle");
      return;
   }
   
   ObjectSetInteger(0, name, OBJPROP_COLOR, zone_color);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, name, OBJPROP_FILL, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
}

//+------------------------------------------------------------------+
//| Draw signal label                                                |
//+------------------------------------------------------------------+
void DrawSignalLabel(datetime time, double price, bool is_buy, double stake, string pattern)
{
   string name = "Label_" + TimeToString(time);
   string text = StringFormat("%s\n Stake: $%.2f\n%s", 
                             is_buy ? "   BUY" : "   SELL", stake, pattern);
   
   if(!ObjectCreate(0, name, OBJ_TEXT, 0, time, price))
   {
      Print("Failed to create signal label");
      return;
   }
   
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, is_buy ? InpBuyColor : InpSellColor);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
   ObjectSetString(0, name, OBJPROP_FONT, "Arial Bold");
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT_LOWER);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
}

//+------------------------------------------------------------------+
//| Initialize dashboard                                             |
//+------------------------------------------------------------------+
void InitializeDashboard()
{
   //--- Reset dashboard data
   ZeroMemory(dashboard);
   dashboard.suggested_stake = CalculateStake();
   dashboard.backend_status = false;
   dashboard.backend_candles = 0;
   dashboard.backend_message = "CONNECTING...";
   
   if(!InpShowDashboard) return;
   
   //--- Create main dashboard background (DARK THEME) - Made bigger
   string bg_name = "Dashboard_BG";
   if(!ObjectCreate(0, bg_name, OBJ_RECTANGLE_LABEL, 0, 0, 0))
   {
      Print("Failed to create dashboard background");
      return;
   }
   
   ObjectSetInteger(0, bg_name, OBJPROP_XDISTANCE, DASH_X);
   ObjectSetInteger(0, bg_name, OBJPROP_YDISTANCE, DASH_Y);
   ObjectSetInteger(0, bg_name, OBJPROP_XSIZE, DASH_WIDTH);
   ObjectSetInteger(0, bg_name, OBJPROP_YSIZE, DASH_HEIGHT);
   ObjectSetInteger(0, bg_name, OBJPROP_BGCOLOR, C'15,17,21'); // Very dark background
   ObjectSetInteger(0, bg_name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, bg_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, bg_name, OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, bg_name, OBJPROP_WIDTH, 2);
   ObjectSetInteger(0, bg_name, OBJPROP_BACK, false);      // Display on top of chart
   ObjectSetInteger(0, bg_name, OBJPROP_ZORDER, 100);      // High z-order priority
   ObjectSetInteger(0, bg_name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, bg_name, OBJPROP_HIDDEN, false);

   //--- Create neon border effect
   string border_name = "Dashboard_Border";
   if(!ObjectCreate(0, border_name, OBJ_RECTANGLE_LABEL, 0, 0, 0))
   {
      Print("Failed to create dashboard border");
      return;
   }
   
   ObjectSetInteger(0, border_name, OBJPROP_XDISTANCE, DASH_X - 2);
   ObjectSetInteger(0, border_name, OBJPROP_YDISTANCE, DASH_Y - 2);
   ObjectSetInteger(0, border_name, OBJPROP_XSIZE, DASH_WIDTH + 4);
   ObjectSetInteger(0, border_name, OBJPROP_YSIZE, DASH_HEIGHT + 4);
   ObjectSetInteger(0, border_name, OBJPROP_BGCOLOR, C'0,255,255'); // Cyan neon border
   ObjectSetInteger(0, border_name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, border_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, border_name, OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, border_name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, border_name, OBJPROP_BACK, false);   // Display on top of chart
   ObjectSetInteger(0, border_name, OBJPROP_ZORDER, 101);   // Higher z-order than background
   ObjectSetInteger(0, border_name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, border_name, OBJPROP_HIDDEN, false);
   
   //--- Create title section background
   string title_bg = "Dashboard_TitleBG";
   if(!ObjectCreate(0, title_bg, OBJ_RECTANGLE_LABEL, 0, 0, 0))
   {
      Print("Failed to create title background");
      return;
   }
   
   ObjectSetInteger(0, title_bg, OBJPROP_XDISTANCE, DASH_X);
   ObjectSetInteger(0, title_bg, OBJPROP_YDISTANCE, DASH_Y);
   ObjectSetInteger(0, title_bg, OBJPROP_XSIZE, DASH_WIDTH);
   ObjectSetInteger(0, title_bg, OBJPROP_YSIZE, ROW2_Y + TITLE_HEIGHT_EXTRA);
   ObjectSetInteger(0, title_bg, OBJPROP_BGCOLOR, C'25,30,40'); // Darker title section
   ObjectSetInteger(0, title_bg, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, title_bg, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, title_bg, OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, title_bg, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, title_bg, OBJPROP_BACK, false);      // Display on top of chart
   ObjectSetInteger(0, title_bg, OBJPROP_ZORDER, 102);      // Higher z-order than border
   ObjectSetInteger(0, title_bg, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, title_bg, OBJPROP_HIDDEN, false);
   
   int STATS_MARGIN = 2;      // Margin from dashboard edge
   int STATS_SPACING = 5;    // Spacing between columns
   int ROW_BG1_Y = 83;
   int ROW_BG2_Y = 195;
   
   //--- Create stats section backgrounds with much better spacing
   CreateStatsSection("Stats_BG1", DASH_X + STATS_MARGIN, ROW_BG1_Y, DASH_WIDTH/2 - STATS_SPACING, STATS_HEIGHT, C'20,25,35'); // Performance stats
   CreateStatsSection("Stats_BG2", DASH_X + DASH_WIDTH/2 + STATS_MARGIN, ROW_BG1_Y, DASH_WIDTH/2 - STATS_SPACING, STATS_HEIGHT, C'20,25,35'); // Win rate stats
   CreateStatsSection("Stats_BG3", DASH_X + STATS_MARGIN, ROW_BG2_Y, DASH_WIDTH/2 - STATS_SPACING, STATS_HEIGHT, C'20,25,35'); // Trading stats
   CreateStatsSection("Stats_BG4", DASH_X + DASH_WIDTH/2 + STATS_MARGIN, ROW_BG2_Y, DASH_WIDTH/2 - STATS_SPACING, STATS_HEIGHT, C'20,25,35'); // System stats
   
   //--- Create main title with glow effect
   CreateGamerLabel("Dashboard_Title", "⚡ F L U X I A", DASH_X + DASH_WIDTH/2, ROW1_Y, C'0,255,255', 16, "Arial Black", ANCHOR_CENTER);
   CreateGamerLabel("Dashboard_Subtitle", "BINARY OPTIONS AI", DASH_X + DASH_WIDTH/2, ROW2_Y, C'255,100,255', 10, "Arial", ANCHOR_CENTER);
}

//+------------------------------------------------------------------+
//| Create stats section background                                  |
//+------------------------------------------------------------------+
void CreateStatsSection(string name, int x, int y, int width, int height, color bg_color)
{
   if(!ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0))
      return;
   
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, width);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, height);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg_color);
   ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DOT);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);          // Display on top of chart
   ObjectSetInteger(0, name, OBJPROP_ZORDER, 103);          // Higher z-order than title
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, false);
}

//+------------------------------------------------------------------+
//| Create gamer-style label                                         |
//+------------------------------------------------------------------+
void CreateGamerLabel(string name, string text, int x, int y, color clr, int font_size, string font, ENUM_ANCHOR_POINT anchor = ANCHOR_LEFT_UPPER)
{
   if(!ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0))
   {
      Print("Failed to create gamer label: ", name);
      return;
   }
   
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, font_size);
   ObjectSetString(0, name, OBJPROP_FONT, font);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);          // Display on top of chart
   ObjectSetInteger(0, name, OBJPROP_ZORDER, 104);          // Highest z-order for text
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
}

//+------------------------------------------------------------------+
//| Update dashboard                                                 |
//+------------------------------------------------------------------+
void UpdateDashboard()
{
   if(!InpShowDashboard) return;
   
   //--- Calculate win rate
   if(dashboard.total_trades > 0)
      dashboard.win_rate = (double)dashboard.wins / dashboard.total_trades * 100.0;
   
   //--- Performance Stats Section (Top Left) - Much better spacing
   CreateGamerLabel("Perf_Title", "📊 STATS", PERF_TITLE_X, ROW3_Y, C'100,255,255', 11, "Arial Bold", ANCHOR_CENTER);
   
   string stats_text = StringFormat("TRADES: %d", dashboard.total_trades);
   CreateGamerLabel("Dashboard_Total", stats_text, COL2_X, ROW4_Y, C'255,255,255', 10, "Arial", ANCHOR_CENTER);
   
   stats_text = StringFormat("WINS: %d", dashboard.wins);
   CreateGamerLabel("Dashboard_Wins", stats_text, COL1_X, ROW5_Y, C'0,255,100', 10, "Arial Bold");
   
   stats_text = StringFormat("LOSS: %d", dashboard.losses);
   CreateGamerLabel("Dashboard_Losses", stats_text, COL3_X, ROW5_Y, C'255,100,100', 10, "Arial Bold");
   
   stats_text = StringFormat("PENDING: %d", dashboard.pending);
   CreateGamerLabel("Dashboard_Pending2", stats_text, COL2_X, ROW6_Y, C'255,200,0', 9, "Arial", ANCHOR_CENTER);
   
   stats_text = StringFormat("PROFIT: $%.0f", (dashboard.wins * dashboard.suggested_stake * 0.85) - (dashboard.losses * dashboard.suggested_stake));
   CreateGamerLabel("Dashboard_Profit", stats_text, COL2_X, ROW7_Y, dashboard.wins > dashboard.losses ? C'0,255,100' : C'255,100,100', 9, "Arial Bold", ANCHOR_CENTER);
   
   //--- Win Rate Section (Top Right) - Better positioning
   CreateGamerLabel("WinRate_Title", "🎯 WIN RATE", WINRATE_TITLE_X, ROW3_Y, C'255,255,100', 11, "Arial Bold", ANCHOR_CENTER);
   
   stats_text = StringFormat("%.1f%%", dashboard.win_rate);
   color wr_color = dashboard.win_rate >= 70 ? C'0,255,100' : (dashboard.win_rate >= 60 ? C'255,255,0' : C'255,100,100');
   CreateGamerLabel("Dashboard_WinRate", stats_text, COL4_X, ROW4_Y + WINRATE_Y_OFFSET, wr_color, 20, "Arial Black", ANCHOR_CENTER);
   
   string rating = "LEGENDARY";
   if(dashboard.win_rate < 50) rating = "NOOB";
   else if(dashboard.win_rate < 60) rating = "AMATEUR"; 
   else if(dashboard.win_rate < 70) rating = "PRO";
   else if(dashboard.win_rate < 80) rating = "EXPERT";
   
   CreateGamerLabel("Dashboard_Rating", rating, COL4_X, ROW6_Y, C'255,100,255', 10, "Arial Bold", ANCHOR_CENTER);
   
   stats_text = "TARGET: 70%";
   CreateGamerLabel("Dashboard_Target", stats_text, COL4_X, ROW7_Y, C'150,150,150', 9, "Arial", ANCHOR_CENTER);
   
   //--- Trading Stats Section (Bottom Left) - Better layout
   CreateGamerLabel("Trade_Title", "💰 TRADING", TRADE_TITLE_X, ROW9_Y, C'255,255,100', 11, "Arial Bold", ANCHOR_CENTER);
   
   stats_text = StringFormat("STAKE: $%.0f", dashboard.suggested_stake);
   CreateGamerLabel("Dashboard_Stake", stats_text, COL2_X, ROW10_Y, C'100,255,255', 10, "Arial Bold", ANCHOR_CENTER);
   
   stats_text = StringFormat("MG1: %d", dashboard.mg1_count);
   CreateGamerLabel("Dashboard_MG1", stats_text, COL1_X, ROW11_Y, C'255,150,255', 9, "Arial");
   
   stats_text = StringFormat("MG2: %d", dashboard.mg2_count);
   CreateGamerLabel("Dashboard_MG2", stats_text, COL3_X, ROW11_Y, C'255,150,255', 9, "Arial");
   
   stats_text = "RISK: 2%";
   CreateGamerLabel("Dashboard_Risk", stats_text, COL2_X, ROW12_Y, C'255,200,100', 9, "Arial", ANCHOR_CENTER);
   
   // SL/TP Simulation Section
   CreateGamerLabel("SLTP_Title", "⚡ SL/TP SIM", SLTP_TITLE_X, ROW8_Y, C'255,200,100', 11, "Arial Bold", ANCHOR_CENTER);
   
   stats_text = StringFormat("TP HITS: %d", dashboard.tp_hits);
   CreateGamerLabel("Dashboard_TP", stats_text, COL4_X - TP_X_OFFSET, ROW10_1_Y, C'0,255,100', 9, "Arial");
   
   stats_text = StringFormat("SL HITS: %d", dashboard.sl_hits);
   CreateGamerLabel("Dashboard_SL", stats_text, COL4_X + SL_X_OFFSET, ROW10_1_Y, C'255,100,100', 9, "Arial");
   
   stats_text = StringFormat("SIM P/L: $%.0f", dashboard.simulated_tp_profit + dashboard.simulated_sl_profit);
   CreateGamerLabel("Dashboard_SimPL", stats_text, COL4_X, ROW11_1_Y, (dashboard.simulated_tp_profit + dashboard.simulated_sl_profit) > 0 ? C'0,255,100' : C'255,100,100', 9, "Arial Bold", ANCHOR_CENTER);
   
   // Calculate and display average profit per trade
   // if(dashboard.total_trades > 0)
   // {
   //   dashboard.avg_profit_per_trade = (dashboard.simulated_tp_profit + dashboard.simulated_sl_profit) / dashboard.total_trades;
   //   stats_text = StringFormat("AVG: $%.1f", dashboard.avg_profit_per_trade);
   //   CreateGamerLabel("Dashboard_AvgProfit", stats_text, COL4_X, ROW11_Y, dashboard.avg_profit_per_trade > 0 ? C'0,255,100' : C'255,100,100', 9, "Arial", ANCHOR_CENTER);
   // }
   
   stats_text = "EXPIRY: 5M";
   CreateGamerLabel("Dashboard_Expiry", stats_text, COL2_X, ROW13_Y, C'200,200,200', 9, "Arial", ANCHOR_CENTER);
   
   //--- System Stats Section (Bottom Right) - Better spacing
   // CreateGamerLabel("System_Title", "⚡ SYSTEM", COL4_X, ROW9_Y, C'100,255,255', 11, "Arial Bold", ANCHOR_CENTER);
   
   // stats_text = "ONLINE";
   // CreateGamerLabel("Dashboard_Status", stats_text, COL4_X, ROW10_Y, C'0,255,100', 10, "Arial Bold", ANCHOR_CENTER);
   
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   stats_text = StringFormat("%02d:%02d:%02d", dt.hour, dt.min, dt.sec);
   CreateGamerLabel("Dashboard_Time", stats_text, COL4_X, ROW12_1_Y, C'255,255,255', 10, "Courier New", ANCHOR_CENTER);
   
   stats_text = "FLUXIA OTC v2.0";
   CreateGamerLabel("Dashboard_Version", stats_text, COL4_X, ROW13_1_Y, C'150,150,150', 9, "Arial", ANCHOR_CENTER);
   
   //--- Create animated elements for extra coolness
   CreateAnimatedIndicator();
   
   dashboard.last_update = TimeCurrent();
}

//+------------------------------------------------------------------+
//| Create animated status indicator                                 |
//+------------------------------------------------------------------+
void CreateAnimatedIndicator()
{
   //--- Create pulsing indicator based on win rate
   string indicator_name = "Status_Indicator";
   if(!ObjectCreate(0, indicator_name, OBJ_RECTANGLE_LABEL, 0, 0, 0))
      return;
   
   color pulse_color = C'0,255,100'; // Green
   if(!backend_connected) pulse_color = C'255,100,100'; // Red
   
   ObjectSetInteger(0, indicator_name, OBJPROP_XDISTANCE, DASH_X + DASH_WIDTH - INDICATOR_X_OFFSET);
   ObjectSetInteger(0, indicator_name, OBJPROP_YDISTANCE, DASH_Y + INDICATOR_Y_OFFSET);
   ObjectSetInteger(0, indicator_name, OBJPROP_XSIZE, INDICATOR_SIZE);
   ObjectSetInteger(0, indicator_name, OBJPROP_YSIZE, INDICATOR_SIZE);
   ObjectSetInteger(0, indicator_name, OBJPROP_BGCOLOR, pulse_color);
   ObjectSetInteger(0, indicator_name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, indicator_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, indicator_name, OBJPROP_BACK, false);    // Display on top of chart
   ObjectSetInteger(0, indicator_name, OBJPROP_ZORDER, 105);    // Highest z-order for indicator
   ObjectSetInteger(0, indicator_name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, indicator_name, OBJPROP_HIDDEN, false);
}

//+------------------------------------------------------------------+
//| Calculate next signal time                                       |
//+------------------------------------------------------------------+
void CalculateNextSignalTime()
{
   datetime current_time = TimeCurrent();
   MqlDateTime dt;
   TimeToStruct(current_time, dt);
   
   //--- Calculate next 5-minute mark
   int next_minute = ((dt.min / 5) + 1) * 5;
   if(next_minute >= 60)
   {
      next_minute = 0;
      dt.hour++;
      if(dt.hour >= 24)
      {
         dt.hour = 0;
         dt.day++;
      }
   }
   
   dt.min = next_minute;
   dt.sec = 0;
   
   next_signal_time = StructToTime(dt);
}

void UpdateSignalStatus(const double &close[])
{
   datetime current_time = TimeCurrent();
   double current_price = close[0];
   
   bool any_updated = false;
   
   for(int i = 0; i < ArraySize(signal_history); i++)
   {
      if(signal_history[i].status != 0) continue; // Already processed
      
      //--- Check for SL/TP hits during signal lifetime (continuous monitoring)
      if(!signal_history[i].sl_hit && !signal_history[i].tp_hit)
      {
         if(signal_history[i].signal_type == 1) // Buy signal
         {
            if(current_price <= signal_history[i].sl_level)
            {
               signal_history[i].sl_hit = true;
               signal_history[i].exit_price = signal_history[i].sl_level;
               signal_history[i].profit_loss = -signal_history[i].stake_amount; // Full loss
               dashboard.sl_hits++;
               dashboard.simulated_sl_profit -= signal_history[i].stake_amount;
            }
            else if(current_price >= signal_history[i].tp_level)
            {
               signal_history[i].tp_hit = true;
               signal_history[i].exit_price = signal_history[i].tp_level;
               signal_history[i].profit_loss = signal_history[i].stake_amount * 0.8; // 80% profit
               dashboard.tp_hits++;
               dashboard.simulated_tp_profit += signal_history[i].profit_loss;
            }
         }
         else // Sell signal
         {
            if(current_price >= signal_history[i].sl_level)
            {
               signal_history[i].sl_hit = true;
               signal_history[i].exit_price = signal_history[i].sl_level;
               signal_history[i].profit_loss = -signal_history[i].stake_amount; // Full loss
               dashboard.sl_hits++;
               dashboard.simulated_sl_profit -= signal_history[i].stake_amount;
            }
            else if(current_price <= signal_history[i].tp_level)
            {
               signal_history[i].tp_hit = true;
               signal_history[i].exit_price = signal_history[i].tp_level;
               signal_history[i].profit_loss = signal_history[i].stake_amount * 0.8; // 80% profit
               dashboard.tp_hits++;
               dashboard.simulated_tp_profit += signal_history[i].profit_loss;
            }
         }
      }
      
      //--- Check if signal has expired
      if(current_time >= signal_history[i].expiry_time)
      {
         //--- Always determine win/loss using original binary options logic (regardless of SL/TP)
         bool is_win = false;
         if(signal_history[i].signal_type == 1) // Buy signal - price should go UP
            is_win = current_price > signal_history[i].entry_price;
         else // Sell signal - price should go DOWN  
            is_win = current_price < signal_history[i].entry_price;
         
         //--- If no SL/TP hit, set exit price and profit_loss for simulation
         if(!signal_history[i].sl_hit && !signal_history[i].tp_hit)
         {
            signal_history[i].exit_price = current_price;
            signal_history[i].profit_loss = is_win ? signal_history[i].stake_amount * 0.8 : -signal_history[i].stake_amount;
         }
         
         //--- Update status using original binary options logic
         signal_history[i].status = is_win ? 1 : -1;
         
         //--- Update dashboard counters
         dashboard.pending--;
         if(is_win)
         {
            dashboard.wins++;
            //--- Reset MG count on win
            dashboard.mg1_count = 0;
            dashboard.mg2_count = 0;
         }
         else
         {
            dashboard.losses++;
            //--- Track martingale progression on losses
            if(dashboard.mg1_count == 0)
               dashboard.mg1_count++;  // First loss triggers MG1
            else if(dashboard.mg2_count == 0)
               dashboard.mg2_count++;  // Second consecutive loss triggers MG2
         }
         
         any_updated = true;
         
         //--- Debug log
         if(InpDebugMode)
         {
            Print("🔧 DEBUG: Signal expired - ", (signal_history[i].signal_type == 1 ? "BUY" : "SELL"),
                  " Entry:", DoubleToString(signal_history[i].entry_price, 5),
                  " Exit:", DoubleToString(current_price, 5),
                  " Result:", (is_win ? "WIN" : "LOSS"));
         }
      }
   }
   
   //--- Force dashboard update if any signals were processed
   if(any_updated && InpShowDashboard)
      UpdateDashboard();
}

//+------------------------------------------------------------------+
//| Send alert message                                               |
//+------------------------------------------------------------------+
void SendAlert(string message)
{
   //--- In backtesting, only print to log to avoid spam
   if(MQLInfoInteger(MQL_TESTER))
   {
      Print("FLUXIA ALERT: ", message);
      return;
   }
   
   //--- In live trading, use all alert methods
   if(InpEnablePopups) Alert(message);
   if(InpEnablePushNotifications) SendNotification(message);
   if(InpEnableEmailAlerts) SendMail("Fluxia Alert", message);
   
   Print("FLUXIA ALERT: ", message);
}

//+------------------------------------------------------------------+
//| Send advance warning alert                                       |
//+------------------------------------------------------------------+
void SendAdvanceAlert(string message)
{
   //--- In backtesting, only print to log to avoid spam
   if(MQLInfoInteger(MQL_TESTER))
   {
      Print("FLUXIA ADVANCE WARNING: ", message);
      return;
   }
   
   //--- In live trading, use popup and notifications (but not email for advance warnings)
   if(InpEnablePopups) Alert("⚠️ " + message);
   if(InpEnablePushNotifications) SendNotification("⚠️ " + message);
   
   Print("FLUXIA ADVANCE WARNING: ", message);
}

//+------------------------------------------------------------------+
//| Cleanup dashboard objects                                        |
//+------------------------------------------------------------------+
void CleanupDashboard()
{
   // Main dashboard elements
   ObjectDelete(0, "Dashboard_BG");
   ObjectDelete(0, "Dashboard_Border");
   ObjectDelete(0, "Dashboard_TitleBG");
   ObjectDelete(0, "Dashboard_Title");
   ObjectDelete(0, "Dashboard_Subtitle");
   
   // Stats section backgrounds
   ObjectDelete(0, "Stats_BG1");
   ObjectDelete(0, "Stats_BG2");
   ObjectDelete(0, "Stats_BG3");
   ObjectDelete(0, "Stats_BG4");
   
   // Performance section
   ObjectDelete(0, "Perf_Title");
   ObjectDelete(0, "Dashboard_Total");
   ObjectDelete(0, "Dashboard_Wins");
   ObjectDelete(0, "Dashboard_Losses");
   
   // Win rate section
   ObjectDelete(0, "WinRate_Title");
   ObjectDelete(0, "Dashboard_WinRate");
   ObjectDelete(0, "Dashboard_Rating");
   
   // Trading section
   ObjectDelete(0, "Trade_Title");
   ObjectDelete(0, "Dashboard_Pending");
   ObjectDelete(0, "Dashboard_Stake");
   ObjectDelete(0, "Dashboard_MG");
   
   // System section
   ObjectDelete(0, "System_Title");
   ObjectDelete(0, "Dashboard_Status");
   ObjectDelete(0, "Dashboard_Time");
   ObjectDelete(0, "Dashboard_Version");
   
   // Backend section
   ObjectDelete(0, "Backend_Status");
   ObjectDelete(0, "Backend_Candles");
   ObjectDelete(0, "Historical_Link");
   
   // Trading section  
   ObjectDelete(0, "Trade_Title");
   ObjectDelete(0, "Dashboard_Pending2");
   ObjectDelete(0, "Dashboard_Stake");
   ObjectDelete(0, "Dashboard_MG1");
   ObjectDelete(0, "Dashboard_MG2");
   ObjectDelete(0, "Dashboard_Profit");
   ObjectDelete(0, "Dashboard_Target");
   ObjectDelete(0, "Dashboard_Risk");
   ObjectDelete(0, "Dashboard_Expiry");
   ObjectDelete(0, "Dashboard_AI");
   
   // SL/TP simulation section
   ObjectDelete(0, "SLTP_Title");
   ObjectDelete(0, "Dashboard_TP");
   ObjectDelete(0, "Dashboard_SL");
   ObjectDelete(0, "Dashboard_SimPL");
   ObjectDelete(0, "Dashboard_AvgProfit");
   
   // Animated elements
   ObjectDelete(0, "Status_Indicator");
}

//+------------------------------------------------------------------+
//| Cleanup signal objects                                           |
//+------------------------------------------------------------------+
void CleanupSignalObjects()
{
   //--- Remove all signal-related objects
   for(int i = ObjectsTotal(0) - 1; i >= 0; i--)
   {
      string name = ObjectName(0, i);
      if(StringFind(name, "Zone_") == 0 || StringFind(name, "Label_") == 0 || StringFind(name, "Arrow_") == 0)
         ObjectDelete(0, name);
   }
}

//+------------------------------------------------------------------+
//| Timer function for real-time updates                            |
//+------------------------------------------------------------------+
void OnTimer()
{
   static int timer_call_count = 0;
   timer_call_count++;
   
   if(InpDebugMode && timer_call_count <= 3) // Only show first 3 calls to avoid spam
      Print("🔧 DEBUG: OnTimer called #", timer_call_count, " at ", TimeToString(TimeLocal()));
   
   if(backend_connected)
   {
      // Get current UTC time to sync with OlympTrade backend
      datetime current_time = TimeGMT();
      if(current_time == 0) 
      {
         current_time = TimeLocal(); // Fallback if TimeGMT() fails
      }
      MqlDateTime dt;
      TimeToStruct(current_time, dt);
      
      // Request candles every :03 seconds (e.g., 12:00:03, 12:01:03, etc.)
      static datetime last_request_time = 0;
      static datetime last_debug_time = 0;
      
      if(dt.sec == 3 && current_time != last_request_time)
      {
         if(InpDebugMode)
            Print("🔧 DEBUG: Requesting candles at ", TimeToString(current_time), " (every :03 second)");
         
         RequestLatestCandles();
         last_request_time = current_time;
      }
      else if(InpDebugMode && current_time - last_debug_time >= 10) // Debug message every 10 seconds
      {
         int seconds_until_next = dt.sec <= 3 ? 3 - dt.sec : 63 - dt.sec;
         Print("🔧 DEBUG: Waiting for :03 second trigger (next in ", seconds_until_next, " seconds, current: :", dt.sec, ")");
         last_debug_time = current_time;
      }
   }
   else 
   {
      static datetime last_disconnect_debug = 0;
      datetime current_time = TimeGMT();
      if(current_time == 0) current_time = TimeLocal();
      if(InpDebugMode && current_time - last_disconnect_debug >= 30) // Every 30 seconds
      {
         Print("🔧 DEBUG: Backend isn't connected - attempting health check...");
         SubscribeToBackend(); // Try to reconnect
         last_disconnect_debug = current_time;
      }
   }
   
   //--- Update dashboard every 5 seconds
   if(InpShowDashboard)
      UpdateDashboard();
}

//+------------------------------------------------------------------+
//| Chart event handler                                              |
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   //--- Handle chart events if needed
   if(id == CHARTEVENT_CHART_CHANGE)
   {
      //--- Refresh dashboard on chart changes
      if(InpShowDashboard)
         UpdateDashboard();
   }
}

// TestBackendHealth function removed - using SubscribeToBackend as health check

//+------------------------------------------------------------------+
//| Extract currency pair from symbol name                           |
//+------------------------------------------------------------------+
string GetCurrencyPairFromSymbol()
{
   string symbol = Symbol();
   
   // Keep _OTC suffix for OlympTrade compatibility!
   // OlympTrade websocket expects format like "EURUSD_OTC"
   
   // If symbol already has _OTC, return as-is
   if(StringFind(symbol, "_OTC") > 0)
   {
      return symbol;
   }
   
   // If no _OTC suffix, add it (for OlympTrade compatibility)
   if(StringLen(symbol) >= 6)
   {
      string base_pair = StringSubstr(symbol, 0, 6);
      return base_pair + "_OTC";
   }
   
   return symbol + "_OTC";
}

//+------------------------------------------------------------------+
//| Check backend health and get candle count                        |
//+------------------------------------------------------------------+
bool SubscribeToBackend()
{
   if(InpBackendURL == "")
      return false;
      
   string url = InpBackendURL + "/health";
   string headers = "";
   
   uchar post[], result[];
   string result_headers;
   
   // Health endpoint uses GET request
   int res = WebRequest("GET", url, headers, InpConnectionTimeout, post, result, result_headers);
   
   if(InpDebugMode)
   {
      Print("🔧 DEBUG: Health check request to: ", url);
      Print("🔧 DEBUG: HTTP response code: ", res);
   }
   
   // Check for WebRequest permission issues
   if(res == -1)
   {
      Print("❌ WebRequest blocked! Add 127.0.0.1:8000 to MT5 allowed URLs");
      Print("💡 Tools → Options → Expert Advisors → Allow WebRequest → Add: 127.0.0.1:8000");
      return false;
   }
   
   if(res == 200)
   {
      string response = CharArrayToString(result);
      
      if(InpDebugMode)
         Print("🔧 DEBUG: Backend health response: ", response);
      
      // Parse response for status
      if(StringFind(response, "\"status\":\"healthy\"") > 0)
      {
         backend_subscribed = true;
         backend_connected = true;
         
         // Set initial candle count to 0, will be updated by first candle request
         available_candles_count = 0;
         
         dashboard.backend_status = true;
         dashboard.backend_candles = available_candles_count;
         
         return true;
      }
   }
   else
   {
      if(res == -1)
         Print("❌ Backend health check failed - WebRequest blocked");
      else if(res == 404)
         Print("❌ Backend health check failed - Endpoint not found");
      else
         Print("❌ Backend health check failed (HTTP ", res, ")");
   }
   
   backend_subscribed = false;
   backend_connected = false;
   dashboard.backend_status = false;
   return false;
}

//+------------------------------------------------------------------+
//| Parse OHLC data from backend JSON response                      |
//+------------------------------------------------------------------+
bool ParseOHLCFromResponse(string response, datetime &candle_time, double &open_price, double &high_price, double &low_price, double &close_price)
{
   if(InpDebugMode)
      Print("🔧 DEBUG: Parsing OHLC from response: ", StringLen(response), " chars");
      
   // Find candles array in JSON response
   int candles_pos = StringFind(response, "\"candles\":");
   if(candles_pos < 0) 
   {
      if(InpDebugMode)
         Print("🔧 DEBUG: No 'candles' field found in response");
      return false;
   }
   
   // Check if candles array is empty
   int empty_array_pos = StringFind(response, "[]", candles_pos);
   if(empty_array_pos > candles_pos && empty_array_pos < candles_pos + 20)
   {
      if(InpDebugMode)
         Print("🔧 DEBUG: Candles array is empty - no data available");
      return false;
   }
   
   // Look for first candle object
   int candle_start = StringFind(response, "{", candles_pos);
   if(candle_start < 0) 
   {
      if(InpDebugMode)
         Print("🔧 DEBUG: No candle object found in candles array");
      return false;
   }
   
   // Find the end of the first candle object
   int candle_end = StringFind(response, "}", candle_start);
   if(candle_end < 0)
   {
      if(InpDebugMode)
         Print("🔧 DEBUG: Could not find end of candle object");
      return false;
   }
   
   // Extract just the first candle object
   string candle_json = StringSubstr(response, candle_start, candle_end - candle_start + 1);
   
   if(InpDebugMode)
      Print("🔧 DEBUG: Extracted candle JSON: ", candle_json);
   
   // Extract OHLC values from the candle object
   if(ExtractJSONValue(candle_json, "timestamp", candle_time) &&
      ExtractJSONValue(candle_json, "open", open_price) &&
      ExtractJSONValue(candle_json, "high", high_price) &&
      ExtractJSONValue(candle_json, "low", low_price) &&
      ExtractJSONValue(candle_json, "close", close_price))
   {
      if(InpDebugMode)
         Print("🔧 DEBUG: Successfully parsed OHLC - Time:", TimeToString(candle_time), " OHLC:", open_price, "/", high_price, "/", low_price, "/", close_price);
      return true;
   }
   
   return false;
}

//+------------------------------------------------------------------+
//| Extract JSON value (simple parser)                              |
//+------------------------------------------------------------------+
bool ExtractJSONValue(string json, string key, double &value)
{
   string search_key = "\"" + key + "\":";
   int pos = StringFind(json, search_key);
   if(pos < 0) return false;
   
   pos += StringLen(search_key);
   int end_pos = StringFind(json, ",", pos);
   if(end_pos < 0) end_pos = StringFind(json, "}", pos);
   if(end_pos < 0) return false;
   
   string value_str = StringSubstr(json, pos, end_pos - pos);
   StringReplace(value_str, " ", "");
   StringReplace(value_str, "\"", "");
   
   value = StringToDouble(value_str);
   return true;
}

bool ExtractJSONValue(string json, string key, datetime &value)
{
   double temp_value;
   if(ExtractJSONValue(json, key, temp_value))
   {
      value = (datetime)temp_value;
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Update custom symbol with new OHLC data                         |
//+------------------------------------------------------------------+
void UpdateCustomSymbol(datetime candle_time, double open_price, double high_price, double low_price, double close_price)
{
   string symbol = Symbol();
   
   // Create MqlRates structure for the new candle
   MqlRates rates[1];
   rates[0].time = candle_time;
   rates[0].open = open_price;
   rates[0].high = high_price;
   rates[0].low = low_price;
   rates[0].close = close_price;
   rates[0].tick_volume = 100; // Default volume
   rates[0].spread = 0;
   rates[0].real_volume = 0;
   
   // Update custom symbol
   if(!CustomRatesUpdate(symbol, rates, 1))
   {
      if(InpEnableBackendLogging)
         Print("⚠️ Failed to update custom symbol: ", symbol);
   }
   else if(InpDebugMode)
   {
      Print("🔧 DEBUG: Updated ", symbol, " - Time:", TimeToString(candle_time), " OHLC:", open_price, "/", high_price, "/", low_price, "/", close_price);
   }
}

//+------------------------------------------------------------------+
//| Request latest candles from backend and update custom symbol    |
//+------------------------------------------------------------------+
void RequestLatestCandles()
{
   if(!backend_subscribed || InpBackendURL == "")
      return;
      
   // Get current UTC time for the request (OlympTrade uses UTC timezone)
   datetime current_time_utc = TimeGMT();
   if(current_time_utc == 0) 
   {
      // Fallback: convert local time to approximate UTC 
      current_time_utc = TimeLocal(); // This is not perfect but better than 0
   }
   
   // Subtract 1 minute because OlympTrade is calculating current minute OHLC
   // We want the completed previous minute's data
   datetime request_time = current_time_utc - 60; // 60 seconds = 1 minute
   
   MqlDateTime dt;
   TimeToStruct(request_time, dt);
   
   if(InpDebugMode)
      Print("🔧 DEBUG: Current UTC time: ", TimeToString(current_time_utc), ", Requesting previous minute: ", TimeToString(request_time));
   
   // Format time as ISO string (YYYY-MM-DD HH:MM:SS)  
   string time_str = StringFormat("%04d-%02d-%02d+%02d:%02d:%02d", 
                                  dt.year, dt.mon, dt.day, 
                                  dt.hour, dt.min, dt.sec);
   
   // Use new API format with time parameter
   string url = InpBackendURL + "/ea/candlesticks?currency_pair=" + current_symbol_pair + "&time=" + time_str;
   string headers = "";
   
   uchar post[], result[];
   string result_headers;
   
   // Use GET request with query parameters
   int res = WebRequest("GET", url, headers, InpConnectionTimeout, post, result, result_headers);
   
   if(InpDebugMode)
   {
      Print("🔧 DEBUG: Requesting candles from: ", url);
      Print("🔧 DEBUG: HTTP response code: ", res);
   }
   
   if(res == 200)
   {
      string response = CharArrayToString(result);
      
      if(InpDebugMode)
      {
         Print("🔧 DEBUG: Candles response: ", StringLen(response), " chars");
         Print("🔧 DEBUG: Response content: ", response);
      }
         
      // Parse response and update custom symbol with OHLC data
      if(StringFind(response, "\"success\":true") > 0 || StringFind(response, "[{") == 0)
      {
         if(InpDebugMode)
            Print("🔧 DEBUG: Candles request successful");
            
         // Parse OHLC data from response
         double open_price = 0, high_price = 0, low_price = 0, close_price = 0;
         datetime candle_time = 0;
         
         if(ParseOHLCFromResponse(response, candle_time, open_price, high_price, low_price, close_price))
         {
            // Update custom symbol with new candle data
            UpdateCustomSymbol(candle_time, open_price, high_price, low_price, close_price);
         }
         else 
         {
            if(InpDebugMode)
               Print("🔧 DEBUG: Failed to parse OHLC - likely no candle data available yet");
            
            // Check if we have any candles at all
            if(StringFind(response, "\"candles\":[]") > 0 || StringFind(response, "[]") == 0)
            {
               if(InpDebugMode)
                  Print("🔧 DEBUG: Backend has no candle data - OlympTrade may not be sending data or connection issue");
            }
         }
         
         // Update candle count from total_count field
         int total_pos = StringFind(response, "\"total_count\":");
         if(total_pos > 0)
         {
            string total_str = StringSubstr(response, total_pos + 14);
            int comma_pos = StringFind(total_str, ",");
            int brace_pos = StringFind(total_str, "}");
            int end_pos = comma_pos;
            if(comma_pos < 0 || (brace_pos > 0 && brace_pos < comma_pos))
               end_pos = brace_pos;
               
            if(end_pos > 0)
            {
               total_str = StringSubstr(total_str, 0, end_pos);
               StringReplace(total_str, " ", "");
               available_candles_count = (int)StringToInteger(total_str);
               
               dashboard.backend_candles = available_candles_count;
               dashboard.backend_status = true;
               
               // Check if we need to show candle count warning
               CheckCandleCount();
            }
         }
      }
   }
   else
   {
      backend_connected = false;
      dashboard.backend_status = false;
      
      if(res != 200 && InpEnableBackendLogging)
         Print("⚠️ Backend candles request failed (HTTP ", res, ")");
   }
}

//+------------------------------------------------------------------+
//| Check candle count and show warnings                             |
//+------------------------------------------------------------------+
void CheckCandleCount()
{
   if(backend_connected && available_candles_count < 500 && !low_candles_warning_shown)
   {
      // Create download history URL using the exact format requested
      historical_data_url = InpBackendURL + "/ea/candlesticks?currency_pair=" + current_symbol_pair + "&count=5&download=true";
      
      string warning_message = "Download latest 600 candles history here: " + historical_data_url;
      
      if(InpEnablePopups)
         Alert(warning_message);
      
      dashboard.backend_message = "LOW CANDLES: " + IntegerToString(available_candles_count) + "/500";
      low_candles_warning_shown = true;
   }
   else if(available_candles_count >= 500)
   {
      dashboard.backend_message = "READY: " + IntegerToString(available_candles_count) + " candles";
      low_candles_warning_shown = false;
   }
   else if(available_candles_count == 0)
   {
      dashboard.backend_message = "NO DATA";
   }
}