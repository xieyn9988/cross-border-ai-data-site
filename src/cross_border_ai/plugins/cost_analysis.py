"""成本分析：成本结构与毛利占比。"""
from typing import Any, Dict, List

import pandas as pd

from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("cost_analysis")
def cost_analysis(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    logger = setup_logger("cost_analysis", cfg["paths"]["log_dir"])

    input_files: List[str] = params.get("input_files") or []
    if not input_files:
        single = params.get("input_path") or f"{cfg['paths']['data_dir']}/order_sample.csv"
        input_files = [single]

    frames = []
    for path in input_files:
        df = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)
        rename_map = {a: b for b, a in mapping.items() if a}
        df = df.rename(columns=rename_map)
        for col in ["amount", "cost", "quantity", "platform_fee", "fba_fee", "ad_cost"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)

    # 采购成本 = 成本价 × 数量
    if "cost" in df.columns and "quantity" in df.columns:
        df["_cost_total"] = (df["cost"] * df["quantity"].fillna(1)).fillna(0)
    else:
        df["_cost_total"] = 0

    # 费用 = 平台佣金 + FBA 费 + 广告费
    df["_fee_total"] = 0
    for col in ["platform_fee", "fba_fee", "ad_cost"]:
        if col in df.columns:
            df["_fee_total"] += df[col].fillna(0)

    # 毛利
    df["_profit"] = df["amount"].fillna(0) - df["_cost_total"] - df["_fee_total"]

    out_dir = cfg["paths"]["output_dir"]
    output_files: List = []

    # 汇总
    total_amount = df["amount"].sum()
    total_cost = df["_cost_total"].sum()
    total_fee = df["_fee_total"].sum()
    total_profit = df["_profit"].sum()

    summary = pd.DataFrame([{
        "总成交额": round(total_amount, 2),
        "总成本": round(total_cost, 2),
        "总费用": round(total_fee, 2),
        "毛利": round(total_profit, 2),
        "毛利率": round(total_profit / total_amount, 4) if total_amount else 0,
        "成本占比": round(total_cost / total_amount, 4) if total_amount else 0,
        "费用占比": round(total_fee / total_amount, 4) if total_amount else 0,
    }])
    write_csv_with_labels(summary, f"{out_dir}/cost_summary.csv", labels)
    output_files.append(("cost_summary.csv", "成本汇总"))

    # 按平台
    if "platform" in df.columns:
        platform_cost = (
            df.groupby("platform")
            .agg(
                总成交额=("amount", "sum"),
                总成本=("_cost_total", "sum"),
                总费用=("_fee_total", "sum"),
                毛利=("_profit", "sum"),
            )
            .reset_index().sort_values("毛利")
        )
        platform_cost["毛利率"] = (platform_cost["毛利"] / platform_cost["总成交额"]).round(4)
        for c in ["总成交额", "总成本", "总费用", "毛利"]:
            platform_cost[c] = platform_cost[c].round(2)
        write_csv_with_labels(platform_cost, f"{out_dir}/cost_by_platform.csv", labels)
        output_files.append(("cost_by_platform.csv", "平台成本汇总"))

    # 按 SKU
    if "sku_code" in df.columns or "product_name" in df.columns:
        group_key = "sku_code" if "sku_code" in df.columns else "product_name"
        sku_cost = (
            df.groupby(group_key)
            .agg(
                总成交额=("amount", "sum"),
                总成本=("_cost_total", "sum"),
                总费用=("_fee_total", "sum"),
                毛利=("_profit", "sum"),
            )
            .reset_index().sort_values("毛利")
        )
        sku_cost["毛利率"] = (sku_cost["毛利"] / sku_cost["总成交额"]).round(4)
        for c in ["总成交额", "总成本", "总费用", "毛利"]:
            sku_cost[c] = sku_cost[c].round(2)
        write_csv_with_labels(sku_cost, f"{out_dir}/cost_by_sku.csv", labels)
        output_files.append(("cost_by_sku.csv", "SKU 成本汇总"))

    # ★ 关键指标卡片
    total_amount = df["amount"].sum() if "amount" in df.columns else 0
    total_profit = df["_profit"].sum() if "_profit" in df.columns else 0
    df.attrs["summary"] = {
        "总成交额": f"¥{total_amount:,.2f}",
        "毛利": f"¥{total_profit:,.2f}",
        "毛利率": f"{(total_profit / total_amount * 100):.1f}%" if total_amount else "—",
    }

    df.attrs["output_files"] = output_files
    logger.info("成本分析完成：...")
    return df