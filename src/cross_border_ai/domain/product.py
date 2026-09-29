"""商品业务对象（Product）。

商品是 SKU 的父级：
  - 一个商品（SPU）包含多个 SKU（规格）
  - 例：商品"果酸控油洗发水" 包含 SKU "280ml"、"500ml"

字段分组：
  identity    标识（商品ID、名称）
  category    类目
  finance     财务（成本）
  extras      扩展（品牌、供应商、条码）
"""


class ProductSchema:
    """商品业务对象的字段契约。"""

    # ---------- 标识 ----------
    identity = [
        "product_id",       # 商品ID（SPU）
        "product_name",     # 商品名称
    ]

    # ---------- 类目 ----------
    category = [
        "category",         # 类目
        "sub_category",     # 子类目
        "brand",            # 品牌
    ]

    # ---------- 财务 ----------
    finance = [
        "cost",             # 成本价
        "retail_price",     # 建议零售价
    ]

    # ---------- 扩展 ----------
    extras = [
        "supplier",         # 供应商
        "barcode",          # 条形码
        "origin",           # 产地
        "weight",           # 重量（克）
        "dimensions",       # 尺寸
    ]

    # ---------- 汇总 ----------
    all_fields = identity + category + finance + extras

    # ---------- 必需字段 ----------
    # 一个商品只要"有 ID"就够了，其他字段都是可选
    required = ["product_id"]

    # ---------- 字段中文标签（用于输出） ----------
    field_labels = {
        "product_id": "商品ID",
        "product_name": "商品名称",
        "category": "类目",
        "sub_category": "子类目",
        "brand": "品牌",
        "cost": "成本",
        "retail_price": "建议零售价",
        "supplier": "供应商",
        "barcode": "条形码",
        "origin": "产地",
        "weight": "重量(g)",
        "dimensions": "尺寸",
    }


# ---------- 便捷函数 ----------
def get_field_label(field: str) -> str:
    """获取字段的中文标签，未定义则返回原字段名。"""
    return ProductSchema.field_labels.get(field, field)


def is_valid(fields: set) -> bool:
    """判断给定的字段集合是否满足商品的必需字段。"""
    return set(ProductSchema.required).issubset(fields)