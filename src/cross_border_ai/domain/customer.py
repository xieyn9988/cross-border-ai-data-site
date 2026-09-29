"""客户业务对象（Customer）—— 预留，未来用于客户分析。"""


class CustomerSchema:
    identity = ["customer_id", "customer_name"]
    contact = ["email", "phone"]
    geography = ["country", "state", "city"]
    behavior = [
        "first_order_time", "last_order_time",
        "total_orders", "total_amount",
    ]
    extras = ["tags", "level"]

    all_fields = identity + contact + geography + behavior + extras

    required = ["customer_id"]

    field_labels = {
        "customer_id": "客户ID",
        "customer_name": "客户名称",
        "email": "邮箱",
        "phone": "电话",
        "country": "国家",
        "state": "州/省",
        "city": "城市",
        "first_order_time": "首单时间",
        "last_order_time": "最近下单",
        "total_orders": "总订单数",
        "total_amount": "总消费额",
        "tags": "标签",
        "level": "会员等级",
    }


def get_field_label(field: str) -> str:
    return CustomerSchema.field_labels.get(field, field)


def is_valid(fields: set) -> bool:
    return set(CustomerSchema.required).issubset(fields)