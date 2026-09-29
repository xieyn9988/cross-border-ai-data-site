from typing import List

import pandas as pd


def coerce_numeric(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def safe_divide(numerator: pd.Series, denominator: pd.Series, fill: float = 0.0) -> pd.Series:
    """除零保护：分母为 0 时返回 fill。"""
    return (numerator / denominator.replace(0, pd.NA)).fillna(fill)