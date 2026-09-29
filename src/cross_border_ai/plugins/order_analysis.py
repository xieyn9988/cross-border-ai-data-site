"""订单分析：输出 1 份汇总 + 6 份下钻报告。"""
from typing import Any, Dict, List

import pandas as pd

from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario

DELAY_THRESHOLD_DAYS = 7
DELAY_SHIP_HOURS = 48


@register_scenario("order_analysis")
def order_analysis(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    logger = setup_logger("order_analysis", cfg["paths"]["log_dir"])

    input_files: List[str] = params.get("input_files") or []
    if not input_files:
        single = params.get("input_path") or f"{cfg['paths']['data_dir']}/order_sample.csv"
        input_files = [single]

    # ---- 读取合并 ----
    frames = []
    for path in input_files:
        df_raw = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)
        rename_map = {actual: biz for biz, actual in mapping.items() if actual}
        df = df_raw.rename(columns=rename_map)
        if "order_id" in df.columns:
            df = df[df["order_id"].astype(str) != "合计"].copy()
        for col in ["amount", "quantity", "receivable", "refund_amount",
                    "cost", "platform_fee", "fba_fee", "ad_cost"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in ["pay_time", "ship_time", "deliver_time"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        df = df.dropna(subset=["order_id", "amount"])
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    out_dir = cfg["paths"]["output_dir"]
    output_files: List = []

    # ========================================================
    # 汇总报告
    # ========================================================
    summary = {
        "总订单数": int(df["order_id"].nunique()),
        "总成交额": round(df["amount"].sum(), 2),
        "平均客单价": round(df["amount"].mean(), 2),
    }
    if "refund_status" in df.columns:
        df["_is_refund"] = df["refund_status"].astype(str).str.contains(
            "退款|退货|售后|Refund|Return", na=False, regex=True
        )
        summary["退款率"] = round(df["_is_refund"].mean(), 4)

    if all(c in df.columns for c in ["pay_time", "ship_time"]):
        df["_ship_hours"] = (df["ship_time"] - df["pay_time"]).dt.total_seconds() / 3600
        summary["平均发货时长_小时"] = round(df["_ship_hours"].mean(), 1)
        if "deliver_time" in df.columns:
            df["_deliver_days"] = (df["deliver_time"] - df["ship_time"]).dt.total_seconds() / 86400
            summary["平均妥投天数"] = round(df["_deliver_days"].mean(), 1)

    summary_df = pd.DataFrame([summary])
    write_csv_with_labels(summary_df, f"{out_dir}/order_summary.csv", labels)
    output_files.append(("order_summary.csv", "订单汇总"))

    # ========================================================
    # 下钻报告 1：店铺订单汇总
    # ========================================================
    shop_stat = (
        df.groupby("shop")
        .agg(订单数=("order_id", "nunique"),
             总成交额=("amount", "sum"),
             平均客单价=("amount", "mean"))
        .reset_index().sort_values("总成交额", ascending=False)
    )
    write_csv_with_labels(shop_stat, f"{out_dir}/order_shop_stat.csv", labels)
    output_files.append(("order_shop_stat.csv", "店铺订单汇总"))

    # ========================================================
    # 下钻报告 2：国家/站点汇总
    # ========================================================
    if "country" in df.columns and df["country"].notna().any():
        country_stat = (
            df.groupby("country")
            .agg(订单数=("order_id", "nunique"),
                 总成交额=("amount", "sum"),
                 平均客单价=("amount", "mean"))
            .reset_index().sort_values("总成交额", ascending=False)
        )
        write_csv_with_labels(country_stat, f"{out_dir}/order_country_stat.csv", labels)
        output_files.append(("order_country_stat.csv", "国家/站点汇总"))

    # ========================================================
    # 下钻报告 3：平台/模式汇总
    # ========================================================
    group_cols = ["platform"]
    if "mode" in df.columns:
        group_cols.append("mode")
    platform_stat = (
        df.groupby(group_cols)
        .agg(订单数=("order_id", "nunique"),
             总成交额=("amount", "sum"))
        .reset_index().sort_values("总成交额", ascending=False)
    )
    write_csv_with_labels(platform_stat, f"{out_dir}/order_platform_stat.csv", labels)
    output_files.append(("order_platform_stat.csv", "平台/模式汇总"))

    # ========================================================
    # 下钻报告 4：退款分析
    # ========================================================
    if "refund_status" in df.columns:
        refund_stat = (
            df.groupby(group_cols)
            .agg(订单总数=("order_id", "nunique"),
                 退款订单数=("order_id", lambda s: s[df.loc[s.index, "_is_refund"]].nunique()))
            .reset_index()
        )
        refund_stat["退款率"] = (refund_stat["退款订单数"] / refund_stat["订单总数"]).round(4)
        refund_stat = refund_stat.sort_values("退款率", ascending=False)
        write_csv_with_labels(refund_stat, f"{out_dir}/order_refund_stat.csv", labels)
        output_files.append(("order_refund_stat.csv", "退款/退货分析"))

    # ========================================================
    # 下钻报告 5：履约时效
    # ========================================================
    if "_ship_hours" in df.columns:
        fulfill_cols = ["platform"]
        if "logistics_company" in df.columns:
            fulfill_cols.append("logistics_company")
        fulfill_stat = (
            df.groupby(fulfill_cols)
            .agg(订单数=("order_id", "nunique"),
                 平均发货时长_小时=("_ship_hours", "mean"))
            .reset_index()
        )
        fulfill_stat["平均发货时长_小时"] = fulfill_stat["平均发货时长_小时"].round(1)
        write_csv_with_labels(fulfill_stat, f"{out_dir}/order_fulfillment_stat.csv", labels)
        output_files.append(("order_fulfillment_stat.csv", "履约时效分析"))

    # ========================================================
    # 下钻报告 6：SKU 利润
    # ========================================================
    if "cost" in df.columns and "product_name" in df.columns:
        df["_cost"] = df["cost"] * df["quantity"]
        df["_fee"] = 0
        for fee_col in ["platform_fee", "fba_fee", "ad_cost"]:
            if fee_col in df.columns:
                df["_fee"] += df[fee_col].fillna(0)
        df["_profit"] = df["amount"] - df["_cost"] - df["_fee"]

        group_key = "sku_code" if "sku_code" in df.columns else "product_name"
        sku_profit = (
            df.groupby(group_key)
            .agg(销量=("quantity", "sum"),
                 总成交额=("amount", "sum"),
                 总成本=("_cost", "sum"),
                 总费用=("_fee", "sum"),
                 毛利=("_profit", "sum"))
            .reset_index().sort_values("毛利")
        )
        sku_profit["毛利率"] = (sku_profit["毛利"] / sku_profit["总成交额"]).round(4)
        write_csv_with_labels(sku_profit, f"{out_dir}/order_sku_profit.csv", labels)
        output_files.append(("order_sku_profit.csv", "SKU 利润分析"))

    df.attrs["output_files"] = output_files
    logger.info("订单分析完成：%d 条订单，%d 份报告", len(df), len(output_files))
    return df