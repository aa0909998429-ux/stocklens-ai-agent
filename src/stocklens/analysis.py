"""Deterministic historical stock-data analysis tools.

These functions calculate descriptive historical metrics only. They do not
predict prices or produce buy/sell recommendations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ("Date", "Open", "High", "Low", "Close", "Volume")
PRICE_COLUMNS = ("Open", "High", "Low", "Close")


def validate_stock_data(data: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize an OHLCV dataframe.

    Returns a cleaned copy sorted by date. Invalid or ambiguous input raises a
    ValueError so the caller can show a clear message instead of guessing.
    """

    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"缺少必要欄位：{', '.join(missing)}")

    frame = data.loc[:, REQUIRED_COLUMNS].copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    for column in (*PRICE_COLUMNS, "Volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if frame.isna().any().any():
        invalid_columns = frame.columns[frame.isna().any()].tolist()
        raise ValueError(f"下列欄位含有空值或無法解析的資料：{', '.join(invalid_columns)}")
    if frame["Date"].duplicated().any():
        raise ValueError("日期欄位含有重複值")
    if (frame[list(PRICE_COLUMNS)] <= 0).any().any():
        raise ValueError("價格必須大於 0")
    if (frame["Volume"] < 0).any():
        raise ValueError("成交量不可小於 0")
    if (frame["High"] < frame[["Open", "Low", "Close"]].max(axis=1)).any():
        raise ValueError("High 不可小於同日的 Open、Low 或 Close")
    if (frame["Low"] > frame[["Open", "High", "Close"]].min(axis=1)).any():
        raise ValueError("Low 不可大於同日的 Open、High 或 Close")
    if len(frame) < 2:
        raise ValueError("至少需要兩筆不同日期的資料")

    return frame.sort_values("Date").reset_index(drop=True)


def load_stock_csv(path: str | Path) -> pd.DataFrame:
    """Load and validate a UTF-8 CSV file containing OHLCV data."""

    return validate_stock_data(pd.read_csv(path))


def add_moving_averages(
    data: pd.DataFrame,
    windows: Iterable[int] = (5, 20),
) -> pd.DataFrame:
    """Return a copy with simple moving-average columns added."""

    frame = validate_stock_data(data)
    for window in windows:
        if not isinstance(window, int) or window < 2 or window > 250:
            raise ValueError("移動平均視窗必須是 2 到 250 的整數")
        frame[f"MA{window}"] = frame["Close"].rolling(window=window).mean()
    return frame


def calculate_metrics(data: pd.DataFrame, trading_days: int = 252) -> dict[str, float | int | str]:
    """Calculate descriptive return, volatility and drawdown metrics."""

    frame = validate_stock_data(data)
    if trading_days <= 0:
        raise ValueError("trading_days 必須大於 0")

    closes = frame["Close"]
    daily_returns = closes.pct_change().dropna()
    running_peak = closes.cummax()
    drawdown = closes / running_peak - 1

    daily_volatility = float(daily_returns.std(ddof=1)) if len(daily_returns) > 1 else 0.0
    return {
        "start_date": frame["Date"].iloc[0].date().isoformat(),
        "end_date": frame["Date"].iloc[-1].date().isoformat(),
        "observations": int(len(frame)),
        "start_close": round(float(closes.iloc[0]), 4),
        "end_close": round(float(closes.iloc[-1]), 4),
        "period_return_percent": round(float((closes.iloc[-1] / closes.iloc[0] - 1) * 100), 4),
        "daily_volatility_percent": round(daily_volatility * 100, 4),
        "annualized_historical_volatility_percent": round(
            daily_volatility * np.sqrt(trading_days) * 100,
            4,
        ),
        "max_drawdown_percent": round(float(drawdown.min() * 100), 4),
    }

