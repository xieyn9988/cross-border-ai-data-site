"""运营驾驶舱：订单 + 库存交叉，输出今日必做清单。"""
from typing import Any, Dict, List

import pandas as pd

from ..exceptions import BusinessLogicError
from ..io_utils import read_csv_any_encoding, write_csv_with_labels
from ..logger import setup_logger
from ..scenario_registry import register_scenario


@register_scenario("business_dashboard")
def business_dashboard(
    cfg: Dict[str, Any], params: Dict[str, Any] | None = None
) -> pd.DataFrame:
    params = params or {}
    mapping = params.get("field_mapping", {})
    labels = params.get("field_labels", {})
    logger = setup_logger("business_dashboard", cfg["paths"]["log_dir"])

    input_files: List[str] = params.get("input_files") or []
    if len(input_files) < 2:
        raise BusinessLogicError(
            "运营驾驶舱需要 2 份数据才能运行：\n"
            "  1. 订单明细表（含订单编号、金额、付款时间）\n"
            "  2. 库存表（含库存SKU、当前库存、日均销量）\n"
            "请补充上传缺失的文件，再点击「开始处理」。"
        )

    # 简单策略：根据文件名判断哪个是订单、哪个是库存
    order_files = []
    inventory_files = []
    for p in input_files:
        name = p.lower()
        if "inventory" in name or "库存" in name:
            inventory_files.append(p)
        else:
            order_files.append(p)

    # 读订单
    order_frames = []
    for path in order_files:
        df = read_csv_any_encoding(path)
        rename_map = {a: b for b, a in mapping.items() if a}
        df = df.rename(columns=rename_map)
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        order_frames.append(df)
    orders = pd.concat(order_frames, ignore_index=True) if order_frames else pd.DataFrame()

    # 读库存
    inv_frames = []
    for path in inventory_files:
        df = read_csv_any_encoding(path)
        rename_map = {a: b for b, a in mapping.items() if a}
        df = df.rename(columns=rename_map)
        for col in ["stock", "safety_stock", "daily_sales", "replenish_days", "safety_days"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        inv_frames.append(df)
    inventory = pd.concat(inv_frames, ignore_index=True) if inv_frames else pd.DataFrame()

    actions = []

    # ========================================================
    # 分析 1：断货风险（库存 + 待发货订单）
    # ========================================================
    if not inventory.empty and "sku_code" in inventory.columns:
        for _, row in inventory.iterrows():
            stock = row.get("stock", 0)
            daily = row.get("daily_sales", 0)
            if pd.isna(daily) or daily <= 0:
                continue
            days_left = stock / daily if daily > 0 else 999
            if days_left <= 2:
                actions.append({
                    "优先级": "P0",
                    "类型": "断货风险",
                    "平台": row.get("platform", ""),
                    "SKU": row.get("sku_code", ""),
                    "问题": f"库存仅够 {days_left:.1f} 天",
                    "建议行动": f"立即补货 {int(daily * 7)} 件",
                    "截止时间": "今天",
                })

    # ========================================================
    # 分析 2：退款率异常
    # ========================================================
    if not orders.empty and "refund_status" in orders.columns and "platform" in orders.columns:
        orders["_is_refund"] = orders["refund_status"].astype(str).str.contains(
            "退款|退货|售后|Refund|Return", na=False, regex=True
        )
        refund_rate = orders.groupby("platform")["_is_refund"].mean().reset_index()
        for _, row in refund_rate.iterrows():
            if row["_is_refund"] > 0.05:
                actions.append({
                    "优先级": "P1",
                    "类型": "高退款率",
                    "平台": row["platform"],
                    "SKU": "全平台",
                    "问题": f"退款率 {row['_is_refund']*100:.1f}%",
                    "建议行动": "检查商品质量",
                    "截止时间": "本周",
                })

    # ========================================================
    # 分析 3：物流延迟
    # ========================================================
    if not orders.empty and "logistics_company" in orders.columns:
        if all(c in orders.columns for c in ["pay_time", "ship_time"]):
            orders["pay_time"] = pd.to_datetime(orders["pay_time"], errors="coerce")
            orders["ship_time"] = pd.to_datetime(orders["ship_time"], errors="coerce")
            orders["_ship_hours"] = (orders["ship_time"] - orders["pay_time"]).dt.total_seconds() / 3600
            logistics = orders.groupby("logistics_company")["_ship_hours"].mean().reset_index()
            for _, row in logistics.iterrows():
                if row["_ship_hours"] > 36:
                    actions.append({
                        "优先级": "P1",
                        "类型": "物流延迟",
                        "平台": "全平台",
                        "SKU": "—",
                        "问题": f"{row['logistics_company']} 平均发货 {row['_ship_hours']:.0f} 小时",
                        "建议行动": "考虑更换物流商",
                        "截止时间": "本周",
                    })

    # ========================================================
    # 分析 4：SKU 利润下滑
    # ========================================================
    if not orders.empty and "cost" in orders.columns:
        orders["cost"] = pd.to_numeric(orders["cost"], errors="coerce")
        orders["_cost_total"] = orders["cost"] * orders.get("quantity", 1)
        if "sku_code" in orders.columns:
            sku_profit = orders.groupby("sku_code").agg(
                成交额=("amount", "sum"),
                成本=("_cost_total", "sum"),
            ).reset_index()
            sku_profit["毛利"] = sku_profit["成交额"] - sku_profit["成本"]
            for _, row in sku_profit.iterrows():
                if row["毛利"] < 0:
                    actions.append({
                        "优先级": "P2",
                        "类型": "利润为负",
                        "平台": "全平台",
                        "SKU": row["sku_code"],
                        "问题": f"毛利 {row['毛利']:.2f}",
                        "建议行动": "调整定价或降低成本",
                        "截止时间": "本月",
                    })

    # ========================================================
    # 输出
    # ========================================================
    if not actions:
        actions = [{
            "优先级": "—", "类型": "—", "平台": "—", "SKU": "—",
            "问题": "无紧急事项", "建议行动": "保持运营", "截止时间": "—",
        }]

    actions_df = pd.DataFrame(actions).sort_values("优先级")
    out = f"{cfg['paths']['output_dir']}/dashboard_action_list.csv"
    write_csv_with_labels(actions_df, out, labels)
    actions_df.attrs["output_files"] = [("dashboard_action_list.csv", "今日必做清单")]

    logger.info("运营驾驶舱完成：%d 条行动建议", len(actions))
    return actions_df