"""币种处理：识别、折算、统一口径。"""
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .exceptions import ConfigError

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RATES_FILE = REPO_ROOT / "config" / "currency_rates.yaml"


class CurrencyConverter:
    def __init__(self, rates_path: str | Path = DEFAULT_RATES_FILE):
        if not Path(rates_path).exists():
            raise ConfigError(f"汇率表不存在：{rates_path}")
        with open(rates_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.base = data.get("base", "CNY")
        self.rates: Dict[str, float] = data.get("rates", {})
        self.platform_defaults: Dict[str, Any] = data.get("platform_defaults", {})

    def to_cny(self, amount: float, currency: str) -> Optional[float]:
        """把某币种金额折算成人民币。"""
        if not currency:
            return None
        rate = self.rates.get(currency.upper())
        if rate is None:
            return None
        return round(amount * rate, 2)

    def guess_currency(self, platform: str, country: str = None) -> str:
        """根据平台/国家猜币种。"""
        if platform not in self.platform_defaults:
            return self.base
        info = self.platform_defaults[platform]
        if isinstance(info, str):
            return info
        if isinstance(info, dict) and country:
            return info.get(country, self.base)
        return self.base


_converter: Optional[CurrencyConverter] = None


def get_converter() -> CurrencyConverter:
    global _converter
    if _converter is None:
        _converter = CurrencyConverter()
    return _converter