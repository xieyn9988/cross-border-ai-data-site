"""滞销库存识别：库存天数超过阈值的 SKU。"""
from typing import Any, Dict, List

import pandas as pd

from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("slow_moving")
def slow_moving(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    threshold_days = int(params.get("threshold_days", 90))
    logger = setup_logger("slow_moving", cfg["paths"]["log_dir"])

    input_files: List[str] = params.get("input_files") or []
    if not input_files:
        single = params.get("input_path") or f"{cfg['paths']['data_dir']}/inventory.csv"
        input_files = [single]

    frames = []
    for path in input_files:
        df = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)
        rename_map = {a: b for b, a in mapping.items() if a}
        df = df.rename(columns=rename_map)
        for col in ["stock", "daily_sales", "cost"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)

    # 库存天数：daily_sales 为 0 或 NA 时视为无穷（滞销）
    df["_daily"] = df["daily_sales"].fillna(0)
    df["库存天数"] = df.apply(
        lambda r: round(r["stock"] / r["_daily"], 1)
        if r["_daily"] > 0 else 9999,
        axis=1,
    )

    slow = df[df["库存天数"] > threshold_days].copy()

    out_dir = cfg["paths"]["output_dir"]
    output_files: List = []

    if not slow.empty:
        if "cost" in slow.columns:
            slow["积压成本"] = (slow["stock"] * slow["cost"]).round(2)
        else:
            slow["积压成本"] = 0

        slow["建议"] = slow["库存天数"].apply(
            lambda d: "立即清仓" if d > 365 else ("促销甩卖" if d > 180 else "考虑降价")
        )

        slow = slow.sort_values("库存天数", ascending=False)
        cols = [c for c in [
            "platform", "shop", "sku_code", "product_name",
            "stock", "daily_sales", "库存天数", "积压成本", "建议",
        ] if c in slow.columns]
        slow = slow[cols]

        write_csv_with_labels(slow, f"{out_dir}/slow_moving.csv", labels)
        output_files.append(("slow_moving.csv", "滞销库存清单"))

    slow.attrs["output_files"] = output_files
    logger.info("滞销库存识别完成：%d 条 SKU（阈值 %d 天）", len(slow), threshold_days)
    return slow