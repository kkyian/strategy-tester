# example_strategy.py
# ruff: noqa: F821

# Strategy: Simple Moving Average Crossover

# Calculate short and long moving averages
df["short_ma"] = df["Close"].rolling(window=10).mean()
df["long_ma"] = df["Close"].rolling(window=30).mean()

# Generate trading signals
df["signal"] = 0
df.loc[df["short_ma"] > df["long_ma"], "signal"] = 1   # Buy
df.loc[df["short_ma"] < df["long_ma"], "signal"] = -1  # Sell

# Generate positions (shift to simulate trading delay)
df["position"] = df["signal"].shift()

# Daily returns
df["returns"] = df["Close"].pct_change()
