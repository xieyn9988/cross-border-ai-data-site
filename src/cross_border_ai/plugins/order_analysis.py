"""订单分析：输出 1 份汇总 + 最多 10 份下钻报告。

输出（按数据可用性动态生成）：
  1.  order_summary.csv              订单汇总
  2.  order_shop_stat.csv            店铺订单汇总
  3.  order_status_stat.csv          订单状态汇总
  4.  order_country_stat.csv         国家/站点汇总
  5.  order_state_stat.csv           州/省汇总
  6.  order_region_stat.csv          区域汇总（国内）
  7.  order_platform_stat.csv        平台/模式汇总
  8.  order_refund_stat.csv          退款/退货分析
  9.  order_fulfillment_stat.csv     履约时效分析
  10. order_delay_list.csv           延迟订单清单
  11. order_sku_profit.csv           SKU 利润分析
"""
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
        valid_hours = df["_ship_hours"].dropna()
        if len(valid_hours) > 0:
            summary["平均发货时长_小时"] = round(valid_hours.mean(), 1)
        if "deliver_time" in df.columns:
            df["_deliver_days"] = (df["deliver_time"] - df["ship_time"]).dt.total_seconds() / 86400
            valid_days = df["_deliver_days"].dropna()
            if len(valid_days) > 0:
                summary["平均妥投天数"] = round(valid_days.mean(), 1)

    summary_df = pd.DataFrame([summary])
    write_csv_with_labels(summary_df, f"{out_dir}/order_summary.csv", labels)
    output_files.append(("order_summary.csv", "订单汇总"))

    # ========================================================
    # 报告 1：店铺订单汇总
    # ========================================================
    if "shop" in df.columns:
        shop_stat = (
            df.groupby("shop")
            .agg(订单数=("order_id", "nunique"),
                 总成交额=("amount", "sum"),
                 平均客单价=("amount", "mean"),
                 总实发数量=("quantity", "sum"))
            .reset_index().sort_values("总成交额", ascending=False)
        )
        shop_stat["总成交额"] = shop_stat["总成交额"].round(2)
        shop_stat["平均客单价"] = shop_stat["平均客单价"].round(2)
        write_csv_with_labels(shop_stat, f"{out_dir}/order_shop_stat.csv", labels)
        output_files.append(("order_shop_stat.csv", "店铺订单汇总"))

    # ========================================================
    # 报告 2：订单状态汇总 ★★★ 新增
    # ========================================================
    if "status" in df.columns:
        amount_col = "receivable" if "receivable" in df.columns else "amount"
        status_stat = (
            df.groupby("status")
            .agg(订单数=("order_id", "nunique"),
                 涉及金额=(amount_col, "sum"))
            .reset_index().sort_values("订单数", ascending=False)
        )
        status_stat["涉及金额"] = status_stat["涉及金额"].round(2)
        write_csv_with_labels(status_stat, f"{out_dir}/order_status_stat.csv", labels)
        output_files.append(("order_status_stat.csv", "订单状态汇总"))

    # ========================================================
    # 报告 3：国家/站点汇总
    # ========================================================
    if "country" in df.columns and df["country"].notna().any():
        country_stat = (
            df.groupby("country")
            .agg(订单数=("order_id", "nunique"),
                 总成交额=("amount", "sum"),
                 平均客单价=("amount", "mean"))
            .reset_index().sort_values("总成交额", ascending=False)
        )
        country_stat["总成交额"] = country_stat["总成交额"].round(2)
        country_stat["平均客单价"] = country_stat["平均客单价"].round(2)
        write_csv_with_labels(country_stat, f"{out_dir}/order_country_stat.csv", labels)
        output_files.append(("order_country_stat.csv", "国家/站点汇总"))

    # ========================================================
    # 报告 4：州/省汇总 ★★★ 新增
    # ========================================================
    if "state" in df.columns and df["state"].notna().any():
        state_group = ["state"]
        if "country" in df.columns and df["country"].notna().any():
            state_group = ["country", "state"]
        state_stat = (
            df.groupby(state_group)
            .agg(订单数=("order_id", "nunique"),
                 总成交额=("amount", "sum"))
            .reset_index().sort_values("总成交额", ascending=False)
        )
        state_stat["总成交额"] = state_stat["总成交额"].round(2)
        write_csv_with_labels(state_stat, f"{out_dir}/order_state_stat.csv", labels)
        output_files.append(("order_state_stat.csv", "州/省汇总"))

    # ========================================================
    # 报告 5：区域汇总（国内）★★★ 新增
    # ========================================================
    if "region" in df.columns and df["region"].notna().any():
        region_stat = (
            df.groupby("region")
            .agg(订单数=("order_id", "nunique"),
                 总成交额=("amount", "sum"))
            .reset_index().sort_values("总成交额", ascending=False)
        )
        region_stat["总成交额"] = region_stat["总成交额"].round(2)
        write_csv_with_labels(region_stat, f"{out_dir}/order_region_stat.csv", labels)
        output_files.append(("order_region_stat.csv", "区域汇总(国内)"))

    # ========================================================
    # 报告 6：平台/模式汇总
    # ========================================================
    group_cols = ["platform"] if "platform" in df.columns else []
    if "mode" in df.columns:
        group_cols.append("mode")
    if group_cols:
        platform_stat = (
            df.groupby(group_cols)
            .agg(订单数=("order_id", "nunique"),
                 总成交额=("amount", "sum"),
                 平均客单价=("amount", "mean"))
            .reset_index().sort_values("总成交额", ascending=False)
        )
        platform_stat["总成交额"] = platform_stat["总成交额"].round(2)
        platform_stat["平均客单价"] = platform_stat["平均客单价"].round(2)
        write_csv_with_labels(platform_stat, f"{out_dir}/order_platform_stat.csv", labels)
        output_files.append(("order_platform_stat.csv", "平台/模式汇总"))

    # ========================================================
    # 报告 7：退款/退货分析
    # ========================================================
    if "_is_refund" in df.columns and group_cols:
        refund_stat = (
            df.groupby(group_cols)
            .agg(订单总数=("order_id", "nunique"),
                 退款订单数=("order_id", lambda s: s[df.loc[s.index, "_is_refund"]].nunique()))
            .reset_index()
        )
        if "refund_amount" in df.columns:
            ra = df[df["_is_refund"]].groupby(group_cols)["refund_amount"].sum().reset_index()
            ra = ra.rename(columns={"refund_amount": "退款金额"})
            refund_stat = refund_stat.merge(ra, on=group_cols, how="left")
            refund_stat["退款金额"] = refund_stat["退款金额"].fillna(0).round(2)
        refund_stat["退款率"] = (refund_stat["退款订单数"] / refund_stat["订单总数"]).round(4)
        refund_stat = refund_stat.sort_values("退款率", ascending=False)
        write_csv_with_labels(refund_stat, f"{out_dir}/order_refund_stat.csv", labels)
        output_files.append(("order_refund_stat.csv", "退款/退货分析"))

    # ========================================================
    # 报告 8：履约时效分析
    # ========================================================
    if "_ship_hours" in df.columns:
        fulfill_cols = []
        if "platform" in df.columns:
            fulfill_cols.append("platform")
        if "logistics_company" in df.columns:
            fulfill_cols.append("logistics_company")
        if not fulfill_cols and "status" in df.columns:
            fulfill_cols = ["status"]

        if fulfill_cols:
            agg_map = {
                "订单数": ("order_id", "nunique"),
                "平均发货时长_小时": ("_ship_hours", "mean"),
            }
            if "_deliver_days" in df.columns:
                agg_map["平均妥投天数"] = ("_deliver_days", "mean")
            fulfill_stat = df.groupby(fulfill_cols).agg(**agg_map).reset_index()
            fulfill_stat["平均发货时长_小时"] = fulfill_stat["平均发货时长_小时"].round(1)
            if "平均妥投天数" in fulfill_stat.columns:
                fulfill_stat["平均妥投天数"] = fulfill_stat["平均妥投天数"].round(1)
            write_csv_with_labels(fulfill_stat, f"{out_dir}/order_fulfillment_stat.csv", labels)
            output_files.append(("order_fulfillment_stat.csv", "履约时效分析"))

    # ========================================================
    # 报告 9：延迟订单清单 ★★★ 新增
    # ========================================================
    if "_ship_hours" in df.columns:
        delay_mask = pd.Series(False, index=df.index)
        delay_mask = delay_mask | (df["_ship_hours"] > DELAY_SHIP_HOURS).fillna(False)
        if "_deliver_days" in df.columns:
            delay_mask = delay_mask | (df["_deliver_days"] > DELAY_THRESHOLD_DAYS).fillna(False)
        if "status" in df.columns and "pay_time" in df.columns and "ship_time" in df.columns:
            pending = df["status"].astype(str).str.contains(
                "待发货|待客审|待处理|Pending", na=False, regex=True
            )
            unpaid_delay = pending & df["pay_time"].notna() & df["ship_time"].isna()
            delay_mask = delay_mask | unpaid_delay

        delay_list = df[delay_mask].copy()
        if not delay_list.empty:
            cols = [c for c in [
                "order_id", "platform", "mode", "shop", "status",
                "country", "state", "product_name", "amount",
                "pay_time", "ship_time",
                "_ship_hours", "_deliver_days", "logistics_company",
            ] if c in delay_list.columns]
            delay_list = delay_list[cols].sort_values("_ship_hours", ascending=False)
            write_csv_with_labels(delay_list, f"{out_dir}/order_delay_list.csv", labels)
            output_files.append(("order_delay_list.csv", "延迟订单清单"))

    # ========================================================
    # 报告 10：SKU 利润分析
    # ========================================================
    if "cost" in df.columns and "product_name" in df.columns:
        df["_cost"] = df["cost"] * df["quantity"].fillna(1)
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
        for c in ["总成交额", "总成本", "总费用", "毛利"]:
            sku_profit[c] = sku_profit[c].round(2)
        write_csv_with_labels(sku_profit, f"{out_dir}/order_sku_profit.csv", labels)
        output_files.append(("order_sku_profit.csv", "SKU 利润分析"))

    df.attrs["output_files"] = output_files
    logger.info("订单分析完成：%d 条订单，%d 份报告", len(df), len(output_files))
    return df