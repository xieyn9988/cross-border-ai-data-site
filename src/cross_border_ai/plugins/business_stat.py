"""业务数据统计：业务字段驱动。"""
from typing import Any, Dict

import pandas as pd

from ..cleaning import safe_divide
from ..exceptions import BusinessLogicError
from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("business_stat")
def calc_business_stat(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    logger = setup_logger("business_stat", cfg["paths"]["log_dir"])

    path = params.get("input_path") or f"{cfg['paths']['data_dir']}/shop_data.csv"
    df_raw = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)

    rename_map = {actual: biz for biz, actual in mapping.items() if actual}
    df = df_raw.rename(columns=rename_map)

    for col in ["amount", "quantity", "sales", "exposure", "order_num"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "region" not in df.columns or "amount" not in df.columns:
        raise BusinessLogicError("缺少必需业务字段：region / amount")

    df = df.dropna(subset=["region", "amount"])
    if df.empty:
        raise BusinessLogicError("清洗后无有效数据")

    agg_map: Dict[str, Any] = {}
    agg_map["total_amount"] = ("amount", "sum")
    if "sales" in df.columns:
        agg_map["total_sales"] = ("sales", "sum")
    if "order_num" in df.columns:
        agg_map["total_order"] = ("order_num", "sum")
    elif "quantity" in df.columns:
        agg_map["total_order"] = ("quantity", "sum")
    if "exposure" in df.columns:
        agg_map["total_exposure"] = ("exposure", "sum")

    stat = df.groupby("region").agg(**agg_map).reset_index()

    if "total_exposure" in stat.columns and "total_order" in stat.columns:
        stat["conversion_rate"] = safe_divide(
            stat["total_order"], stat["total_exposure"]
        )

    out = f"{cfg['paths']['output_dir']}/stat_result.csv"
    write_csv_with_labels(stat, out, labels)
    logger.info("业务统计完成，%d 个区域，输出 %s", len(stat), out)
    return stat