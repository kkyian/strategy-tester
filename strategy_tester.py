"""Simple cryptocurrency strategy backtester."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

import matplotlib.pyplot as plt
import pandas as pd
import requests
import yfinance as yf

# === Gemini AI Setup ===
GEMINI_API_KEY = ""  # Optional: Insert your key if you want Gemini feedback
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
HEADERS = {"Content-Type": "application/json"}

INITIAL_CAPITAL = 1000

# === Load Historical Data ===
def get_crypto_data(symbol: str = "BTC-USD", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Download historical price data from Yahoo Finance."""

    return yf.download(symbol, period=period, interval=interval, auto_adjust=True)

# === Apply Strategy from .py File ===
def apply_user_strategy(df: pd.DataFrame, strategy_code: str) -> pd.DataFrame:
    """Execute the user strategy code and return the modified DataFrame."""

    local_env: Dict[str, Any] = {"df": df.copy(), "pd": pd}
    try:
        exec(strategy_code, {}, local_env)
        return local_env["df"]
    except Exception as e:  # pragma: no cover - runtime execution
        raise RuntimeError(f"❌ Strategy execution failed:\n{e}") from e

# === Evaluate Performance ===
def evaluate_performance(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate equity curve and performance statistics."""

    df = df.copy()
    if "position" not in df.columns or "returns" not in df.columns:
        raise ValueError("Strategy must define both 'position' and 'returns'.")

    df["position"] = df["position"].fillna(0).astype(float)
    df["returns"] = df["returns"].fillna(0).astype(float)
    df["strategy"] = df["position"] * df["returns"]
    df["equity"] = INITIAL_CAPITAL * (1 + df["strategy"]).cumprod()

    final_equity = df["equity"].iloc[-1]
    total_return = final_equity - INITIAL_CAPITAL
    win_rate = (df["strategy"] > 0).sum() / len(df)
    strat_std = df["strategy"].std()
    sharpe = df["strategy"].mean() / strat_std * (252 ** 0.5) if strat_std else 0

    return {
        "final_equity": round(final_equity, 2),
        "total_return": round(total_return, 2),
        "win_rate": round(win_rate, 4),
        "sharpe_ratio": round(sharpe, 2),
        "df": df
    }

# === Gemini AI Analysis ===
def analyze_with_gemini(code: str, metrics: Dict[str, Any]) -> str:
    """Send the strategy and metrics to Gemini for feedback."""

    if not GEMINI_API_KEY:
        return "Gemini feedback skipped (API key not provided)."

    prompt = f"""
Analyze this crypto trading strategy:

--- Code ---
{code}

--- Backtest ---
Final Equity: ${metrics['final_equity']}
Total Return: ${metrics['total_return']}
Win Rate: {metrics['win_rate'] * 100:.2f}%
Sharpe Ratio: {metrics['sharpe_ratio']}
"""

    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            headers=HEADERS,
            data=json.dumps(data),
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - network call
        return f"❌ Gemini error: {exc}"

    return response.json()["candidates"][0]["content"]["parts"][0]["text"]

# === Main Entry ===
def main() -> None:
    """Entry point for the command line interface."""

    parser = argparse.ArgumentParser(description="Crypto Strategy Tester")
    parser.add_argument("strategy", help="Path to the strategy file")
    parser.add_argument("--symbol", default="BTC-USD", help="Ticker symbol")
    parser.add_argument("--period", default="1y", help="Data period")
    parser.add_argument("--interval", default="1d", help="Data interval")
    args = parser.parse_args()

    try:
        with open(args.strategy, "r") as f:
            strategy_code = f.read()
    except FileNotFoundError:
        print("❌ File not found.")
        sys.exit(1)

    print("📥 Downloading data...")
    df = get_crypto_data(args.symbol, args.period, args.interval)

    try:
        df = apply_user_strategy(df, strategy_code)
    except Exception as exc:  # pragma: no cover - user code errors
        print(exc)
        sys.exit(1)

    try:
        results = evaluate_performance(df)
        df = results.pop("df")
    except Exception as exc:
        print(f"❌ Backtest error: {exc}")
        sys.exit(1)

    print("\n📈 Backtest Results:")
    for key, value in results.items():
        print(f"{key}: {value}")

    print("\n🤖 Gemini Feedback:")
    print(analyze_with_gemini(strategy_code, results))

    df["equity"].plot(title="Equity Curve", figsize=(10, 5))
    plt.xlabel("Date")
    plt.ylabel("Equity ($)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
