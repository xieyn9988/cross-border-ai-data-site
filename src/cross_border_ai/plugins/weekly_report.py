"""业务周报：本周 vs 上周的核心指标环比。"""
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd

from ..io_utils import (
    parse_datetime_safe,
    read_csv_any_encoding,
    write_csv_with_labels,
)
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("weekly_report")
def weekly_report(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    logger = setup_logger("weekly_report", cfg["paths"]["log_dir"])

    input_files: List[str] = params.get("input_files") or []
    if not input_files:
        single = params.get("input_path") or f"{cfg['paths']['data_dir']}/order_sample.csv"
        input_files = [single]

    frames = []
    for path in input_files:
        df = read_csv_any_encoding(path).dropna(how="all").reset_index(drop=True)
        rename_map = {a: b for b, a in mapping.items() if a}
        df = df.rename(columns=rename_map)
        if "pay_time" in df.columns:
            df["pay_time"] = parse_datetime_safe(df["pay_time"])
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["pay_time", "amount"])

    # 时间边界
    now = datetime.now()
    this_week_start = now - timedelta(days=7)
    last_week_start = now - timedelta(days=14)

    this_week = df[df["pay_time"] >= this_week_start]
    last_week = df[(df["pay_time"] >= last_week_start) & (df["pay_time"] < this_week_start)]

    def _metrics(sub: pd.DataFrame) -> Dict:
        if sub.empty:
            return {"订单数": 0, "成交额": 0, "客单价": 0, "退款率": 0}
        m = {
            "订单数": int(sub["order_id"].nunique()),
            "成交额": round(sub["amount"].sum(), 2),
            "客单价": round(sub["amount"].mean(), 2),
        }
        if "refund_status" in sub.columns:
            is_refund = sub["refund_status"].astype(str).str.contains(
                "退款|退货|Refund|Return", na=False, regex=True
            )
            m["退款率"] = round(is_refund.mean(), 4)
        else:
            m["退款率"] = 0
        return m

    this_m = _metrics(this_week)
    last_m = _metrics(last_week)

    def _trend(cur, prev):
        if prev == 0:
            return "—"
        pct = (cur - prev) / prev
        if pct > 0.1:
            return "📈 上升"
        if pct < -0.1:
            return "📉 下降"
        return "➡️ 持平"

    def _change(cur, prev):
        if prev == 0:
            return None
        return round((cur - prev) / prev, 4)

    rows = []
    for key in ["订单数", "成交额", "客单价", "退款率"]:
        rows.append({
            "指标": key,
            "本周": this_m.get(key, 0),
            "上周": last_m.get(key, 0),
            "环比": _change(this_m.get(key, 0), last_m.get(key, 0)),
            "趋势": _trend(this_m.get(key, 0), last_m.get(key, 0)),
        })

    report = pd.DataFrame(rows)

    out_dir = cfg["paths"]["output_dir"]
    write_csv_with_labels(report, f"{out_dir}/weekly_report.csv", labels)
    report.attrs["output_files"] = [("weekly_report.csv", "业务周报")]

    logger.info("周报生成完成：%d 个指标", len(report))
    return report