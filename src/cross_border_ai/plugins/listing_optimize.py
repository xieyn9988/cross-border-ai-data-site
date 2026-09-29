"""Listing 页面优化：业务字段驱动。"""
from typing import Any, Dict

import pandas as pd

from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("listing_optimize")
def batch_listing_optimize(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    title_tpl = cfg["prompt_templates"]["listing_title"]
    desc_tpl = cfg["prompt_templates"]["listing_desc"]
    logger = setup_logger("listing_optimize", cfg["paths"]["log_dir"])

    path = params.get("input_path") or f"{cfg['paths']['data_dir']}/listing.csv"
    df_raw = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)

    rename_map = {actual: biz for biz, actual in mapping.items() if actual}
    df = df_raw.rename(columns=rename_map)

    required = {"pid", "raw_title", "raw_desc"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"缺少必需业务字段：{sorted(missing)}")

    df = df.copy()
    df["is_abnormal"] = df["pid"].isna()
    df["optimized_title"] = df.apply(
        lambda r: "数据异常"
        if r["is_abnormal"]
        else title_tpl.format(raw_title=r["raw_title"]),
        axis=1,
    )
    df["optimized_desc"] = df.apply(
        lambda r: "数据异常"
        if r["is_abnormal"]
        else desc_tpl.format(raw_desc=r["raw_desc"]),
        axis=1,
    )

    out_df = df.rename(columns={"raw_title": "old_title", "raw_desc": "old_desc"})[
        ["pid", "old_title", "optimized_title", "old_desc", "optimized_desc"]
    ]
    out = f"{cfg['paths']['output_dir']}/listing_out.csv"
    write_csv_with_labels(out_df, out, labels)
    logger.info("Listing 优化完成，%d 条，输出 %s", len(out_df), out)
    return out_df