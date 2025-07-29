import sqlite3
import json
import pandas as pd
import yfinance as yf
import requests
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret-key"  # In production, use a secure key
DB_PATH = "database.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, api_key TEXT)"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS strategies (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, code TEXT, feedback TEXT)"
    )
    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# === Backtest and Gemini ===

def get_crypto_data(symbol: str = "BTC-USD", period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    return yf.download(symbol, period=period, interval=interval)


def evaluate_performance(df: pd.DataFrame) -> dict:
    df = df.copy()
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
    }


def analyze_with_gemini(code: str, metrics: dict, api_key: str) -> str:
    if not api_key:
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
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    response = requests.post(f"{url}?key={api_key}", headers={"Content-Type": "application/json"}, data=json.dumps(data))
    if response.ok:
        try:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return "Unexpected Gemini response."
    return f"Gemini error: {response.text}"


def run_strategy(code: str) -> dict:
    local_env = {}
    exec(code, {}, local_env)
    strategy_func = local_env.get("apply_strategy")
    if not callable(strategy_func):
        raise ValueError("Strategy must define an apply_strategy(df) function")

    df = get_crypto_data()
    df = strategy_func(df.copy())
    results = evaluate_performance(df)
    return results


# === Routes ===

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = generate_password_hash(request.form["password"].strip())
        api_key = request.form["api_key"].strip()
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password, api_key) VALUES (?, ?, ?)", (username, password, api_key))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Username already exists"
        conn.close()
        return redirect(url_for("login"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        return "Invalid credentials"
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    strategies = conn.execute("SELECT id, code, feedback FROM strategies WHERE user_id=?", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("dashboard.html", strategies=strategies)


@app.route("/add_strategy", methods=["POST"])
def add_strategy():
    if "user_id" not in session:
        return redirect(url_for("login"))
    code = request.form["code"]
    conn = get_db_connection()
    conn.execute("INSERT INTO strategies (user_id, code, feedback) VALUES (?, ?, '')", (session["user_id"], code))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/analyze/<int:strategy_id>", methods=["POST"])
def analyze(strategy_id: int):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    strat = conn.execute(
        "SELECT strategies.code, users.api_key FROM strategies JOIN users ON users.id = strategies.user_id WHERE strategies.id=? AND users.id=?",
        (strategy_id, session["user_id"]),
    ).fetchone()
    if not strat:
        conn.close()
        return "Strategy not found"
    code, api_key = strat["code"], strat["api_key"]
    try:
        metrics = run_strategy(code)
        feedback = analyze_with_gemini(code, metrics, api_key)
    except Exception as exc:
        feedback = f"Error: {exc}"
    conn.execute("UPDATE strategies SET feedback=? WHERE id=?", (feedback, strategy_id))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5050, debug=True)
