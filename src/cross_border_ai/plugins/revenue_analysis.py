"""收入分析：按平台/国家/币种汇总收入，并折算人民币。"""
from typing import Any, Dict, List

import pandas as pd

from ..currency import get_converter
from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("revenue_analysis")
def revenue_analysis(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    logger = setup_logger("revenue_analysis", cfg["paths"]["log_dir"])

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
    df = df.dropna(subset=["amount"])

    # 币种折算
    converter = get_converter()
    if "currency" in df.columns:
        df["_amount_cny"] = df.apply(
            lambda r: converter.to_cny(r["amount"], r["currency"])
            if pd.notna(r.get("currency")) else None,
            axis=1,
        )
    else:
        df["_amount_cny"] = None

    out_dir = cfg["paths"]["output_dir"]
    output_files: List = []

    # 按平台
    if "platform" in df.columns:
        platform_stat = (
            df.groupby("platform")
            .agg(总订单数=("order_id", "nunique"), 总金额=("amount", "sum"))
            .reset_index().sort_values("总金额", ascending=False)
        )
        platform_stat["总金额"] = platform_stat["总金额"].round(2)
        if df["_amount_cny"].notna().any():
            cny = df.groupby("platform")["_amount_cny"].sum().reset_index()
            cny = cny.rename(columns={"_amount_cny": "折合人民币"})
            platform_stat = platform_stat.merge(cny, on="platform", how="left")
            platform_stat["折合人民币"] = platform_stat["折合人民币"].round(2)
        write_csv_with_labels(platform_stat, f"{out_dir}/revenue_by_platform.csv", labels)
        output_files.append(("revenue_by_platform.csv", "平台收入汇总"))

    # 按国家
    if "country" in df.columns and df["country"].notna().any():
        country_stat = (
            df.groupby("country")
            .agg(总订单数=("order_id", "nunique"), 总金额=("amount", "sum"))
            .reset_index().sort_values("总金额", ascending=False)
        )
        country_stat["总金额"] = country_stat["总金额"].round(2)
        write_csv_with_labels(country_stat, f"{out_dir}/revenue_by_country.csv", labels)
        output_files.append(("revenue_by_country.csv", "国家收入汇总"))

    # 按币种
    if "currency" in df.columns and df["currency"].notna().any():
        currency_stat = (
            df.groupby("currency")
            .agg(总订单数=("order_id", "nunique"), 原币金额=("amount", "sum"))
            .reset_index().sort_values("原币金额", ascending=False)
        )
        currency_stat["原币金额"] = currency_stat["原币金额"].round(2)
        write_csv_with_labels(currency_stat, f"{out_dir}/revenue_by_currency.csv", labels)
        output_files.append(("revenue_by_currency.csv", "币种收入汇总"))

    df.attrs["output_files"] = output_files
    logger.info("收入分析完成：%d 条记录", len(df))
    return df