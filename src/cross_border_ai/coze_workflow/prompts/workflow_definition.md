# Coze 工作流定义（版本化）

## 工作流名称
`Cross_border_CSV_data_cleaning`

## 节点拓扑

| 序号 | 节点名 | 类型 | 输入 | 输出 |
|---|---|---|---|---|
| 1 | 开始 | Start | `input: str` | `input` |
| 2 | 大模型 | LLM（豆包·2.0·lite） | `csv_data = 开始.input` | `output: str` |
| 3 | JsonTocsv | 插件 | `data = 大模型.output`（需先转 Array） | `csv: str` |
| 4 | create_spreadsheet | 插件 | `csv_content = JsonTocsv.csv`，`title = clean`，`to_format = csv` | `data: str`（下载链接） |
| 5 | 结束 | End | `download_file = create_spreadsheet.data` | 返回变量 |

## 参数映射（对照 Python）

| Python 位置 | Coze 节点 | 说明 |
|---|---|---|
| `io_utils.read_csv_safe` | 节点 1 开始 | 接收用户上传 CSV 文本 |
| `cleaning.*` | 节点 2 大模型 | 用系统提示词替代确定性清洗 |
| `io_utils.write_csv_safe` | 节点 3+4 | 转 CSV + 生成下载文件 |
| `pipeline.run_pipeline` | 节点连线 | 编排顺序 |

## 已知问题

### 问题 1：类型不匹配
- 现象：大模型输出 `str`，`JsonTocsv.data` 需要 `Array<Object>`
- 临时方案：节点 2 和节点 3 之间插入代码节点做 `JSON.parse`
- 长期方案：阶段 2 改用 API 调用（见 `docs/coze_migration.md`）

### 问题 2：稳定性
- 现象：提示词再严谨，也可能因模型波动字段错位
- 长期方案：Python 封装 API，Coze 只负责上传与展示

### 问题 3：Token 成本
- 现象：单次约 33k tokens（实测）
- 长期方案：API 调用后成本趋近于 0

## 截图索引
见 `screenshots/` 目录。