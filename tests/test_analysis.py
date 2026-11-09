import pandas as pd
import pytest

from stocklens.analysis import add_moving_averages, calculate_metrics, validate_stock_data


def sample_frame():
    closes = [100, 110, 105, 120, 90]
    return pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"],
            "Open": [99, 101, 108, 106, 118],
            "High": [102, 112, 111, 122, 121],
            "Low": [98, 100, 103, 105, 88],
            "Close": closes,
            "Volume": [1000, 1200, 900, 1500, 2000],
        }
    )


def test_metrics_have_expected_return_and_drawdown():
    metrics = calculate_metrics(sample_frame())
    assert metrics["period_return_percent"] == -10.0
    assert metrics["max_drawdown_percent"] == -25.0


def test_moving_average_is_calculated():
    result = add_moving_averages(sample_frame(), windows=(2,))
    assert result["MA2"].iloc[-1] == 105.0


def test_missing_column_is_rejected():
    invalid = sample_frame().drop(columns=["Volume"])
    with pytest.raises(ValueError, match="Volume"):
        validate_stock_data(invalid)


def test_duplicate_date_is_rejected():
    invalid = sample_frame()
    invalid.loc[4, "Date"] = invalid.loc[3, "Date"]
    with pytest.raises(ValueError, match="重複"):
        validate_stock_data(invalid)

