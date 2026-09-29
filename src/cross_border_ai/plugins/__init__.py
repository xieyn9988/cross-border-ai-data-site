"""插件注册：import 即触发 @register_scenario。"""

# ---- 销售 ----
from . import business_stat  # noqa: F401
from . import order_analysis  # noqa: F401
from . import sales_trend  # noqa: F401

# ---- 库存 ----
from . import inventory_alert  # noqa: F401
from . import inventory_turnover  # noqa: F401
from . import slow_moving  # noqa: F401

# ---- 营销 ----
from . import material_process  # noqa: F401
from . import listing_optimize  # noqa: F401
from . import competitor_price  # noqa: F401
from . import ad_performance  # noqa: F401

# ---- 财务 ----
from . import revenue_analysis  # noqa: F401
from . import cost_analysis  # noqa: F401

# ---- 决策 ----
from . import business_dashboard  # noqa: F401
from . import weekly_report  # noqa: F401
from . import anomaly_alert  # noqa: F401

# ---- 客户（可选）----
from . import repurchase_analysis  # noqa: F401