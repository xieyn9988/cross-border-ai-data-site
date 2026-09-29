"""声明式编排：读 scenarios.yaml，自动执行已注册插件。"""
from typing import Any, Dict, List

import yaml

from .config_loader import ensure_dirs
from .exceptions import ConfigError, CrossBorderAIError
from .logger import setup_logger
from .scenario_registry import get_scenario
from . import plugins  # noqa: F401  触发所有插件注册


def load_scenarios(path: str = "./config/scenarios.yaml") -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if "scenarios" not in data:
        raise ConfigError("scenarios.yaml 缺少 scenarios 字段")
    return data["scenarios"]


def run_pipeline(cfg: Dict[str, Any], scenario_file: str = "./config/scenarios.yaml") -> Dict[str, str]:
    logger = setup_logger("pipeline", cfg["paths"]["log_dir"])
    ensure_dirs(cfg)
    results: Dict[str, str] = {}

    for sc in load_scenarios(scenario_file):
        name = sc["name"]
        if not sc.get("enabled", True):
            logger.info("场景 [%s] 已禁用", name)
            results[name] = "disabled"
            continue
        try:
            handler = get_scenario(sc["handler"])
            logger.info("执行场景 [%s] → %s", name, sc["handler"])
            handler(cfg, sc.get("params", {}))
            results[name] = "success"
        except CrossBorderAIError as e:
            logger.error("场景 [%s] 业务异常：%s", name, e, exc_info=True)
            results[name] = f"business_error: {e}"
        except Exception as e:
            logger.critical("场景 [%s] 未知异常：%s", name, e, exc_info=True)
            results[name] = f"unknown_error: {e}"
    return results