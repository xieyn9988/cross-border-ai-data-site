"""字段映射引擎：把任意上传文件的列名，映射到统一的业务字段。

工作方式：
  1. 读 config/field_dictionary.yaml（业务字段 → 同义词）
  2. 读 config/scenario_contracts.yaml（场景 → 需要的业务字段）
  3. 上传文件时：
       - 读文件的列名
       - 每个场景判断 required_fields 是否都能匹配到实际列
       - 返回匹配结果 + 字段映射表
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .exceptions import ConfigError

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DICT = REPO_ROOT / "config" / "field_dictionary.yaml"
DEFAULT_CONTRACTS = REPO_ROOT / "config" / "scenario_contracts.yaml"


class FieldMapper:
    def __init__(
        self,
        dictionary_path: str | Path = DEFAULT_DICT,
        contracts_path: str | Path = DEFAULT_CONTRACTS,
    ):
        self.entities = self._load_entities(dictionary_path)
        self.contracts = self._load_contracts(contracts_path)

    @staticmethod
    def _load_entities(path: str | Path) -> Dict[str, Any]:
        if not Path(path).exists():
            raise ConfigError(f"字段字典不存在：{path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if "entities" not in data:
            raise ConfigError("field_dictionary.yaml 缺少 entities")
        return data["entities"]

    @staticmethod
    def _load_contracts(path: str | Path) -> List[Dict[str, Any]]:
        if not Path(path).exists():
            raise ConfigError(f"场景契约不存在：{path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if "contracts" not in data:
            raise ConfigError("scenario_contracts.yaml 缺少 contracts")
        return data["contracts"]

    def match_entity(
        self, entity: str, columns: List[str]
    ) -> Dict[str, Optional[str]]:
        """返回 {业务字段: 实际列名}，未匹配到的字段值为 None。


        未知实体不抛异常，返回空映射：
        - 让 evaluate_contract 判定该场景"不适用"
        - 不会因为契约里多声明了一个实体就整体崩溃
        """
        if entity not in self.entities:
            return {}


        fields = self.entities[entity]["fields"]
        cols_lower = {c.strip().lower(): c for c in columns}
        result: Dict[str, Optional[str]] = {}

        for field_name, meta in fields.items():
            synonyms = [s.lower() for s in meta.get("synonyms", [field_name])]
            matched = None
            for syn in synonyms:
                if syn in cols_lower:
                    matched = cols_lower[syn]
                    break
            result[field_name] = matched
        return result

    def evaluate_contract(
        self, entity: str, required: List[str], columns: List[str]
    ) -> Dict[str, Any]:
        """判断单个场景是否可用。"""
        mapping = self.match_entity(entity, columns)
        missing = [f for f in required if mapping.get(f) is None]
        return {
            "supported": len(missing) == 0,
            "mapping": mapping,
            "missing": missing,
        }

    def evaluate_all(self, columns: List[str]) -> List[Dict[str, Any]]:
        """评估所有场景，返回可用性列表。"""
        out = []
        for c in self.contracts:
            # 特殊场景：需要多个文件（如运营驾驶舱）
            if "required_files" in c:
                # /recommend 阶段只有一个文件，标记为"需要多文件"
                out.append({
                    "handler": c["handler"],
                    "name": c.get("name", c["handler"]),
                    "description": c.get("description", ""),
                    "entity": c["entity"],
                    "required_fields": c.get("required_fields", []),
                    "optional_fields": c.get("optional_fields", []),
                    "field_labels": c.get("field_labels", {}),
                    "supported": False,                       # ★ 不标为可用
                    "mapping": {},
                    "missing": [],
                    "note": f"需要同时上传：{'、'.join(c['required_files'])}",  # ★ 提示
                    "requires_files": c["required_files"],
                })
                continue

            result = self.evaluate_contract(
                c["entity"], c.get("required_fields", []), columns
            )
            out.append({
                "handler": c["handler"],
                "name": c.get("name", c["handler"]),
                "description": c.get("description", ""),
                "entity": c["entity"],
                "required_fields": c.get("required_fields", []),
                "optional_fields": c.get("optional_fields", []),
                "field_labels": c.get("field_labels", {}),
                "supported": result["supported"],
                "mapping": result["mapping"],
                "missing": result["missing"],
            })
        return out

    def get_contract(self, handler: str) -> Optional[Dict[str, Any]]:
        for c in self.contracts:
            if c["handler"] == handler:
                return c
        return None


# 单例
_mapper: Optional[FieldMapper] = None


def get_mapper() -> FieldMapper:
    global _mapper
    if _mapper is None:
        _mapper = FieldMapper()
    return _mapper