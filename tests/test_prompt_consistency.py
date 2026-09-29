from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COZE = REPO / "src" / "cross_border_ai" / "coze_workflow" / "prompts"


def test_system_prompt_exists():
    content = (COZE / "csv_to_json_system.md").read_text(encoding="utf-8")
    assert len(content.strip()) > 100
    for kw in ["JSON", "禁止", "表头", "字符串类型"]:
        assert kw in content, f"缺少约束：{kw}"


def test_workflow_definition_complete():
    content = (REPO / "src" / "cross_border_ai" / "coze_workflow" / "workflow_definition.md").read_text(encoding="utf-8")
    for node in ["开始", "大模型", "JsonTocsv", "create_spreadsheet", "结束"]:
        assert node in content