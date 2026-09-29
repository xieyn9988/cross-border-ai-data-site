# 更新日志

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [Unreleased]

### Planned

- V3.1：结果可视化（表格预览 + 图表）
- V3.2：历史记录（SQLite）
- V4.0：定时任务 + API 接入 ERP
- V5.0：多租户 + 用户体系

---

## [3.0.1] - 2026-09-30

### Added

- 多文件上传：一次上传多个 CSV，每个场景自动匹配对应文件
- `assets` 字段处理：支持多平台、多店铺、多 SKU 交叉分析
- 业务数据统计：兼容 `amount` / `sales` 两种命名

### Fixed

- 修复多文件上传时「第一个文件评估所有场景」的 bug
- 修复 `field_dictionary.yaml` 里 `sales` / `amount` 同义词冲突
- 修复 `business_stat.py` 缺少 `sales` 兼容逻辑
- 修复前端场景列表「默认勾选」导致的上传新文件时勾选残留
- 修复 `recommend` 接口 `mapper` 变量未定义

### Changed

- 统一 SKU 字段命名为「库存SKU」，区别于「平台 SKU ID」
- 清理 `workspace.py` 里的调试 print

---

## [3.0.0] - 2026-09-29

### Added

- 工程化重构：从单文件脚本升级为分层架构
- 插件化机制：`scenario_registry` 自动注册
- 声明式编排：`scenarios.yaml` 控制场景开关与参数
- 业务场景扩展至 16 个：
  - 销售：订单分析、销售趋势、业务数据统计
  - 库存：库存预警、库存周转、滞销识别
  - 营销：广告效果、竞品价格、素材处理、Listing 优化
  - 财务：收入分析、成本分析
  - 决策：运营驾驶舱、业务周报、异常告警
  - 客户：复购分析
- 6 大业务对象：Order / Product / SKU / Inventory / Customer / Channel
- 多币种处理：USD / EUR / JPY / SGD / MYR / CNY 自动折算
- 异常分层：ConfigError / DataValidationError / BusinessLogicError
- 日志系统：按模块分文件，5MB 轮转，保留 3 份
- FastAPI 封装：REST 接口 + 文件上传
- 前端页面：`/app` 单页工作台
- Coze 资产版本化：提示词入库 + 一致性测试
- 完整文档：README / 架构 / 业务价值 / 维护指南
- `Makefile`：`setup` / `run` / `test` / `api`
- `Dockerfile`：容器化部署
- GitHub Actions CI

### Changed

- 目录结构重组：`src/cross_border_ai/` 作为核心包
- 入口统一：`scripts/run.py` 为命令行入口

### Removed

- 硬编码路径与列名（迁移至 `config.yaml`）
- `print` 调试输出（迁移至 `logger`）

---

## [2.0.0] - 2026-09-27

### Added

- V2 工程化版本：增加全局异常捕获、脏数据识别、日志输出

### Fixed

- 修复 V1 异常输入导致程序崩溃的问题

---

## [1.0.0] - 2026-09-26

### Added

- V1 初版：单文件脚本，覆盖三大基础场景

---

## 版本号说明

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)：

- **主版本号**：不兼容的 API 变更
- **次版本号**：向下兼容的功能新增
- **修订号**：向下兼容的问题修复
