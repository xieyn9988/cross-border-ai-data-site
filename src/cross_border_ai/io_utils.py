"""IO 工具：健壮的 CSV 读取/写出。"""
import re
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd

from .exceptions import DataValidationError


# ============================================================
# 编码检测
# ============================================================
def detect_encoding(content: bytes) -> str:
    """检测 CSV 编码。优先 utf-8-sig（Excel 导出），其次 utf-8/gb18030/gbk/big5。"""
    if content.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    for enc in ("utf-8", "gb18030", "gbk", "big5"):
        try:
            content.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "utf-8"


# ============================================================
# 健壮读取（多编码 + 多格式）
# ============================================================
def read_csv_any_encoding(file_path: str, **kwargs) -> pd.DataFrame:
    """自动尝试多种编码读取 CSV。"""
    last_err = None
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5"):
        try:
            return pd.read_csv(file_path, encoding=enc, **kwargs)
        except UnicodeDecodeError as e:
            last_err = e
            continue
    raise last_err if last_err else RuntimeError(f"无法读取：{file_path}")


def read_csv_safe(file_path: str, required_columns: Iterable[str]) -> pd.DataFrame:
    """读取并校验必需列。"""
    path = Path(file_path)
    if not path.exists():
        raise DataValidationError(f"文件不存在：{file_path}")
    try:
        df = read_csv_any_encoding(file_path)
    except Exception as e:
        raise DataValidationError(f"读取失败：{file_path}，原因：{e}") from e

    missing = set(required_columns) - set(df.columns)
    if missing:
        raise DataValidationError(f"{file_path} 缺少列：{sorted(missing)}")
    return df.dropna(how="all").reset_index(drop=True)


# ============================================================
# 健壮写出
# ============================================================
def write_csv_with_labels(
    df: pd.DataFrame,
    file_path: str,
    labels: Optional[Dict[str, str]] = None,
) -> str:
    """输出 CSV，把业务字段名换成中文标签。"""
    labels = labels or {}
    df_out = df.rename(columns={k: v for k, v in labels.items() if k in df.columns})
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(file_path, index=False, encoding="utf-8-sig")
    return file_path


def write_csv_safe(df: pd.DataFrame, file_path: str) -> str:
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=False, encoding="utf-8-sig")
    return file_path


# ============================================================
# 时间解析（多格式兼容）
# ============================================================
_TIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
]


def parse_datetime_safe(series: pd.Series) -> pd.Series:
    """多格式兼容解析时间。失败置 NaT。"""
    if series.empty:
        return pd.to_datetime(series, errors="coerce")
    s = series.astype(str).str.strip()
    result = pd.to_datetime(s, errors="coerce")
    if result.isna().sum() < len(s):
        return result
    for fmt in _TIME_FORMATS:
        try:
            parsed = pd.to_datetime(s, format=fmt, errors="coerce")
            if parsed.notna().sum() > 0:
                return parsed
        except Exception:
            continue
    return result


# ============================================================
# 时区统一（全部转 UTC）
# ============================================================
def to_utc(series: pd.Series) -> pd.Series:
    """把时间序列统一转为 UTC（无时区的按本地处理，不转换）。"""
    try:
        return series.dt.tz_localize("UTC", ambiguous="NaT", nonexistent="NaT")
    except Exception:
        return series


# ============================================================
# 去重（按 key 保留第一行）
# ============================================================
def drop_duplicates_safe(
    df: pd.DataFrame,
    subset: List[str],
    logger=None,
) -> pd.DataFrame:
    """按 subset 去重，返回去重后的 df。"""
    if not all(c in df.columns for c in subset):
        return df
    before = len(df)
    df = df.drop_duplicates(subset=subset, keep="first")
    after = len(df)
    if logger and after < before:
        logger.info("去重：%d 行 → %d 行（去掉 %d 行重复）", before, after, before - after)
    return df


def convert_amount_to_cny(df, amount_col: str, currency_col: str):
    """把 DataFrame 里的金额列折算成人民币，新增一列 _amount_cny。"""
    from .currency import get_converter
    converter = get_converter()
    df = df.copy()
    if currency_col in df.columns:
        df["_amount_cny"] = df.apply(
            lambda r: converter.to_cny(r[amount_col], r[currency_col])
            if pd.notna(r[amount_col]) and pd.notna(r[currency_col]) else None,
            axis=1,
        )
    else:
        df["_amount_cny"] = df[amount_col]
    return df