#!/usr/bin/env python3
"""
Algorithmic Trading Backtester
===============================
Tests a Moving Average Crossover strategy on real historical stock data.
Calculates real quant metrics: Sharpe Ratio, Max Drawdown, Win Rate, CAGR.
Generates a professional HTML report with charts.

No API keys. No libraries. Pure Python.

How to run:
    python3 backtester.py

Author: Your Name
"""

import urllib.request
import json
import os
import math
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════
# CONFIGURATION — change these to test different strategies
# ═══════════════════════════════════════════════════════════

CONFIG = {
    "ticker": "AAPL",          # Stock to test (try TSLA, NVDA, MSFT, GOOGL)
    "starting_cash": 10000,    # How much money you start with ($)
    "short_window": 20,        # Short moving average (days) — fast signal
    "long_window": 50,         # Long moving average (days) — slow signal
    "position_size": 0.95,     # Use 95% of cash per trade
}

# ═══════════════════════════════════════════════════════════
# STEP 1: FETCH REAL HISTORICAL DATA FROM YAHOO FINANCE
# ═══════════════════════════════════════════════════════════

def fetch_historical_data(ticker):
    """
    Downloads 2 years of daily price data from Yahoo Finance.
    Returns a list of {"date": "...", "close": 123.45} dicts.
    """
    print(f"\n📡 Fetching 2 years of {ticker} data from Yahoo Finance...")

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2y"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]

        # Combine timestamps and prices, skip any None values
        prices = []
        for ts, price in zip(timestamps, closes):
            if price is not None:
                date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                prices.append({"date": date, "close": round(price, 4)})

        print(f"✅ Got {len(prices)} trading days of data")
        return prices

    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# STEP 2: CALCULATE MOVING AVERAGES
# ═══════════════════════════════════════════════════════════

def calculate_moving_average(prices, window):
    """
    Moving Average = average of the last N closing prices.
    Example: 20-day MA = average of last 20 days.
    Returns None for the first N-1 days (not enough data yet).
    """
    mas = []
    for i in range(len(prices)):
        if i < window - 1:
            mas.append(None)  # not enough data yet
        else:
            window_prices = [prices[j]["close"] for j in range(i - window + 1, i + 1)]
            avg = sum(window_prices) / window
            mas.append(round(avg, 4))
    return mas


# ═══════════════════════════════════════════════════════════
# STEP 3: RUN THE TRADING STRATEGY
# ═══════════════════════════════════════════════════════════

def run_strategy(prices, short_ma, long_ma, starting_cash, position_size):
    """
    Moving Average Crossover Strategy:
    - BUY  when short MA crosses ABOVE long MA (uptrend starting)
    - SELL when short MA crosses BELOW long MA (downtrend starting)

    This is one of the most classic quantitative trading strategies,
    used by real hedge funds and algo traders.
    """
    cash = starting_cash
    shares = 0
    position = "OUT"  # Are we in the market or not?
    trades = []
    portfolio_values = []

    print(f"\n⚙️  Running Moving Average Crossover strategy...")
    print(f"   Short window: {CONFIG['short_window']} days")
    print(f"   Long window:  {CONFIG['long_window']} days")

    for i in range(1, len(prices)):
        # Skip if we don't have both MAs yet
        if short_ma[i] is None or long_ma[i] is None:
            portfolio_values.append({"date": prices[i]["date"], "value": cash})
            continue
        if short_ma[i-1] is None or long_ma[i-1] is None:
            portfolio_values.append({"date": prices[i]["date"], "value": cash})
            continue

        price = prices[i]["close"]
        date  = prices[i]["date"]

        # CROSSOVER DETECTION
        # Was short below long yesterday? And now above? → BUY SIGNAL
        short_crossed_above = (short_ma[i-1] < long_ma[i-1]) and (short_ma[i] > long_ma[i])
        # Was short above long yesterday? And now below? → SELL SIGNAL
        short_crossed_below = (short_ma[i-1] > long_ma[i-1]) and (short_ma[i] < long_ma[i])

        # BUY
        if short_crossed_above and position == "OUT" and cash > price:
            shares_to_buy = int((cash * position_size) / price)
            if shares_to_buy > 0:
                cost = shares_to_buy * price
                cash -= cost
                shares += shares_to_buy
                position = "IN"
                trades.append({
                    "type": "BUY",
                    "date": date,
                    "price": price,
                    "shares": shares_to_buy,
                    "cost": round(cost, 2),
                    "cash_after": round(cash, 2),
                })

        # SELL
        elif short_crossed_below and position == "IN" and shares > 0:
            revenue = shares * price
            entry_trade = next((t for t in reversed(trades) if t["type"] == "BUY"), None)
            entry_cost = entry_trade["cost"] if entry_trade else revenue
            profit = revenue - entry_cost
            profit_pct = (profit / entry_cost) * 100

            cash += revenue
            trades.append({
                "type": "SELL",
                "date": date,
                "price": price,
                "shares": shares,
                "revenue": round(revenue, 2),
                "profit": round(profit, 2),
                "profit_pct": round(profit_pct, 2),
                "cash_after": round(cash, 2),
            })
            shares = 0
            position = "OUT"

        # Track portfolio value each day
        portfolio_value = cash + (shares * price)
        portfolio_values.append({
            "date": date,
            "value": round(portfolio_value, 2)
        })

    # Close any open position at end
    if position == "IN" and shares > 0:
        final_price = prices[-1]["close"]
        revenue = shares * final_price
        cash += revenue
        entry_trade = next((t for t in reversed(trades) if t["type"] == "BUY"), None)
        entry_cost = entry_trade["cost"] if entry_trade else revenue
        profit = revenue - entry_cost
        trades.append({
            "type": "SELL (Close)",
            "date": prices[-1]["date"],
            "price": final_price,
            "shares": shares,
            "revenue": round(revenue, 2),
            "profit": round(profit, 2),
            "profit_pct": round((profit / entry_cost) * 100, 2),
            "cash_after": round(cash, 2),
        })

    return trades, portfolio_values, cash


# ═══════════════════════════════════════════════════════════
# STEP 4: CALCULATE PERFORMANCE METRICS
# ═══════════════════════════════════════════════════════════

def calculate_metrics(trades, portfolio_values, starting_cash, prices):
    """
    Calculates the same metrics professional quants use to evaluate strategies.
    """

    final_value = portfolio_values[-1]["value"] if portfolio_values else starting_cash
    total_return = ((final_value - starting_cash) / starting_cash) * 100

    # CAGR — Compound Annual Growth Rate
    # How much does your money grow per year on average?
    years = len(portfolio_values) / 252  # ~252 trading days per year
    if years > 0 and final_value > 0:
        cagr = ((final_value / starting_cash) ** (1 / years) - 1) * 100
    else:
        cagr = 0

    # WIN RATE — what % of trades were profitable?
    sell_trades = [t for t in trades if "SELL" in t["type"]]
    winning_trades = [t for t in sell_trades if t.get("profit", 0) > 0]
    win_rate = (len(winning_trades) / len(sell_trades) * 100) if sell_trades else 0

    # MAX DRAWDOWN — worst peak-to-trough loss (risk measure)
    # A lower drawdown = less risk
    peak = starting_cash
    max_drawdown = 0
    for pv in portfolio_values:
        if pv["value"] > peak:
            peak = pv["value"]
        drawdown = (peak - pv["value"]) / peak * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    # SHARPE RATIO — return per unit of risk (higher = better)
    # > 1.0 is good, > 2.0 is excellent, used by every hedge fund
    daily_returns = []
    for i in range(1, len(portfolio_values)):
        prev = portfolio_values[i-1]["value"]
        curr = portfolio_values[i]["value"]
        if prev > 0:
            daily_returns.append((curr - prev) / prev)

    if daily_returns:
        avg_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)
        std_dev = math.sqrt(variance)
        risk_free_rate = 0.05 / 252  # ~5% annual risk-free rate daily
        sharpe = ((avg_return - risk_free_rate) / std_dev * math.sqrt(252)) if std_dev > 0 else 0
    else:
        sharpe = 0

    # BUY AND HOLD comparison — what if you just bought and held?
    buy_hold_return = ((prices[-1]["close"] - prices[0]["close"]) / prices[0]["close"]) * 100

    return {
        "final_value": round(final_value, 2),
        "total_return": round(total_return, 2),
        "cagr": round(cagr, 2),
        "win_rate": round(win_rate, 1),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe": round(sharpe, 2),
        "total_trades": len(sell_trades),
        "winning_trades": len(winning_trades),
        "buy_hold_return": round(buy_hold_return, 2),
        "alpha": round(total_return - buy_hold_return, 2),  # Did we beat buy & hold?
    }


# ═══════════════════════════════════════════════════════════
# STEP 5: GENERATE HTML REPORT
# ═══════════════════════════════════════════════════════════

def generate_report(ticker, prices, short_ma, long_ma, trades, portfolio_values, metrics, config):
    """
    Builds a beautiful, interactive HTML report.
    """

    date_generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # Prepare data for charts (sample every 3rd point to keep HTML small)
    sampled = list(range(0, len(portfolio_values), 3))
    pv_dates  = [portfolio_values[i]["date"] for i in sampled]
    pv_values = [portfolio_values[i]["value"] for i in sampled]

    # Price chart data
    price_dates  = [p["date"] for p in prices[::3]]
    price_closes = [p["close"] for p in prices[::3]]

    # Short and long MA (filter Nones)
    sma_data = [{"date": prices[i]["date"], "val": short_ma[i]} for i in range(0, len(prices), 3) if short_ma[i] is not None]
    lma_data = [{"date": prices[i]["date"], "val": long_ma[i]}  for i in range(0, len(prices), 3) if long_ma[i] is not None]

    # Buy/sell markers
    buy_markers  = [t for t in trades if t["type"] == "BUY"]
    sell_markers = [t for t in trades if "SELL" in t["type"]]

    # Trade table rows
    trade_rows = ""
    for t in trades:
        if t["type"] == "BUY":
            trade_rows += f"""
            <tr>
                <td><span class="badge badge-buy">BUY</span></td>
                <td>{t['date']}</td>
                <td>${t['price']:,.2f}</td>
                <td>{t['shares']}</td>
                <td>—</td>
                <td class="neutral">—</td>
            </tr>"""
        else:
            profit = t.get("profit", 0)
            pct    = t.get("profit_pct", 0)
            color  = "green" if profit >= 0 else "red"
            sign   = "+" if profit >= 0 else ""
            trade_rows += f"""
            <tr>
                <td><span class="badge badge-sell">SELL</span></td>
                <td>{t['date']}</td>
                <td>${t['price']:,.2f}</td>
                <td>{t['shares']}</td>
                <td class="{color}">{sign}${abs(profit):,.2f}</td>
                <td class="{color}">{sign}{pct}%</td>
            </tr>"""

    # Metrics color logic
    ret_color   = "green" if metrics["total_return"] >= 0 else "red"
    alpha_color = "green" if metrics["alpha"] >= 0 else "red"
    sharpe_color = "green" if metrics["sharpe"] >= 1 else "gold" if metrics["sharpe"] >= 0 else "red"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{ticker} Backtester Report</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #080b10;
    --surface: #0d1117;
    --surface2: #161b22;
    --border: #21262d;
    --text: #e6edf3;
    --muted: #7d8590;
    --green: #3fb950;
    --red: #f85149;
    --blue: #58a6ff;
    --gold: #d29922;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:var(--bg); color:var(--text); font-family:'Syne',sans-serif; padding:40px 24px; }}
  body::before {{ content:''; position:fixed; inset:0; background-image:linear-gradient(rgba(88,166,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(88,166,255,0.03) 1px,transparent 1px); background-size:40px 40px; pointer-events:none; }}
  .wrap {{ max-width:1100px; margin:0 auto; position:relative; }}
  h1 {{ font-size:36px; font-weight:800; letter-spacing:-1px; }}
  h1 span {{ color:var(--blue); }}
  .sub {{ color:var(--muted); font-family:'Space Mono',monospace; font-size:12px; margin-top:6px; margin-bottom:40px; }}
  .metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:16px; margin-bottom:32px; }}
  .metric {{ background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:20px; }}
  .metric-label {{ font-size:11px; color:var(--muted); font-family:'Space Mono',monospace; letter-spacing:1px; text-transform:uppercase; margin-bottom:8px; }}
  .metric-value {{ font-size:26px; font-weight:800; font-family:'Space Mono',monospace; }}
  .metric-sub {{ font-size:11px; color:var(--muted); margin-top:4px; }}
  .green {{ color:var(--green) !important; }}
  .red {{ color:var(--red) !important; }}
  .gold {{ color:var(--gold) !important; }}
  .neutral {{ color:var(--muted); }}
  .card {{ background:var(--surface); border:1px solid var(--border); border-radius:16px; padding:28px; margin-bottom:24px; }}
  .card h2 {{ font-size:14px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:var(--muted); font-family:'Space Mono',monospace; margin-bottom:20px; }}
  canvas {{ width:100% !important; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ text-align:left; padding:10px 14px; font-size:11px; font-family:'Space Mono',monospace; letter-spacing:1px; text-transform:uppercase; color:var(--muted); border-bottom:1px solid var(--border); }}
  td {{ padding:14px; font-size:13px; border-bottom:1px solid #0d1117; font-family:'Space Mono',monospace; }}
  tr:hover td {{ background:rgba(88,166,255,0.03); }}
  .badge {{ padding:3px 10px; border-radius:6px; font-size:11px; font-weight:700; font-family:'Space Mono',monospace; }}
  .badge-buy {{ background:rgba(63,185,80,0.15); color:var(--green); }}
  .badge-sell {{ background:rgba(248,81,73,0.15); color:var(--red); }}
  .strategy-box {{ background:var(--surface2); border-radius:12px; padding:20px; margin-bottom:20px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }}
  .strategy-item {{ display:flex; flex-direction:column; gap:4px; }}
  .strategy-label {{ font-size:11px; color:var(--muted); font-family:'Space Mono',monospace; }}
  .strategy-value {{ font-size:15px; font-weight:700; font-family:'Space Mono',monospace; }}
  .footer {{ text-align:center; color:var(--border); font-size:12px; margin-top:40px; font-family:'Space Mono',monospace; }}
  .vs-bar {{ display:flex; gap:16px; margin-bottom:16px; }}
  .vs-item {{ flex:1; background:var(--surface2); border-radius:10px; padding:16px; text-align:center; }}
  .vs-label {{ font-size:11px; color:var(--muted); font-family:'Space Mono',monospace; margin-bottom:6px; }}
  .vs-val {{ font-size:20px; font-weight:800; font-family:'Space Mono',monospace; }}
</style>
</head>
<body>
<div class="wrap">

  <h1>📊 <span>{ticker}</span> Backtest Report</h1>
  <p class="sub">Generated on {date_generated} · MA({config['short_window']}/{config['long_window']}) Crossover Strategy · 2 Year Period</p>

  <!-- Strategy Config -->
  <div class="strategy-box">
    <div class="strategy-item">
      <div class="strategy-label">TICKER</div>
      <div class="strategy-value">{ticker}</div>
    </div>
    <div class="strategy-item">
      <div class="strategy-label">STARTING CAPITAL</div>
      <div class="strategy-value">${config['starting_cash']:,}</div>
    </div>
    <div class="strategy-item">
      <div class="strategy-label">STRATEGY</div>
      <div class="strategy-value">MA {config['short_window']}/{config['long_window']}</div>
    </div>
  </div>

  <!-- Key Metrics -->
  <div class="metrics">
    <div class="metric">
      <div class="metric-label">Final Value</div>
      <div class="metric-value">${metrics['final_value']:,.0f}</div>
      <div class="metric-sub">Started with ${config['starting_cash']:,}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Total Return</div>
      <div class="metric-value {ret_color}">{'+' if metrics['total_return'] >= 0 else ''}{metrics['total_return']}%</div>
      <div class="metric-sub">Over 2 years</div>
    </div>
    <div class="metric">
      <div class="metric-label">CAGR</div>
      <div class="metric-value">{metrics['cagr']}%</div>
      <div class="metric-sub">Annual growth rate</div>
    </div>
    <div class="metric">
      <div class="metric-label">Sharpe Ratio</div>
      <div class="metric-value {sharpe_color}">{metrics['sharpe']}</div>
      <div class="metric-sub">&gt;1.0 is good</div>
    </div>
    <div class="metric">
      <div class="metric-label">Max Drawdown</div>
      <div class="metric-value red">-{metrics['max_drawdown']}%</div>
      <div class="metric-sub">Worst peak-to-trough</div>
    </div>
    <div class="metric">
      <div class="metric-label">Win Rate</div>
      <div class="metric-value">{metrics['win_rate']}%</div>
      <div class="metric-sub">{metrics['winning_trades']}/{metrics['total_trades']} trades won</div>
    </div>
  </div>

  <!-- vs Buy & Hold -->
  <div class="card">
    <h2>Strategy vs Buy &amp; Hold</h2>
    <div class="vs-bar">
      <div class="vs-item">
        <div class="vs-label">YOUR STRATEGY</div>
        <div class="vs-val {ret_color}">{'+' if metrics['total_return'] >= 0 else ''}{metrics['total_return']}%</div>
      </div>
      <div class="vs-item">
        <div class="vs-label">BUY &amp; HOLD</div>
        <div class="vs-val {'green' if metrics['buy_hold_return'] >= 0 else 'red'}">{'+' if metrics['buy_hold_return'] >= 0 else ''}{metrics['buy_hold_return']}%</div>
      </div>
      <div class="vs-item">
        <div class="vs-label">ALPHA (EDGE)</div>
        <div class="vs-val {alpha_color}">{'+' if metrics['alpha'] >= 0 else ''}{metrics['alpha']}%</div>
      </div>
    </div>
  </div>

  <!-- Portfolio Value Chart -->
  <div class="card">
    <h2>Portfolio Value Over Time</h2>
    <canvas id="portfolioChart" height="250"></canvas>
  </div>

  <!-- Price + MA Chart -->
  <div class="card">
    <h2>Price Chart with Moving Averages</h2>
    <canvas id="priceChart" height="250"></canvas>
  </div>

  <!-- Trade Log -->
  <div class="card">
    <h2>Trade Log ({len(trades)} total trades)</h2>
    <table>
      <thead>
        <tr>
          <th>Type</th><th>Date</th><th>Price</th><th>Shares</th><th>Profit/Loss</th><th>Return</th>
        </tr>
      </thead>
      <tbody>{trade_rows}</tbody>
    </table>
  </div>

  <p class="footer">Built with Python · Data from Yahoo Finance · For educational purposes only · Not financial advice</p>
</div>

<script>
// ── Portfolio Value Chart ──────────────────────────────────
(function() {{
  const canvas = document.getElementById('portfolioChart');
  const ctx = canvas.getContext('2d');
  const W = canvas.offsetWidth; const H = 250;
  canvas.width = W; canvas.height = H;

  const dates  = {json.dumps(pv_dates)};
  const values = {json.dumps(pv_values)};
  const start  = {config['starting_cash']};

  const pad = {{top:20, bottom:30, left:70, right:10}};
  const min = Math.min(...values) * 0.98;
  const max = Math.max(...values) * 1.02;
  const xOf = i => pad.left + (i/(values.length-1))*(W-pad.left-pad.right);
  const yOf = v => pad.top + (1-(v-min)/(max-min))*(H-pad.top-pad.bottom);

  // Grid
  ctx.strokeStyle = 'rgba(255,255,255,0.04)'; ctx.lineWidth = 1;
  for(let i=0;i<=4;i++) {{
    const yp = pad.top + i/4*(H-pad.top-pad.bottom);
    ctx.beginPath(); ctx.moveTo(pad.left,yp); ctx.lineTo(W-pad.right,yp); ctx.stroke();
    const val = max - i/4*(max-min);
    ctx.fillStyle='#7d8590'; ctx.font='10px Space Mono';
    ctx.fillText('$'+Math.round(val).toLocaleString(), 2, yp+4);
  }}

  // Starting line
  ctx.strokeStyle='rgba(88,166,255,0.3)'; ctx.lineWidth=1; ctx.setLineDash([4,4]);
  const startY = yOf(start);
  ctx.beginPath(); ctx.moveTo(pad.left,startY); ctx.lineTo(W-pad.right,startY); ctx.stroke();
  ctx.setLineDash([]);

  // Fill
  const finalUp = values[values.length-1] >= start;
  ctx.beginPath();
  ctx.moveTo(xOf(0), yOf(values[0]));
  values.forEach((v,i) => ctx.lineTo(xOf(i), yOf(v)));
  ctx.lineTo(xOf(values.length-1), H-pad.bottom);
  ctx.lineTo(xOf(0), H-pad.bottom);
  ctx.closePath();
  ctx.fillStyle = finalUp ? 'rgba(63,185,80,0.07)' : 'rgba(248,81,73,0.07)';
  ctx.fill();

  // Line
  ctx.beginPath();
  ctx.moveTo(xOf(0), yOf(values[0]));
  values.forEach((v,i) => ctx.lineTo(xOf(i), yOf(v)));
  ctx.strokeStyle = finalUp ? '#3fb950' : '#f85149';
  ctx.lineWidth=2; ctx.lineJoin='round'; ctx.stroke();

  // Date labels
  ctx.fillStyle='#7d8590'; ctx.font='9px Space Mono';
  [0, Math.floor(dates.length/2), dates.length-1].forEach(i => {{
    ctx.fillText(dates[i], xOf(i)-20, H-8);
  }});
}})();

// ── Price + MA Chart ───────────────────────────────────────
(function() {{
  const canvas = document.getElementById('priceChart');
  const ctx = canvas.getContext('2d');
  const W = canvas.offsetWidth; const H = 250;
  canvas.width = W; canvas.height = H;

  const dates  = {json.dumps(price_dates)};
  const closes = {json.dumps(price_closes)};
  const sma    = {json.dumps([d['val'] for d in sma_data])};
  const lma    = {json.dumps([d['val'] for d in lma_data])};
  const buys   = {json.dumps([{'date':t['date'],'price':t['price']} for t in buy_markers])};
  const sells  = {json.dumps([{'date':t['date'],'price':t['price']} for t in sell_markers])};

  const pad = {{top:20, bottom:30, left:70, right:10}};
  const allVals = [...closes, ...sma, ...lma].filter(v => v !== null);
  const min = Math.min(...allVals) * 0.98;
  const max = Math.max(...allVals) * 1.02;
  const xOf = i => pad.left + (i/(closes.length-1))*(W-pad.left-pad.right);
  const yOf = v => pad.top + (1-(v-min)/(max-min))*(H-pad.top-pad.bottom);

  // Grid
  ctx.strokeStyle='rgba(255,255,255,0.04)'; ctx.lineWidth=1;
  for(let i=0;i<=4;i++) {{
    const yp = pad.top + i/4*(H-pad.top-pad.bottom);
    ctx.beginPath(); ctx.moveTo(pad.left,yp); ctx.lineTo(W-pad.right,yp); ctx.stroke();
    const val = max - i/4*(max-min);
    ctx.fillStyle='#7d8590'; ctx.font='10px Space Mono';
    ctx.fillText('$'+Math.round(val), 2, yp+4);
  }}

  // Price line
  ctx.beginPath(); ctx.moveTo(xOf(0), yOf(closes[0]));
  closes.forEach((v,i) => ctx.lineTo(xOf(i), yOf(v)));
  ctx.strokeStyle='rgba(88,166,255,0.6)'; ctx.lineWidth=1.5; ctx.lineJoin='round'; ctx.stroke();

  // Short MA
  ctx.beginPath();
  let started = false;
  sma.forEach((v,i) => {{
    if(v===null) return;
    const xi = xOf(i); const yi = yOf(v);
    if(!started) {{ ctx.moveTo(xi,yi); started=true; }} else ctx.lineTo(xi,yi);
  }});
  ctx.strokeStyle='#f59e0b'; ctx.lineWidth=1.5; ctx.stroke();

  // Long MA
  ctx.beginPath(); started=false;
  lma.forEach((v,i) => {{
    if(v===null) return;
    const xi = xOf(i); const yi = yOf(v);
    if(!started) {{ ctx.moveTo(xi,yi); started=true; }} else ctx.lineTo(xi,yi);
  }});
  ctx.strokeStyle='#ec4899'; ctx.lineWidth=1.5; ctx.stroke();

  // Buy markers
  buys.forEach(b => {{
    const idx = dates.indexOf(b.date);
    if(idx<0) return;
    const xi=xOf(idx); const yi=yOf(b.price);
    ctx.beginPath(); ctx.arc(xi,yi,5,0,Math.PI*2);
    ctx.fillStyle='#3fb950'; ctx.fill();
  }});

  // Sell markers
  sells.forEach(s => {{
    const idx = dates.indexOf(s.date);
    if(idx<0) return;
    const xi=xOf(idx); const yi=yOf(s.price);
    ctx.beginPath(); ctx.arc(xi,yi,5,0,Math.PI*2);
    ctx.fillStyle='#f85149'; ctx.fill();
  }});

  // Legend
  const leg = [
    {{color:'rgba(88,166,255,0.6)', label:'Price'}},
    {{color:'#f59e0b', label:'MA{config["short_window"]}'}},
    {{color:'#ec4899', label:'MA{config["long_window"]}'}},
    {{color:'#3fb950', label:'Buy'}},
    {{color:'#f85149', label:'Sell'}},
  ];
  leg.forEach((l,i) => {{
    ctx.fillStyle=l.color;
    ctx.fillRect(pad.left + i*80, H-12, 10, 10);
    ctx.fillStyle='#7d8590'; ctx.font='9px Space Mono';
    ctx.fillText(l.label, pad.left+i*80+14, H-4);
  }});
}})();


</script>
</body>
</html>"""

    os.makedirs("outputs", exist_ok=True)
    path = "outputs/backtest_report.html"
    with open(path, "w") as f:
        f.write(html)
    return path


# ═══════════════════════════════════════════════════════════
# MAIN — runs everything
# ═══════════════════════════════════════════════════════════

def main():
    print("\n🤖 Algorithmic Trading Backtester")
    print("=" * 45)

    # Let user customize or use defaults
    print(f"\nDefault config: {CONFIG['ticker']} | MA({CONFIG['short_window']}/{CONFIG['long_window']}) | ${CONFIG['starting_cash']:,} starting")
    custom = input("Press Enter to use defaults, or type a ticker to change (e.g. TSLA): ").strip().upper()
    if custom:
        CONFIG["ticker"] = custom

    ticker = CONFIG["ticker"]

    # Fetch data
    prices = fetch_historical_data(ticker)
    if not prices:
        print("❌ Could not fetch data. Check your internet connection.")
        return

    # Calculate moving averages
    print(f"\n📐 Calculating MA{CONFIG['short_window']} and MA{CONFIG['long_window']}...")
    short_ma = calculate_moving_average(prices, CONFIG["short_window"])
    long_ma  = calculate_moving_average(prices, CONFIG["long_window"])

    # Run strategy
    trades, portfolio_values, final_cash = run_strategy(
        prices, short_ma, long_ma,
        CONFIG["starting_cash"],
        CONFIG["position_size"]
    )

    # Calculate metrics
    metrics = calculate_metrics(trades, portfolio_values, CONFIG["starting_cash"], prices)

    # Print summary
    print("\n" + "=" * 45)
    print("📊 BACKTEST RESULTS")
    print("=" * 45)
    print(f"Starting Capital : ${CONFIG['starting_cash']:,}")
    print(f"Final Value      : ${metrics['final_value']:,.2f}")
    print(f"Total Return     : {'+' if metrics['total_return'] >= 0 else ''}{metrics['total_return']}%")
    print(f"CAGR             : {metrics['cagr']}%")
    print(f"Sharpe Ratio     : {metrics['sharpe']} {'✅' if metrics['sharpe'] >= 1 else '⚠️'}")
    print(f"Max Drawdown     : -{metrics['max_drawdown']}%")
    print(f"Win Rate         : {metrics['win_rate']}% ({metrics['winning_trades']}/{metrics['total_trades']} trades)")
    print(f"Buy & Hold       : {'+' if metrics['buy_hold_return'] >= 0 else ''}{metrics['buy_hold_return']}%")
    print(f"Alpha vs B&H     : {'+' if metrics['alpha'] >= 0 else ''}{metrics['alpha']}%")
    print(f"Total Trades     : {len(trades)}")

    # Generate report
    print("\n⏳ Generating HTML report...")
    path = generate_report(ticker, prices, short_ma, long_ma, trades, portfolio_values, metrics, CONFIG)
    print(f"✅ Report saved: {path}")
    print(f"\n👉 Open it now:")
    print(f"   open {path}")


if __name__ == "__main__":
    main()
