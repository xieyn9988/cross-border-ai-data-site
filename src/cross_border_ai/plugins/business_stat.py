"""业务数据统计：按区域聚合销售额、订单数、曝光量。

兼容 amount / sales 两种命名：
  - 数据里叫"成交价"、"amount"、"销售额"、"sales" 都能识别
  - 内部统一用 amount 列做聚合
"""
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

    # ---- 读文件 ----
    input_files = params.get("input_files") or []
    if not input_files:
        single = params.get("input_path") or f"{cfg['paths']['data_dir']}/shop_data_店铺数据.csv"
        input_files = [single]

    frames = []
    for path in input_files:
        df = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)
        rename_map = {actual: biz for biz, actual in mapping.items() if actual}
        df = df.rename(columns=rename_map)
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)

    # ========================================================
    # ★ 关键：兼容 amount / sales 两种命名
    # ========================================================
    # 如果只有 sales，没有 amount → 用 sales 补一个 amount
    if "amount" not in df.columns and "sales" in df.columns:
        df["amount"] = df["sales"]
    # 如果只有 amount，没有 sales → 用 amount 补一个 sales
    if "sales" not in df.columns and "amount" in df.columns:
        df["sales"] = df["amount"]

    # ---- 数值列清洗 ----
    for col in ["amount", "sales", "order_num", "exposure", "quantity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ---- 必需字段校验 ----
    if "region" not in df.columns:
        raise BusinessLogicError("缺少必需业务字段：region")
    if "amount" not in df.columns:
        raise BusinessLogicError("缺少必需业务字段：amount / sales")

    df = df.dropna(subset=["region", "amount"])
    if df.empty:
        raise BusinessLogicError("清洗后无有效数据")

    # ========================================================
    # 聚合
    # ========================================================
    agg_map = {
        "总销售额": ("amount", "sum"),
        "订单数": ("order_num", "sum") if "order_num" in df.columns else ("amount", "count"),
    }
    if "exposure" in df.columns:
        agg_map["总曝光量"] = ("exposure", "sum")

    stat = df.groupby("region").agg(**agg_map).reset_index()

    # 平均客单价
    stat["平均客单价"] = safe_divide(stat["总销售额"], stat["订单数"], fill=0.0).round(2)

    # 转化率（有曝光量时）
    if "总曝光量" in stat.columns:
        stat["转化率"] = safe_divide(stat["订单数"], stat["总曝光量"], fill=0.0).round(4)

    stat["总销售额"] = stat["总销售额"].round(2)
    stat = stat.sort_values("总销售额", ascending=False)

    # ========================================================
    # 输出
    # ========================================================
    out = f"{cfg['paths']['output_dir']}/stat_result.csv"
    write_csv_with_labels(stat, out, labels)
    stat.attrs["output_files"] = [("stat_result.csv", "业务数据统计")]

    # ★ 关键指标卡片
    stat.attrs["summary"] = {
        "区域数": len(stat),
        "总销售额": f"¥{stat['总销售额'].sum():,.2f}" if "总销售额" in stat.columns else "—",
        "总订单数": int(stat["订单数"].sum()) if "订单数" in stat.columns else "—",
    }

    logger.info("业务统计完成：%d 个区域，输出 %s", len(stat), out)
    return stat