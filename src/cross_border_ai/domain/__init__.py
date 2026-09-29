"""领域层：6 大业务对象的定义。

每个对象暴露：
  - all_fields     所有字段
  - required       必需字段
  - field_labels   中文字段标签
  - is_valid()     校验函数
  - get_field_label()  获取中文标签
"""

from .order import OrderSchema, get_field_label as order_label, is_valid as is_valid_order
from .product import ProductSchema, get_field_label as product_label, is_valid as is_valid_product
from .sku import SkuSchema, get_field_label as sku_label, is_valid as is_valid_sku
from .inventory import InventorySchema, get_field_label as inventory_label, is_valid as is_valid_inventory
from .customer import CustomerSchema, get_field_label as customer_label, is_valid as is_valid_customer
from .channel import ChannelSchema, get_field_label as channel_label, is_valid as is_valid_channel

__all__ = [
    "OrderSchema", "ProductSchema", "SkuSchema",
    "InventorySchema", "CustomerSchema", "ChannelSchema",
    "order_label", "product_label", "sku_label",
    "inventory_label", "customer_label", "channel_label",
    "is_valid_order", "is_valid_product", "is_valid_sku",
    "is_valid_inventory", "is_valid_customer", "is_valid_channel",
]