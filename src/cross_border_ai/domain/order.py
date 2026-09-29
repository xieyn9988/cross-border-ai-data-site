"""订单业务对象（Order）。"""


class OrderSchema:
    # ---------- 标识 ----------
    identity = ["order_id", "platform", "mode", "shop"]

    # ---------- 交易 ----------
    commerce = [
        "status", "amount", "quantity", "receivable",
        "product_id", "product_name", "sku_code",
    ]

    # ---------- 履约 ----------
    logistics = ["pay_time", "ship_time", "deliver_time", "logistics_company"]

    # ---------- 财务 ----------
    finance = ["cost", "platform_fee", "fba_fee", "ad_cost", "currency"]

    # ---------- 地理 ----------
    geographic = ["country", "state", "city", "region"]

    # ---------- 扩展 ----------
    extras = ["refund_status", "refund_amount"]

    all_fields = (identity + commerce + logistics +
                  finance + geographic + extras)

    required = ["order_id", "platform", "shop", "status",
                "amount", "quantity", "product_name"]

    field_labels = {
        "order_id": "订单编号",
        "platform": "平台",
        "mode": "模式",
        "shop": "店铺",
        "status": "订单状态",
        "amount": "成交价",
        "quantity": "数量",
        "receivable": "应收金额",
        "product_id": "商品ID",
        "product_name": "商品名称",
        "sku_code": "SKU编码",
        "pay_time": "付款时间",
        "ship_time": "发货时间",
        "deliver_time": "妥投时间",
        "logistics_company": "物流公司",
        "cost": "成本",
        "platform_fee": "平台佣金",
        "fba_fee": "FBA费",
        "ad_cost": "广告费",
        "currency": "币种",
        "country": "国家",
        "state": "州/省",
        "city": "城市",
        "region": "区域",
        "refund_status": "退款状态",
        "refund_amount": "退款金额",
    }


def get_field_label(field: str) -> str:
    return OrderSchema.field_labels.get(field, field)


def is_valid(fields: set) -> bool:
    return set(OrderSchema.required).issubset(fields)