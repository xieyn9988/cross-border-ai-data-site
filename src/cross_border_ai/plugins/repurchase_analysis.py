"""复购分析：识别多次下单的客户。"""
from typing import Any, Dict, List

import pandas as pd

from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("repurchase_analysis")
def repurchase_analysis(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    logger = setup_logger("repurchase_analysis", cfg["paths"]["log_dir"])

    input_files: List[str] = params.get("input_files") or []
    if not input_files:
        single = params.get("input_path") or f"{cfg['paths']['data_dir']}/order_sample.csv"
        input_files = [single]

    frames = []
    for path in input_files:
        df = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)
        rename_map = {a: b for b, a in mapping.items() if a}
        df = df.rename(columns=rename_map)
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)

    if "customer_id" not in df.columns:
        raise ValueError("缺少 customer_id 字段，无法进行复购分析")

    # 按客户汇总
    customer_stat = (
        df.groupby("customer_id")
        .agg(
            订单数=("order_id", "nunique"),
            总消费额=("amount", "sum"),
        )
        .reset_index().sort_values("订单数", ascending=False)
    )
    customer_stat["总消费额"] = customer_stat["总消费额"].round(2)
    customer_stat["客户类型"] = customer_stat["订单数"].apply(
        lambda n: "高频复购" if n >= 5 else ("复购客户" if n >= 2 else "新客户")
    )

    out_dir = cfg["paths"]["output_dir"]
    write_csv_with_labels(customer_stat, f"{out_dir}/repurchase_analysis.csv", labels)

    # 汇总
    summary = (
        customer_stat.groupby("客户类型")
        .agg(客户数=("customer_id", "nunique"), 总消费额=("总消费额", "sum"))
        .reset_index()
    )
    write_csv_with_labels(summary, f"{out_dir}/repurchase_summary.csv", labels)

    customer_stat.attrs["output_files"] = [
        ("repurchase_analysis.csv", "复购明细"),
        ("repurchase_summary.csv", "复购汇总"),
    ]

    logger.info("复购分析完成：%d 个客户", len(customer_stat))
    return customer_stat