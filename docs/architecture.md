# 架构说明

本文档面向**开发者与维护者**，说明本项目的分层设计、核心机制、扩展方式。

---

## 一、整体分层

系统采用 **5 层架构**，从下到上依次为：

### L1 基础层（Infrastructure）

**职责**：提供与业务无关的通用能力。

**包含模块**：

- `io_utils.py` -- CSV 安全读写（多编码 / 多格式）
- `logger.py` -- 日志（按模块分文件 + 轮转）
- `exceptions.py` -- 异常分层
- `currency.py` -- 币种处理与折算
- `config_loader.py` -- 配置加载与校验

### L2 接入层（Ingestion）

**职责**：把用户上传的任意 CSV 翻译成系统认识的业务字段。

**包含模块**：

- `field_mapper.py` -- 字段映射引擎
- `config/field_dictionary.yaml` -- 业务字段字典
- `config/scenario_contracts.yaml` -- 场景契约

**核心机制**：

- 每个业务字段（如 `amount`）配置一组同义词
- 系统读上传文件的列名，逐字段匹配同义词，得到映射表
- 每个场景声明它需要哪些字段，系统判断该场景是否可用

### L3 领域层（Domain）

**职责**：定义业务里有什么。

**包含模块**：

- `domain/order.py` -- 订单对象
- `domain/product.py` -- 商品对象
- `domain/sku.py` -- SKU 对象
- `domain/inventory.py` -- 库存对象
- `domain/customer.py` -- 客户对象
- `domain/channel.py` -- 渠道对象

**每个对象暴露**：

- `all_fields` -- 所有字段
- `required` -- 必需字段
- `field_labels` -- 字段中文标签
- `is_valid()` -- 校验函数

### L4 分析层（Analysis）

**职责**：定义业务现在怎么样。

**包含 13 个插件**：

- `order_analysis.py` / `sales_trend.py` / `business_stat.py`
- `inventory_alert.py` / `inventory_turnover.py` / `slow_moving.py`
- `ad_performance.py` / `competitor_price.py`
- `material_process.py` / `listing_optimize.py`
- `revenue_analysis.py` / `cost_analysis.py` / `repurchase_analysis.py`

**每个插件的约定**：

- 用 `@register_scenario("xxx")` 装饰
- 函数签名 `func(cfg, params)`
- 从 `params` 里取 `field_mapping` / `field_labels` / `input_files`
- 输出 DataFrame，挂 `df.attrs["output_files"]`

### L5 决策层（Decision）

**职责**：把分析结果翻译成今天该干什么。

**包含 3 个插件**：

- `business_dashboard.py` -- 运营驾驶舱（订单 + 库存交叉）
- `weekly_report.py` -- 业务周报
- `anomaly_alert.py` -- 异常告警

**与 L4 的区别**：

- L4 输出数据表
- L5 输出行动清单

---

## 二、核心机制：字段驱动

### 问题

不同 ERP、不同平台导出的 CSV 列名千差万别：Amazon 导出订单编号，Shopee 导出订单号，ERP 导出 order_id。

如果每个场景都硬编码列名，换个数据源就报错。

### 解决方案

引入**业务字段字典**。在 `config/field_dictionary.yaml` 里：

```
order_id:
  synonyms: ["订单编号", "订单号", "order_id", "order_no", "单号"]
```

**上传文件时**：

1. 读文件的列名
2. 逐字段匹配同义词
3. 得到业务字段到实际列名的映射表
4. 插件用映射表 rename，之后所有逻辑只用业务字段名

### 好处

- **换数据源**：只改字段字典加同义词，不改代码
- **跨平台**：同一场景能处理多平台数据
- **容错**：缺字段时给明确提示

---

## 三、插件化扩展

### 新增场景（3 步）

**第 1 步：写插件**

在 `src/cross_border_ai/plugins/` 新建 `xxx.py`：

```
@register_scenario("xxx")
def my_scenario(cfg, params=None):
    params = params or {}
    mapping = params.get("field_mapping", {})
    input_files = params.get("input_files") or []
    df.attrs["output_files"] = [("xxx.csv", "报告名")]
    return df
```

**第 2 步：加契约**

在 `config/scenario_contracts.yaml` 加一条：

```
- handler: xxx
  entity: order
  name: "我的场景"
  required_fields: [order_id, amount]
```

**第 3 步：注册**

在 `plugins/__init__.py` 加：

```
from . import xxx
```

**完成**。前端自动出现新场景，不用改 API。

### 新增字段

只改 `config/field_dictionary.yaml`：

```
order:
  fields:
    new_field:
      synonyms: ["新字段名", "别名1", "别名2"]
```

---

## 四、数据流

用户上传 CSV，触发 `/recommend` 接口：读列名，字段匹配，返回可用场景。

用户勾选场景，触发 `/process` 接口：

- 保存所有上传文件到 `output/uploads/`
- 对每个场景：遍历所有文件，找字段匹配的；传给插件；插件处理，输出到 `output/results/`
- 返回每个场景的结果和下载链接

用户下载 CSV。

---

## 五、异常分层

```
CrossBorderAIError（基类）
├── ConfigError           配置错误
├── DataValidationError   输入数据错误
└── BusinessLogicError    业务逻辑错误
```

**pipeline 处理**：

- `CrossBorderAIError` -- 记录 error 日志，标记 business_error
- 其他 `Exception` -- 记录 critical 日志，标记 unknown_error
- **单模块失败不影响其他模块**

---

## 六、可观测性

**日志**：

- 按模块分文件，位于 `output/logs/模块名.log`
- 轮转：单文件 5MB，保留 3 份
- 格式：时间 | 级别 | 模块 | 消息

**输出**：

- 上传文件：`output/uploads/{run_id}_{idx}_{原文件名}.csv`
- 结果文件：`output/results/{场景名}.csv`
- 下载名：`{场景中文名}_{报告名}_{时间戳}.csv`

---

## 七、阶段演进

**V3.0.0（当前）**：16 个场景 + 6 大业务对象 + 币种处理 + 多文件上传

**V3.1（计划）**：结果可视化（表格预览 + 图表）

**V3.2（计划）**：历史记录（SQLite），可回溯、可对比

**V4.0（计划）**：定时任务 + API 接入 ERP（Amazon SP-API / Shopee Open API）

**V5.0（计划）**：多租户 + 用户体系 + 权限管理

---

## 八、设计决策

### 决策 1：为什么不用数据库

**当前阶段**：系统本质是文件处理器，用户上传处理下载，不需要持久化历史。

**触发升级**：需要历史记录，上 SQLite；需要多用户，SQLite 加用户表；需要大规模，上 PostgreSQL。

### 决策 2：为什么用 YAML 而不是数据库配置

可读（业务人员能直接改）、可版本化（Git 能追踪）、简单（无需 DB 连接）。

### 决策 3：为什么用字段驱动而不是场景驱动

- **场景驱动**：先想要分析什么，再定字段，换数据源就崩
- **字段驱动**：先想业务里有什么，再组织分析，换数据源只改字典
