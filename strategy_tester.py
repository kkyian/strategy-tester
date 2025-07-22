"""Simple command line crypto strategy backtester with optional Gemini analysis."""

import json
from typing import Callable, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import requests
import yfinance as yf

# === Gemini AI Setup ===
GEMINI_API_KEY = ""  # Optional: Insert your key if you want Gemini feedback
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)
HEADERS = {"Content-Type": "application/json"}

# === Load Historical Data ===
def get_crypto_data(symbol: str = "BTC-USD", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Download historical OHLC data using yfinance."""

    return yf.download(symbol, period=period, interval=interval)


# === Strategy Loading ===
def load_strategy(path: str) -> Tuple[Callable[[pd.DataFrame], pd.DataFrame], str]:
    """Load a strategy file and return the apply_strategy function and source."""

    try:
        with open(path, "r") as f:
            code = f.read()
    except FileNotFoundError as exc:
        raise FileNotFoundError("❌ File not found.") from exc

    local_env: dict = {}
    exec(code, {}, local_env)
    strategy_func = local_env.get("apply_strategy")

    if not callable(strategy_func):
        raise ValueError("Strategy file must define an 'apply_strategy(df)' function")

    return strategy_func, code

# === Evaluate Performance ===
def evaluate_performance(df: pd.DataFrame) -> dict:
    """Calculate simple performance statistics."""

    df = df.copy()
    if "position" not in df.columns or "returns" not in df.columns:
        raise ValueError("Strategy must define both 'position' and 'returns'.")

    df["position"] = df["position"].fillna(0).astype(float)
    df["returns"] = df["returns"].fillna(0).astype(float)
    df["strategy"] = df["position"] * df["returns"]
    df["equity"] = 1000 * (1 + df["strategy"]).cumprod()

    final_equity = df["equity"].iloc[-1]
    total_return = final_equity - 1000
    win_rate = (df["strategy"] > 0).sum() / len(df)
    sharpe = df["strategy"].mean() / df["strategy"].std() * (252 ** 0.5) if df["strategy"].std() != 0 else 0

    return {
        "final_equity": round(final_equity, 2),
        "total_return": round(total_return, 2),
        "win_rate": round(win_rate, 4),
        "sharpe_ratio": round(sharpe, 2),
        "df": df
    }

# === Gemini AI Analysis ===
def analyze_with_gemini(code: str, metrics: dict) -> str:
    """Return a short analysis of the strategy using Gemini, if configured."""

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
    response = requests.post(f"{GEMINI_URL}?key={GEMINI_API_KEY}", headers=HEADERS, data=json.dumps(data))

    if response.ok:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"❌ Gemini error: {response.text}"

def plot_equity(df: pd.DataFrame) -> None:
    """Display a basic equity curve."""

    df["equity"].plot(title="Equity Curve", figsize=(10, 5))
    plt.xlabel("Date")
    plt.ylabel("Equity ($)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def main() -> None:
    print("📊 Crypto Strategy Tester (BTC-USD)")
    strategy_path = input(
        "Enter path to your strategy file (e.g. example_strategy.py): "
    ).strip()

    try:
        strategy_func, code = load_strategy(strategy_path)
    except Exception as exc:
        print(str(exc))
        return

    print("📥 Downloading data...")
    df = get_crypto_data()

    try:
        df = strategy_func(df.copy())
    except Exception as exc:
        print(f"❌ Strategy execution failed:\n{exc}")
        return

    try:
        results = evaluate_performance(df)
        df = results.pop("df")
    except Exception as exc:
        print(f"❌ Backtest error: {exc}")
        return

    print("\n📈 Backtest Results:")
    for key, value in results.items():
        print(f"{key}: {value}")

    print("\n🤖 Gemini Feedback:")
    print(analyze_with_gemini(code, results))

    plot_equity(df)


if __name__ == "__main__":
    main()
