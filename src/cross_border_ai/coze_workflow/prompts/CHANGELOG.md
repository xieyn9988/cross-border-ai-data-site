# Coze 工作流变更记录

## [Unreleased]
### Fixed
- 待修复：大模型输出 str → JsonTocsv 需要 Array，拟增加代码节点

## [2026-09-27]
### Added
- 初版工作流：开始 → 大模型 → JsonTocsv → create_spreadsheet → 结束
- 大模型节点系统提示词：字面解析 CSV → JSON
- 工作流定义文档化，提示词版本化