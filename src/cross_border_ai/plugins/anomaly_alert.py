"""异常告警：识别退款率突增、订单骤降、库存骤降。"""
from typing import Any, Dict, List

import pandas as pd

from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("anomaly_alert")
def anomaly_alert(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    logger = setup_logger("anomaly_alert", cfg["paths"]["log_dir"])

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
    alerts = []

    # ---- 告警 1：退款率 > 8% ----
    if "refund_status" in df.columns and "platform" in df.columns:
        df["_is_refund"] = df["refund_status"].astype(str).str.contains(
            "退款|退货|售后|Refund|Return", na=False, regex=True
        )
        refund_rate = df.groupby("platform")["_is_refund"].mean().reset_index()
        for _, row in refund_rate.iterrows():
            rate = row["_is_refund"]
            if rate > 0.08:
                level = "🔴 高危" if rate > 0.15 else "🟡 警告"
                alerts.append({
                    "告警类型": "高退款率",
                    "严重程度": level,
                    "对象": row["platform"],
                    "当前值": f"{rate*100:.1f}%",
                    "历史值": "5.0%",
                    "变化率": round(rate - 0.05, 4),
                    "建议": "检查商品质量或物流问题",
                })

    # ---- 告警 2：订单骤降（按平台成交额）----
    if "platform" in df.columns:
        platform_amount = df.groupby("platform")["amount"].sum().reset_index()
        avg = platform_amount["amount"].mean()
        for _, row in platform_amount.iterrows():
            if row["amount"] < avg * 0.5:
                alerts.append({
                    "告警类型": "订单骤降",
                    "严重程度": "🟡 警告",
                    "对象": row["platform"],
                    "当前值": f"{row['amount']:.2f}",
                    "历史值": f"{avg:.2f}",
                    "变化率": round((row["amount"] - avg) / avg, 4),
                    "建议": "检查广告投放或库存是否断货",
                })

    # ---- 告警 3：缺货风险 ----
    if "stock" in df.columns and "sku_code" in df.columns and "daily_sales" in df.columns:
        df["stock"] = pd.to_numeric(df["stock"], errors="coerce")
        df["daily_sales"] = pd.to_numeric(df["daily_sales"], errors="coerce")
        risky = df[(df["daily_sales"] > 0) & (df["stock"] / df["daily_sales"] <= 2)]
        for _, row in risky.iterrows():
            alerts.append({
                "告警类型": "缺货风险",
                "严重程度": "🔴 高危",
                "对象": f"{row.get('platform','')} / {row['sku_code']}",
                "当前值": f"{row['stock']}",
                "历史值": "—",
                "变化率": None,
                "建议": "立即补货",
            })

    if not alerts:
        alerts.append({
            "告警类型": "—", "严重程度": "—", "对象": "—",
            "当前值": "—", "历史值": "—", "变化率": None, "建议": "无异常",
        })

    alerts_df = pd.DataFrame(alerts)
    out_dir = cfg["paths"]["output_dir"]
    write_csv_with_labels(alerts_df, f"{out_dir}/anomaly_alert.csv", labels)
    alerts_df.attrs["output_files"] = [("anomaly_alert.csv", "异常告警")]

    logger.info("异常告警完成：%d 条告警", len(alerts))
    return alerts_df