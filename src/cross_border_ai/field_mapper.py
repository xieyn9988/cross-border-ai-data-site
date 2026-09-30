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

# 文件类型 → 业务化名称（用于"运营驾驶舱"这类多文件场景的提示）
FILE_TYPE_LABELS = {
    "order": "订单明细表",
    "inventory": "库存表",
}


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

        未知实体不抛异常，返回空映射。
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

    def _check_file_type_matched(
        self, file_type: str, all_columns: List[List[str]]
    ) -> bool:
        """检查"上传的文件"里是否有能匹配"某类文件"的。

        例：file_type = "order" → 用 order 实体的前 3 个核心字段去匹配。
        """
        if file_type not in self.entities:
            return False

        entity_fields = list(self.entities[file_type]["fields"].keys())
        # 只取前几个核心字段做快速判断，避免"文件必须完美匹配所有字段"
        core_fields = entity_fields[:3]

        for cols in all_columns:
            r = self.evaluate_contract(file_type, core_fields, cols)
            if r["supported"]:
                return True
        return False

    def evaluate_all(
        self,
        columns: List[str],
        all_columns: Optional[List[List[str]]] = None,
        file_count: int = 1,
    ) -> List[Dict[str, Any]]:
        """评估所有场景，返回可用性列表。

        参数：
          columns:     上传文件的列名列表（用第一个文件，兼容旧调用）
          all_columns: 所有上传文件的列名列表（用于精确判断多文件场景）
          file_count:  上传的文件数
        """
        if all_columns is None:
            all_columns = [columns]

        out = []
        for c in self.contracts:
            # ---- 特殊场景：需要多文件（如运营驾驶舱）----
            if "required_files" in c:
                required_types = c["required_files"]  # 例：["order", "inventory"]

                matched_types = []
                missing_types = []
                for file_type in required_types:
                    if self._check_file_type_matched(file_type, all_columns):
                        matched_types.append(file_type)
                    else:
                        missing_types.append(file_type)

                supported = len(missing_types) == 0

                # 业务化提示
                missing_names = [FILE_TYPE_LABELS.get(t, t) for t in missing_types]
                required_names = [FILE_TYPE_LABELS.get(t, t) for t in required_types]

                out.append({
                    "handler": c["handler"],
                    "name": c.get("name", c["handler"]),
                    "description": c.get("description", ""),
                    "entity": c["entity"],
                    "required_fields": c.get("required_fields", []),
                    "optional_fields": c.get("optional_fields", []),
                    "field_labels": c.get("field_labels", {}),
                    "supported": supported,
                    "mapping": {},
                    "missing": missing_types,
                    "note": (
                        None if supported
                        else f"需要同时上传：{'、'.join(required_names)}（当前缺：{'、'.join(missing_names)}）"
                    ),
                    "requires_files": required_types,
                })
                continue

            # ---- 普通场景：按字段匹配判断（用第一个文件的列名）----
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