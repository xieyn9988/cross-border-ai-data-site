"""素材批量处理：业务字段驱动。"""
from typing import Any, Dict

import pandas as pd

from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("material_process")
def batch_material_process(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    platform = params.get("platform", cfg["defaults"].get("platform", "amazon"))
    tpl = cfg["prompt_templates"]["material"]
    logger = setup_logger("material_process", cfg["paths"]["log_dir"])

    path = params.get("input_path") or f"{cfg['paths']['data_dir']}/material.csv"
    df_raw = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)

    rename_map = {actual: biz for biz, actual in mapping.items() if actual}
    df = df_raw.rename(columns=rename_map)

    if "material_id" not in df.columns or "raw_text" not in df.columns:
        raise ValueError("缺少必需业务字段：material_id / raw_text")

    df = df.copy()
    df["is_abnormal"] = df["material_id"].isna()
    df["ai_prompt"] = df.apply(
        lambda r: "数据异常，跳过"
        if r["is_abnormal"]
        else tpl.format(raw_text=r["raw_text"], platform=platform),
        axis=1,
    )

    keep_cols = ["material_id", "raw_text", "ai_prompt"]
    if "category" in df.columns:
        keep_cols.insert(1, "category")

    out_df = df[keep_cols]
    out = f"{cfg['paths']['output_dir']}/material_out.csv"
    write_csv_with_labels(out_df, out, labels)
    logger.info("素材处理完成，%d 条，输出 %s", len(out_df), out)
    return out_df