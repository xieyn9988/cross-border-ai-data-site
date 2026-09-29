"""库存业务对象（Inventory）。"""


class InventorySchema:
    # ---------- 标识 ----------
    identity = ["platform", "mode", "shop", "warehouse"]

    # ---------- 商品 ----------
    product = [
        "product_id", "product_name",
        "sku_code", "sku_name", "category",
    ]

    # ---------- 库存 ----------
    stock = ["stock", "safety_stock", "in_transit", "locked_stock"]

    # ---------- 销售 ----------
    sales = ["daily_sales", "sales_30d"]

    # ---------- 补货 ----------
    replenish = ["replenish_days", "safety_days"]

    # ---------- 财务 ----------
    finance = ["cost"]

    all_fields = (identity + product + stock + sales + replenish + finance)

    required = ["platform", "shop", "sku_code", "stock", "safety_stock"]

    field_labels = {
        "platform": "平台",
        "mode": "模式",
        "shop": "店铺",
        "warehouse": "仓库",
        "product_id": "商品ID",
        "product_name": "商品名称",
        "sku_code": "SKU编码",
        "sku_name": "SKU规格",
        "category": "类目",
        "stock": "当前库存",
        "safety_stock": "安全库存",
        "in_transit": "在途库存",
        "locked_stock": "锁定库存",
        "daily_sales": "日均销量",
        "sales_30d": "近30天销量",
        "replenish_days": "补货周期(天)",
        "safety_days": "安全天数",
        "cost": "成本",
    }


def get_field_label(field: str) -> str:
    return InventorySchema.field_labels.get(field, field)


def is_valid(fields: set) -> bool:
    return set(InventorySchema.required).issubset(fields)