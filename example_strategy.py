import pandas as pd


def apply_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """Example simple moving average crossover strategy."""
    df = df.copy()
    df["short_ma"] = df["Close"].rolling(window=10).mean()
    df["long_ma"] = df["Close"].rolling(window=30).mean()

    df["signal"] = 0
    df.loc[df["short_ma"] > df["long_ma"], "signal"] = 1
    df.loc[df["short_ma"] < df["long_ma"], "signal"] = -1

    df["position"] = df["signal"].shift()
    df["returns"] = df["Close"].pct_change()
    return df

