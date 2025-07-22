# 🧠 Crypto Strategy Tester

A backtesting and AI analysis tool for cryptocurrency trading strategies using Python, yfinance, and Google Gemini.

## 🔧 Features

- ✅ Run trading logic from a `.py` strategy file
- 📈 Backtests with PnL, Sharpe Ratio, Win Rate
- 🤖 Gemini AI explains your strategy's logic and performance
- 📉 Auto-generated equity curve
- 💥 Fully alignment-safe (no pandas errors)

## 🚀 Quick Start

```bash
git clone https://github.com/kkyian/strategy-tester.git
cd strategy-tester
python strategy_tester.py
```
When prompted, enter: `example_strategy.py`

## 📂 Files

- `strategy_tester.py` - main backtesting engine
- `example_strategy.py` - sample SMA crossover strategy

## ✍️ Customize

Edit `example_strategy.py` to test your own logic or create a new file with
an `apply_strategy(df)` function that returns the modified `DataFrame`.

The function must assign `df["position"]` and `df["returns"]`.
Gemini API (optional): paste your key in `GEMINI_API_KEY` to get AI insights.

## 🧠 Powered By

- yfinance

- Google Gemini API

- matplotlib



