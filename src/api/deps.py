from functools import lru_cache
from typing import Any, Dict

from cross_border_ai.config_loader import load_config
from cross_border_ai import plugins  # noqa: F401  触发注册


@lru_cache(maxsize=1)
def get_config() -> Dict[str, Any]:
    return load_config()