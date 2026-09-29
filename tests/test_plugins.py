from cross_border_ai.plugins.business_stat import calc_business_stat
from cross_border_ai.plugins.inventory_alert import inventory_alert


def test_business_stat_no_inf(cfg):
    df = calc_business_stat(cfg, {})
    eu = df[df["region"] == "EU"].iloc[0]
    assert eu["conversion_rate"] == 0.0


def test_inventory_alert_threshold(cfg):
    df = inventory_alert(cfg, {"threshold": 50})
    assert (df["alert"] == "紧急补货").sum() == 1