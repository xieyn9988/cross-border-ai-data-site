"""SKU 业务对象（Stock Keeping Unit）。

SKU 是商品的最小销售单元：
  - 一个商品有多个 SKU（规格）
  - 例：洗发水有 "280ml"、"500ml"、"试用装 8ml" 三个 SKU

字段分组：
  identity    标识（SKU编码、规格名）
  parent      父级（所属商品ID）
  finance     财务（成本、售价）
  logistics   物流（重量、尺寸）
  extras      扩展（条码、图片、状态）
"""


class SkuSchema:
    """SKU 业务对象的字段契约。"""

    # ---------- 标识 ----------
    identity = [
        "sku_code",         # SKU编码
        "sku_name",         # SKU规格名（如"280ml"）
    ]

    # ---------- 父级 ----------
    parent = [
        "product_id",       # 所属商品ID
        "product_name",     # 所属商品名（冗余，便于查询）
    ]

    # ---------- 财务 ----------
    finance = [
        "cost",             # 成本价
        "price",            # 售价
        "currency",         # 币种
    ]

    # ---------- 物流 ----------
    logistics = [
        "weight",           # 重量（克）
        "length",           # 长（cm）
        "width",            # 宽（cm）
        "height",           # 高（cm）
    ]

    # ---------- 扩展 ----------
    extras = [
        "barcode",          # 条形码
        "image_url",        # 图片链接
        "status",           # 状态（在售/下架）
        "created_at",       # 创建时间
    ]

    # ---------- 汇总 ----------
    all_fields = identity + parent + finance + logistics + extras

    # ---------- 必需字段 ----------
    # 一个 SKU 最少要有"编码"，否则无法区分
    required = ["sku_code"]

    # ---------- 字段中文标签 ----------
    field_labels = {
        "sku_code": "SKU编码",
        "sku_name": "SKU规格",
        "product_id": "商品ID",
        "product_name": "商品名称",
        "cost": "成本",
        "price": "售价",
        "currency": "币种",
        "weight": "重量(g)",
        "length": "长(cm)",
        "width": "宽(cm)",
        "height": "高(cm)",
        "barcode": "条形码",
        "image_url": "图片链接",
        "status": "状态",
        "created_at": "创建时间",
    }


# ---------- 便捷函数 ----------
def get_field_label(field: str) -> str:
    """获取字段的中文标签。"""
    return SkuSchema.field_labels.get(field, field)


def is_valid(fields: set) -> bool:
    """判断给定的字段集合是否满足 SKU 的必需字段。"""
    return set(SkuSchema.required).issubset(fields)