"""库存预警：输出 1 份汇总 + 3 份下钻报告。"""
from typing import Any, Dict, List

import pandas as pd

from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("inventory_alert")
def inventory_alert(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    threshold_fixed = int(params.get("threshold", 10))
    logger = setup_logger("inventory_alert", cfg["paths"]["log_dir"])

    input_files: List[str] = params.get("input_files") or []
    if not input_files:
        single = params.get("input_path") or f"{cfg['paths']['data_dir']}/inventory.csv"
        input_files = [single]

    frames = []
    for path in input_files:
        df_raw = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)
        rename_map = {actual: biz for biz, actual in mapping.items() if actual}
        df = df_raw.rename(columns=rename_map)
        required = {"platform", "shop", "sku_code", "stock", "safety_stock"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"库存表缺少必需字段：{sorted(missing)}")
        for col in ["stock", "safety_stock", "in_transit", "locked_stock",
                    "daily_sales", "sales_30d", "cost",
                    "replenish_days", "safety_days"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    out_dir = cfg["paths"]["output_dir"]
    output_files: List = []

    # ========================================================
    # 动态阈值
    # ========================================================
    has_daily = "daily_sales" in df.columns
    has_rep = "replenish_days" in df.columns
    has_safe = "safety_days" in df.columns

    def _calc_threshold(row):
        daily = row.get("daily_sales") if has_daily else None
        rep = row.get("replenish_days") if has_rep else None
        safe = row.get("safety_days") if has_safe else None
        safety_stock = row.get("safety_stock", 0)
        if pd.isna(daily) or daily <= 0:
            return float(safety_stock) if pd.notna(safety_stock) else float(threshold_fixed)
        rep = rep if pd.notna(rep) and rep > 0 else 30
        safe = safe if pd.notna(safe) and safe >= 0 else 5
        return round(daily * (rep + safe) + (safety_stock or 0), 0)

    df["动态预警阈值"] = df.apply(_calc_threshold, axis=1)

    def _alert(row):
        stock = row.get("stock")
        if pd.isna(stock):
            return "数据异常"
        if stock < row["动态预警阈值"] * 0.3:
            return "紧急补货"
        if stock < row["动态预警阈值"]:
            return "低于安全库存"
        return "正常"

    df["预警状态"] = df.apply(_alert, axis=1)

    if has_daily:
        df["可售天数"] = (df["stock"] / df["daily_sales"]).round(1)
        df["可售天数"] = df["可售天数"].replace([float("inf"), -float("inf")], pd.NA)
        df["建议补货量"] = (
            df["daily_sales"] * ((df["replenish_days"] if has_rep else 30) +
                                 (df["safety_days"] if has_safe else 5))
            - df["stock"]
        ).clip(lower=0).round(0)

        def _action(row):
            days = row.get("可售天数")
            rep = row.get("replenish_days") if has_rep else 30
            safe = row.get("safety_days") if has_safe else 5
            if pd.isna(days):
                return "—"
            if days <= (rep or 30):
                return "立即补货，走空运"
            if days <= (rep or 30) + (safe or 5):
                return "尽快补货，走海运"
            return "—"

        df["行动建议"] = df.apply(_action, axis=1)
    else:
        df["行动建议"] = df["预警状态"].apply(
            lambda s: "提交备货单" if s != "正常" else "—"
        )

    # ========================================================
    # 汇总报告
    # ========================================================
    total_sku = df["sku_code"].nunique()
    urgent = df[df["预警状态"] == "紧急补货"]["sku_code"].nunique()
    warning = df[df["预警状态"] == "低于安全库存"]["sku_code"].nunique()

    summary = {
        "SKU总数": total_sku,
        "紧急补货SKU数": urgent,
        "低于安全库存SKU数": warning,
        "库存健康率": round(1 - (urgent + warning) / total_sku, 4) if total_sku else 0,
    }
    summary_df = pd.DataFrame([summary])
    write_csv_with_labels(summary_df, f"{out_dir}/inventory_summary.csv", labels)
    output_files.append(("inventory_summary.csv", "库存汇总"))

    # ========================================================
    # 下钻报告 1：库存预警明细
    # ========================================================
    order_map = {"紧急补货": 0, "低于安全库存": 1, "数据异常": 2, "正常": 3}
    df["_order"] = df["预警状态"].map(order_map).fillna(9)
    sort_cols = ["_order"]
    if "可售天数" in df.columns:
        sort_cols.append("可售天数")
    else:
        sort_cols.append("stock")
    df_detail = df.sort_values(sort_cols).drop(columns=["_order"])
    write_csv_with_labels(df_detail, f"{out_dir}/inventory_alert.csv", labels)
    output_files.append(("inventory_alert.csv", "库存预警明细"))

    # ========================================================
    # 下钻报告 2：平台/店铺汇总
    # ========================================================
    group_cols = ["platform"]
    if "mode" in df.columns:
        group_cols.append("mode")
    group_cols.append("shop")

    agg_map = {
        "SKU数量": ("sku_code", "nunique"),
        "总库存": ("stock", "sum"),
        "预警SKU数": ("预警状态", lambda s: (s != "正常").sum()),
    }
    shop_summary = (
        df.groupby(group_cols).agg(**agg_map).reset_index()
        .sort_values("预警SKU数", ascending=False)
    )
    shop_summary["预警率"] = (shop_summary["预警SKU数"] / shop_summary["SKU数量"]).round(4)
    write_csv_with_labels(shop_summary, f"{out_dir}/inventory_shop_summary.csv", labels)
    output_files.append(("inventory_shop_summary.csv", "平台/店铺汇总"))

    # ========================================================
    # 下钻报告 3：缺货风险 Top 20
    # ========================================================
    risk = df[df["预警状态"] != "正常"].copy()
    if not risk.empty:
        risk["_order"] = risk["预警状态"].map(order_map).fillna(9)
        if "可售天数" in risk.columns:
            risk = risk.sort_values(["_order", "可售天数"])
        else:
            risk = risk.sort_values(["_order", "stock"])
        risk = risk.drop(columns=["_order"]).head(20)
        write_csv_with_labels(risk, f"{out_dir}/inventory_risk_top20.csv", labels)
        output_files.append(("inventory_risk_top20.csv", "缺货风险 Top 20"))

    df.attrs["output_files"] = output_files
    logger.info("库存预警完成：%d 条 SKU，输出 %d 份报告", len(df), len(output_files))
    return df