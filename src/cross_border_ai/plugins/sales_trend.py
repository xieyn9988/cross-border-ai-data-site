"""销售趋势分析：按日/周看销售额与订单量走势。"""
from typing import Any, Dict, List

import pandas as pd

from ..io_utils import (
    parse_datetime_safe,
    read_csv_any_encoding,
    write_csv_with_labels,
)
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("sales_trend")
def sales_trend(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    logger = setup_logger("sales_trend", cfg["paths"]["log_dir"])

    input_files: List[str] = params.get("input_files") or []
    if not input_files:
        single = params.get("input_path") or f"{cfg['paths']['data_dir']}/order_sample.csv"
        input_files = [single]

    frames = []
    for path in input_files:
        df = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)
        rename_map = {a: b for b, a in mapping.items() if a}
        df = df.rename(columns=rename_map)
        if "pay_time" in df.columns:
            df["pay_time"] = parse_datetime_safe(df["pay_time"])
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["pay_time", "amount"])
    if df.empty:
        raise ValueError("清洗后无有效数据")

    out_dir = cfg["paths"]["output_dir"]
    output_files: List = []

    # ---- 按日 ----
    df["_date"] = df["pay_time"].dt.date.astype(str)
    daily = (
        df.groupby("_date")
        .agg(订单数=("order_id", "nunique"), 总成交额=("amount", "sum"))
        .reset_index()
        .rename(columns={"_date": "日期"})
    )
    daily["总成交额"] = daily["总成交额"].round(2)
    daily["环比"] = daily["总成交额"].pct_change().round(4)
    write_csv_with_labels(daily, f"{out_dir}/sales_trend_daily.csv", labels)
    output_files.append(("sales_trend_daily.csv", "日销售趋势"))

    # ---- 按月 ----
    df["_month"] = df["pay_time"].dt.to_period("M").astype(str)
    monthly = (
        df.groupby("_month")
        .agg(订单数=("order_id", "nunique"), 总成交额=("amount", "sum"))
        .reset_index()
        .rename(columns={"_month": "月份"})
    )
    monthly["总成交额"] = monthly["总成交额"].round(2)
    monthly["环比"] = monthly["总成交额"].pct_change().round(4)
    write_csv_with_labels(monthly, f"{out_dir}/sales_trend_monthly.csv", labels)
    output_files.append(("sales_trend_monthly.csv", "月销售趋势"))

    daily.attrs["output_files"] = output_files
    logger.info("销售趋势分析完成：%d 天数据", len(daily))
    return daily