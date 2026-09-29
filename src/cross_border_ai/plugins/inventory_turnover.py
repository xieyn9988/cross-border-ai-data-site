"""库存周转分析：ITO（库存周转率）和 DOS（库存天数）。"""
from typing import Any, Dict, List

import pandas as pd

from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("inventory_turnover")
def inventory_turnover(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    logger = setup_logger("inventory_turnover", cfg["paths"]["log_dir"])

    input_files: List[str] = params.get("input_files") or []
    if not input_files:
        single = params.get("input_path") or f"{cfg['paths']['data_dir']}/inventory.csv"
        input_files = [single]

    frames = []
    for path in input_files:
        df = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)
        rename_map = {a: b for b, a in mapping.items() if a}
        df = df.rename(columns=rename_map)
        required = {"platform", "shop", "sku_code", "stock", "daily_sales"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"缺少必需字段：{sorted(missing)}")
        for col in ["stock", "daily_sales", "cost"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df = df[df["daily_sales"] > 0].copy()

    # 库存天数 = 库存 / 日均销量
    df["库存天数"] = (df["stock"] / df["daily_sales"]).round(1)
    # 周转率 = 30 天销量 / 平均库存（这里近似：30 / 库存天数）
    df["周转率"] = (30 / df["库存天数"]).round(2)

    # 分级
    def _level(days: float) -> str:
        if pd.isna(days):
            return "数据异常"
        if days <= 30:
            return "周转快"
        if days <= 90:
            return "周转正常"
        if days <= 180:
            return "周转慢"
        return "严重滞销"

    df["周转等级"] = df["库存天数"].apply(_level)

    if "cost" in df.columns:
        df["积压成本"] = (df["stock"] * df["cost"]).round(2)

    out_dir = cfg["paths"]["output_dir"]
    output_files: List = []

    # 明细
    df_detail = df.sort_values("库存天数", ascending=False)
    write_csv_with_labels(df_detail, f"{out_dir}/inventory_turnover.csv", labels)
    output_files.append(("inventory_turnover.csv", "库存周转明细"))

    # 汇总
    summary = (
        df.groupby("周转等级")
        .agg(SKU数量=("sku_code", "nunique"), 总库存=("stock", "sum"))
        .reset_index()
    )
    write_csv_with_labels(summary, f"{out_dir}/inventory_turnover_summary.csv", labels)
    output_files.append(("inventory_turnover_summary.csv", "库存周转汇总"))

    df.attrs["output_files"] = output_files
    logger.info("库存周转分析完成：%d 条 SKU", len(df))
    return df