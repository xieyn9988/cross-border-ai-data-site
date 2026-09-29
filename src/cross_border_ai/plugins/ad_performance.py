"""广告投放效果分析：业务字段驱动。"""
from typing import Any, Dict

import pandas as pd

from ..cleaning import safe_divide
from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("ad_performance")
def ad_performance(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    logger = setup_logger("ad_performance", cfg["paths"]["log_dir"])

    # 优先读上传文件；命令行运行时回退到 data/
    path = params.get("input_path") or f"{cfg['paths']['data_dir']}/ad_performance.csv"
    df_raw = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)

    rename_map = {actual: biz for biz, actual in mapping.items() if actual}
    df = df_raw.rename(columns=rename_map)

    required = {"campaign", "spend", "sales", "clicks", "impressions"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"缺少必需业务字段：{sorted(missing)}")

    df = df.copy()
    for col in ["spend", "sales", "clicks", "impressions"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["roi"] = safe_divide(df["sales"], df["spend"]).round(4)
    df["acos"] = safe_divide(df["spend"], df["sales"]).round(4)
    df["ctr"] = safe_divide(df["clicks"], df["impressions"]).round(4)

    out = f"{cfg['paths']['output_dir']}/ad_performance.csv"
    write_csv_with_labels(df, out, labels)
    logger.info("广告效果分析完成，%d 条，输出 %s", len(df), out)
    return df