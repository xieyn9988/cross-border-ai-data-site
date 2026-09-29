import os
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cross_border_ai.config_loader import load_config  # noqa: E402


@pytest.fixture
def cfg(tmp_path):
    config = load_config()
    for key in ("data_dir", "output_dir", "log_dir"):
        config["paths"][key] = str(tmp_path / key)
        os.makedirs(config["paths"][key], exist_ok=True)

    pd.DataFrame({
        "region": ["US", "US", "EU"],
        "order_num": [10, "abc", 5],
        "sales": [1000, 2000, 500],
        "exposure": [1000, 2000, 0],
    }).to_csv(f"{config['paths']['data_dir']}/shop_data.csv", index=False)

    pd.DataFrame({
        "material_id": [1, None],
        "category": ["bag", "shoe"],
        "raw_text": ["red bag", "blue shoe"],
    }).to_csv(f"{config['paths']['data_dir']}/material.csv", index=False)

    pd.DataFrame({
        "pid": [1, 2],
        "raw_title": ["bag", "shoe"],
        "raw_desc": ["nice", "good"],
    }).to_csv(f"{config['paths']['data_dir']}/listing.csv", index=False)

    pd.DataFrame({
        "sku": ["A", "B"],
        "stock": [5, 100],
        "safety_stock": [20, 30],
    }).to_csv(f"{config['paths']['data_dir']}/inventory.csv", index=False)

    pd.DataFrame({
        "sku": ["A", "B"],
        "my_price": [100, 50],
        "competitor_price": [80, 55],
    }).to_csv(f"{config['paths']['data_dir']}/competitor_price.csv", index=False)

    pd.DataFrame({
        "campaign": ["c1", "c2"],
        "spend": [100, 0],
        "sales": [500, 200],
        "clicks": [50, 20],
        "impressions": [1000, 500],
    }).to_csv(f"{config['paths']['data_dir']}/ad_performance.csv", index=False)

    return config