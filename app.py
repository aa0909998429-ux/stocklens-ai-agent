"""StockLens offline CSV prototype."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import gradio as gr
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from stocklens.analysis import add_moving_averages, calculate_metrics, load_stock_csv


def analyze_csv(file_path: str | None):
    """Run the deterministic CSV tools and return a summary, chart and trace."""

    if not file_path:
        raise gr.Error("請先上傳 CSV 檔案")

    try:
        data = load_stock_csv(file_path)
        enriched = add_moving_averages(data, windows=(5, 20))
        metrics = calculate_metrics(data)
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc

    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.72, 0.28],
    )
    figure.add_trace(go.Scatter(x=enriched["Date"], y=enriched["Close"], name="收盤價"), row=1, col=1)
    figure.add_trace(go.Scatter(x=enriched["Date"], y=enriched["MA5"], name="5 日均線"), row=1, col=1)
    figure.add_trace(go.Scatter(x=enriched["Date"], y=enriched["MA20"], name="20 日均線"), row=1, col=1)
    figure.add_trace(go.Bar(x=enriched["Date"], y=enriched["Volume"], name="成交量"), row=2, col=1)
    figure.update_layout(
        title="歷史收盤價、移動平均與成交量",
        hovermode="x unified",
        height=620,
        margin=dict(l=30, r=20, t=60, b=30),
    )
    figure.update_yaxes(title_text="價格", row=1, col=1)
    figure.update_yaxes(title_text="成交量", row=2, col=1)

    summary = f"""### 歷史資料摘要

- 資料期間：{metrics['start_date']} 至 {metrics['end_date']}
- 觀測筆數：{metrics['observations']}
- 期初／期末收盤：{metrics['start_close']} → {metrics['end_close']}
- 期間報酬率：{metrics['period_return_percent']}%
- 日波動度：{metrics['daily_volatility_percent']}%
- 年化歷史波動度：{metrics['annualized_historical_volatility_percent']}%
- 最大回撤：{metrics['max_drawdown_percent']}%

> 以上為歷史描述性統計，不代表未來表現，也不構成投資建議。
"""
    trace = [
        {"step": 1, "tool": "load_stock_csv", "result": {"rows": len(data)}},
        {"step": 2, "tool": "add_moving_averages", "arguments": {"windows": [5, 20]}},
        {"step": 3, "tool": "calculate_metrics", "result": metrics},
        {"step": 4, "tool": "draw_stock_chart", "result": "plotly figure"},
    ]
    return summary, figure, json.loads(json.dumps(trace, ensure_ascii=False))


with gr.Blocks(title="StockLens") as demo:
    gr.Markdown(
        "# StockLens：股市歷史資料分析原型\n"
        "上傳 OHLCV CSV，使用 Python 工具計算歷史指標並顯示工具紀錄。"
    )
    with gr.Row():
        csv_file = gr.File(label="歷史股價 CSV", file_types=[".csv"], type="filepath")
        analyze_button = gr.Button("開始分析", variant="primary")
    with gr.Row():
        chart = gr.Plot(label="歷史圖表")
        with gr.Column():
            summary_box = gr.Markdown()
            tool_trace = gr.JSON(label="工具呼叫紀錄")
    gr.Markdown(
        "**免責聲明：本系統僅供課程展示、資料分析與學習使用，"
        "不構成投資建議或獲利保證。**"
    )
    analyze_button.click(analyze_csv, inputs=csv_file, outputs=[summary_box, chart, tool_trace])


if __name__ == "__main__":
    demo.launch()

