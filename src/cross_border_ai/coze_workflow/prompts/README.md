# 提示词版本管理

## 为什么版本化
Coze 云端提示词是黑盒，改坏后难回滚、难审计。本项目将提示词纳入 Git，与 Python 代码同级对待。

## 命名规范
- `*_system.md`：节点系统提示词
- `*_user.md`：节点用户提示词
- 文件内容必须与 Coze 云端完全一致；改云端前先改本地，再同步。

## 同步流程
1. 修改本地 `prompts/*.md`
2. 运行 `make test`（`test_prompt_consistency.py` 会校验关键约束）
3. 复制到 Coze 云端节点提示词
4. 在 `CHANGELOG.md` 记录变更

## 一致性约束
提示词中引用的业务变量（如列名、平台）必须与 `config/config.yaml` 键名一致。