"""竞品价格监控：业务字段驱动。"""
from typing import Any, Dict

import pandas as pd

from ..cleaning import safe_divide
from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("competitor_price")
def competitor_price(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    pct = float(params.get("price_alert_pct", 0.1))
    logger = setup_logger("competitor_price", cfg["paths"]["log_dir"])

    path = params.get("input_path") or f"{cfg['paths']['data_dir']}/competitor_price.csv"
    df_raw = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)

    rename_map = {actual: biz for biz, actual in mapping.items() if actual}
    df = df_raw.rename(columns=rename_map)

    required = {"sku", "my_price", "competitor_price"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"缺少必需业务字段：{sorted(missing)}")

    df = df.copy()
    df["my_price"] = pd.to_numeric(df["my_price"], errors="coerce")
    df["competitor_price"] = pd.to_numeric(df["competitor_price"], errors="coerce")

    df["price_gap_pct"] = safe_divide(
        df["my_price"] - df["competitor_price"],
        df["competitor_price"],
        fill=0.0,
    ).round(4)

    df["alert"] = df["price_gap_pct"].apply(
        lambda x: "价格偏高" if x > pct else ("价格偏低" if x < -pct else "价格正常")
    )

    out = f"{cfg['paths']['output_dir']}/competitor_price.csv"
    write_csv_with_labels(df, out, labels)
    logger.info("竞品价格监控完成，%d 条，输出 %s", len(df), out)
    return df