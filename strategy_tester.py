import yfinance as yf
import pandas as pd
import requests
import json
import matplotlib.pyplot as plt

# === Gemini AI Setup ===
GEMINI_API_KEY = ""  # Optional: Insert your key if you want Gemini feedback
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
HEADERS = {"Content-Type": "application/json"}

# === Load Historical Data ===
def get_crypto_data(symbol="BTC-USD", period="1y", interval="1d"):
    return yf.download(symbol, period=period, interval=interval)

# === Apply Strategy from .py File ===
def apply_user_strategy(df, strategy_code):
    local_env = {"df": df.copy(), "pd": pd}
    try:
        exec(strategy_code, {}, local_env)
        return local_env["df"]
    except Exception as e:
        raise RuntimeError(f"❌ Strategy execution failed:\n{e}")

# === Evaluate Performance ===
def evaluate_performance(df):
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
def analyze_with_gemini(code, metrics):
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

# === Main Entry ===
if __name__ == "__main__":
    print("📊 Crypto Strategy Tester (BTC-USD)")
    strategy_path = input("Enter path to your strategy file (e.g. example_strategy.py): ").strip()

    try:
        with open(strategy_path, "r") as f:
            strategy_code = f.read()
    except FileNotFoundError:
        print("❌ File not found.")
        exit(1)

    print("📥 Downloading data...")
    df = get_crypto_data()

    try:
        df = apply_user_strategy(df, strategy_code)
    except Exception as e:
        print(str(e))
        exit(1)

    try:
        results = evaluate_performance(df)
        df = results.pop("df")
    except Exception as e:
        print(f"❌ Backtest error: {e}")
        exit(1)

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
