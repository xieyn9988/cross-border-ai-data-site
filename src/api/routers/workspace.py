"""业务工作台 API：上传文件 → 字段匹配 → 执行场景 → 返回下载链接。"""

import json
import secrets
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote, unquote

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from cross_border_ai.exceptions import CrossBorderAIError
from cross_border_ai.field_mapper import get_mapper
from cross_border_ai.scenario_registry import get_scenario, list_scenarios

from ..deps import get_config

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[3]
UPLOAD_DIR = REPO_ROOT / "output" / "uploads"
RESULT_DIR = REPO_ROOT / "output" / "results"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 工具函数
# ============================================================
def _detect_encoding(content: bytes) -> str:
    if content.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    for enc in ("utf-8", "gb18030", "gbk", "big5"):
        try:
            content.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "utf-8"


def _read_columns(content: bytes) -> List[str]:
    enc = _detect_encoding(content)
    try:
        df = pd.read_csv(BytesIO(content), nrows=0, encoding=enc)
    except Exception as e:
        raise HTTPException(400, f"无法解析 CSV 表头（编码 {enc}）：{e}") from e
    return [str(c) for c in df.columns]


# ============================================================
# 场景列表
# ============================================================
@router.get("/api/workspace/scenarios")
def list_available() -> Dict[str, Any]:
    return {"scenarios": [{"handler": k, "name": k} for k in list_scenarios().keys()]}


# ============================================================
# 上传前推荐：接收多个文件，每个文件 + 每个场景分别评估
# ============================================================
@router.post("/api/workspace/recommend")
async def recommend(files: List[UploadFile] = File(...)):
    ...
    # 读所有文件的列名
    all_columns = []
    for f in files:
        content = await f.read()
        cols = _read_columns(content)
        all_columns.append(cols)

    # 对每个场景，判断"它是否能匹配任意一个文件的列名"
    mapper = get_mapper()

    scenarios = []
    for c in mapper.contracts:
        handler = c["handler"]
        entity = c["entity"]
        required = c.get("required_fields", [])

        # 遍历每个文件的列名
        best_supported = False
        best_missing = []
        for cols in all_columns:
            r = mapper.evaluate_contract(entity, required, cols)
            if r["supported"]:
                best_supported = True
                best_missing = []
                break
            if not best_missing or len(r["missing"]) < len(best_missing):
                best_missing = r["missing"]

        scenarios.append(
            {
                "handler": handler,
                "name": c.get("name", handler),
                "description": c.get("description", ""),
                "required_fields": required,
                "optional_fields": c.get("optional_fields", []),
                "field_labels": c.get("field_labels", {}),
                "supported": best_supported,
                "mapping": {},
                "missing": best_missing,
            }
        )

    return {
        "file_count": len(files),
        "detected_columns": all_columns[0] if all_columns else [],
        "scenarios": scenarios,
    }


# ============================================================
# 执行：接收多个文件，逐个执行
# ============================================================
@router.post("/api/workspace/process")
async def process(
    files: List[UploadFile] = File(...),
    handlers: str = Form(...),
) -> Dict[str, Any]:
    try:
        selected: List[str] = json.loads(handlers)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"handlers 不是合法 JSON：{e}") from e

    if not selected:
        raise HTTPException(400, "至少选择一个场景")
    if not files:
        raise HTTPException(400, "没有上传文件")

    run_id = secrets.token_urlsafe(8)
    run_start = time.time()

    # ---- 保存所有上传文件，并读取第一个文件的列名用于字段匹配 ----
    saved_paths: List[str] = []
    first_columns: List[str] = []

    for idx, uf in enumerate(files):
        if not uf.filename.endswith(".csv"):
            raise HTTPException(400, f"仅支持 CSV 文件：{uf.filename}")
        content = await uf.read()
        path = UPLOAD_DIR / f"{run_id}_{idx}_{uf.filename}"
        with open(path, "wb") as f:
            f.write(content)
        saved_paths.append(str(path))
        if idx == 0:
            first_columns = _read_columns(content)

    # ---- 配置 ----
    cfg = get_config()
    cfg["paths"]["data_dir"] = str(REPO_ROOT / "data")
    cfg["paths"]["output_dir"] = str(RESULT_DIR)
    cfg["paths"]["log_dir"] = str(REPO_ROOT / "output" / "logs")

    mapper = get_mapper()
    results = []

    for handler_name in selected:
        contract = mapper.get_contract(handler_name)
        if contract is None:
            results.append(
                {
                    "handler": handler_name,
                    "status": "error",
                    "message": f"未在 scenario_contracts.yaml 声明：{handler_name}",
                }
            )
            continue

        # 字段评估
        try:
            func = get_scenario(handler_name)

            # ★ 逐个文件评估，找出"匹配本场景字段"的文件
            entity = contract["entity"]
            required = contract.get("required_fields", [])
            matched_files = []
            matched_eval = None
            best_missing = None

            for path in saved_paths:
                try:
                    cols = _read_columns(Path(path).read_bytes())                    
                    r = mapper.evaluate_contract(entity, required, cols)                    
                    if r["supported"]:
                        matched_files.append(path)
                        if matched_eval is None:
                            matched_eval = r  
                    else:
                        # 记录"最接近匹配"的错误（缺字段最少）
                        if best_missing is None or len(r["missing"]) < len(
                            best_missing
                        ):
                            best_missing = r["missing"]                
                except Exception as e:                    
                    continue

            # 没有任何文件匹配 → 报错（用最接近的缺字段信息）
            if not matched_files:
                results.append(
                    {
                        "handler": handler_name,
                        "status": "error",
                        "message": f"上传文件缺少业务字段：{best_missing or required}",
                    }
                )
                continue

            # 特殊场景（多文件）：传所有文件；普通场景：只传匹配的文件
            if "required_files" in contract:
                target_files = saved_paths
            else:
                target_files = matched_files

            params = {
                "field_mapping": matched_eval["mapping"] if matched_eval else {},
                "field_labels": contract.get("field_labels", {}),
                "input_files": target_files,
                "input_path": target_files[0],
            }
            df = func(cfg, params)

            # 记录本次运行的产物
            candidates = [
                p for p in RESULT_DIR.glob("*.csv") if p.stat().st_mtime >= run_start
            ]
            candidates.sort(key=lambda p: p.stat().st_mtime)

            if not candidates:
                results.append(
                    {
                        "handler": handler_name,
                        "status": "error",
                        "message": "本次运行未产生输出文件",
                    }
                )
                continue

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            cn_name_base = contract.get("name", handler_name)
            output_files = (
                df.attrs.get("output_files") if df is not None else None
            ) or []

            if output_files:
                downloads = []
                for fname, alias in output_files:
                    if (RESULT_DIR / fname).exists():
                        cn = f"{cn_name_base}_{alias}_{ts}.csv"
                        downloads.append(
                            {
                                "download_token": fname,
                                "download_name": cn,
                                "download_url": (
                                    f"/api/workspace/download/{fname}"
                                    f"?as_name={quote(cn)}"
                                ),
                            }
                        )
                results.append(
                    {
                        "handler": handler_name,
                        "status": "success",
                        "rows": int(len(df)) if df is not None else 0,
                        "downloads": downloads,
                    }
                )
            else:
                latest = candidates[-1]
                cn_download_name = f"{cn_name_base}_{ts}.csv"
                results.append(
                    {
                        "handler": handler_name,
                        "status": "success",
                        "rows": int(len(df)) if df is not None else 0,
                        "download_token": latest.name,
                        "download_name": cn_download_name,
                        "download_url": (
                            f"/api/workspace/download/{latest.name}"
                            f"?as_name={quote(cn_download_name)}"
                        ),
                    }
                )
        except CrossBorderAIError as e:
            results.append(
                {"handler": handler_name, "status": "error", "message": str(e)}
            )
        except Exception as e:
            results.append(
                {
                    "handler": handler_name,
                    "status": "error",
                    "message": f"{type(e).__name__}: {e}",
                }
            )

    return {
        "run_id": run_id,
        "uploaded": [p.split("/")[-1].split("\\")[-1] for p in saved_paths],
        "results": results,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }


# ============================================================
# 下载结果文件
# ============================================================
@router.get("/api/workspace/download/{filename}")
def download(filename: str, as_name: str | None = None) -> FileResponse:
    path = RESULT_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "文件不存在")
    if path.resolve().parent != RESULT_DIR.resolve():
        raise HTTPException(400, "非法路径")

    download_name = unquote(as_name) if as_name else filename
    if not download_name.endswith(".csv"):
        download_name += ".csv"

    return FileResponse(
        path,
        filename=download_name,
        media_type="text/csv",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


# ============================================================
# 上传前能力预览
# ============================================================
@router.get("/api/workspace/capabilities")
def capabilities() -> Dict[str, Any]:
    mapper = get_mapper()
    return {
        "scenarios": [
            {
                "handler": c["handler"],
                "name": c.get("name", c["handler"]),
                "description": c.get("description", ""),
                "required_fields": c.get("required_fields", []),
                "optional_fields": c.get("optional_fields", []),
                "field_labels": c.get("field_labels", {}),
            }
            for c in mapper.contracts
        ]
    }


# ============================================================
# 示例文件下载
# ============================================================
# 示例文件映射：(磁盘文件名, 用户下载时看到的名字)
SAMPLE_MAP = {
    "order": ("order_sample_订单示例.csv", "订单明细示例.csv"),
    "material": ("material_素材列表.csv", "素材列表示例.csv"),
    "listing": ("listing_商品列表.csv", "Listing示例.csv"),
    "inventory": ("inventory_库存表.csv", "库存表示例.csv"),
    "ad": ("ad_performance_广告活动.csv", "广告报表示例.csv"),
}


@router.get("/api/workspace/sample/{name}")
def download_sample(name: str) -> FileResponse:
    if name not in SAMPLE_MAP:
        raise HTTPException(404, "示例不存在")

    # SAMPLE_MAP[name] 现在是 (磁盘名, 下载名) 元组
    disk_name, download_name = SAMPLE_MAP[name]
    path = REPO_ROOT / "data" / disk_name

    if not path.exists():
        raise HTTPException(404, f"示例文件未部署：{disk_name}")

    return FileResponse(
        path,
        filename=download_name,  # ★ 用中文下载名
        media_type="text/csv",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
