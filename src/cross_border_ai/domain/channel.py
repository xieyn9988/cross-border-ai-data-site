"""渠道业务对象（Channel）—— 平台 + 店铺。"""


class ChannelSchema:
    identity = ["platform", "shop"]
    geography = ["country", "region"]
    mode = ["mode"]  # FBA/FBM/海外仓等
    metrics = [
        "commission_rate",   # 佣金率
        "return_rate",       # 退货率
        "avg_ship_hours",    # 平均发货时长
    ]

    all_fields = identity + geography + mode + metrics

    required = ["platform", "shop"]

    field_labels = {
        "platform": "平台",
        "shop": "店铺",
        "country": "国家",
        "region": "区域",
        "mode": "模式",
        "commission_rate": "佣金率",
        "return_rate": "退货率",
        "avg_ship_hours": "平均发货时长(小时)",
    }


def get_field_label(field: str) -> str:
    return ChannelSchema.field_labels.get(field, field)


def is_valid(fields: set) -> bool:
    return set(ChannelSchema.required).issubset(fields)