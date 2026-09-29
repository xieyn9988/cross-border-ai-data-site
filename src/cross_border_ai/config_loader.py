import os
from typing import Any, Dict

import yaml

from .exceptions import ConfigError

_REQUIRED = {"paths", "files", "business_rules", "prompt_templates"}


def load_config(config_path: str = "./config/config.yaml") -> Dict[str, Any]:
    if not os.path.exists(config_path):
        raise ConfigError(f"配置文件不存在：{config_path}")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"配置解析失败：{e}") from e
    if not isinstance(cfg, dict):
        raise ConfigError("配置根节点必须是字典")
    missing = _REQUIRED - cfg.keys()
    if missing:
        raise ConfigError(f"配置缺少字段：{missing}")
    return cfg


def ensure_dirs(cfg: Dict[str, Any]) -> None:
    for key in ("data_dir", "output_dir", "log_dir"):
        path = cfg["paths"].get(key)
        if not path:
            raise ConfigError(f"paths 缺少 {key}")
        os.makedirs(path, exist_ok=True)