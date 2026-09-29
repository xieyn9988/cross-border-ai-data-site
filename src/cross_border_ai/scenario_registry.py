from typing import Callable, Dict

_REGISTRY: Dict[str, Callable] = {}


def register_scenario(name: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        if name in _REGISTRY:
            raise ValueError(f"场景重复注册：{name}")
        _REGISTRY[name] = func
        return func
    return decorator


def get_scenario(name: str) -> Callable:
    if name not in _REGISTRY:
        raise KeyError(f"未注册场景：{name}")
    return _REGISTRY[name]


def list_scenarios() -> Dict[str, Callable]:
    return dict(_REGISTRY)