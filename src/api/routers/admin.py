"""业务配置面板 API：让业务人员通过网页读写 scenarios.yaml。"""
import asyncio
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# 基于仓库根目录定位，避免 cwd 依赖
REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = REPO_ROOT / "config"
SCENARIOS_FILE = CONFIG_DIR / "scenarios.yaml"
BACKUP_DIR = CONFIG_DIR / "scenarios.backup"
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

_executor = ThreadPoolExecutor(max_workers=1)
_last_run = {"ts": 0.0}
_RUN_COOLDOWN_SEC = 5


def _load_scenarios() -> Dict[str, Any]:
    if not SCENARIOS_FILE.exists():
        raise HTTPException(500, "scenarios.yaml 不存在")
    with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _backup() -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"scenarios_{ts}.yaml"
    shutil.copy2(SCENARIOS_FILE, target)
    backups = sorted(BACKUP_DIR.glob("scenarios_*.yaml"))
    for old in backups[:-20]:
        old.unlink()
    return target.name


@router.get("/admin", include_in_schema=False)
def admin_page() -> FileResponse:
    page = STATIC_DIR / "admin.html"
    if not page.exists():
        raise HTTPException(500, "admin.html 未部署")
    return FileResponse(page)


@router.get("/api/admin/scenarios")
def get_scenarios() -> Dict[str, Any]:
    return _load_scenarios()


@router.put("/api/admin/scenarios")
def update_scenarios(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "scenarios" not in payload or not isinstance(payload["scenarios"], list):
        raise HTTPException(400, "payload 必须包含 scenarios 数组")

    cleaned = []
    for sc in payload["scenarios"]:
        if not isinstance(sc, dict) or "handler" not in sc:
            raise HTTPException(400, "每个场景必须有 handler")
        cleaned.append({
            "name": sc.get("name", ""),
            "enabled": bool(sc.get("enabled", True)),
            "handler": sc["handler"],
            "description": sc.get("description", ""),
            "params": sc.get("params", {}),
        })

    backup_name = _backup()
    with open(SCENARIOS_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump({"scenarios": cleaned}, f, allow_unicode=True, sort_keys=False)

    return {
        "status": "saved",
        "backup": backup_name,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/api/admin/backups")
def list_backups() -> List[str]:
    if not BACKUP_DIR.exists():
        return []
    return sorted([p.name for p in BACKUP_DIR.glob("scenarios_*.yaml")], reverse=True)


@router.post("/api/admin/restore/{filename}")
def restore_backup(filename: str) -> Dict[str, str]:
    src = BACKUP_DIR / filename
    if not src.exists():
        raise HTTPException(404, "备份不存在")
    _backup()
    shutil.copy2(src, SCENARIOS_FILE)
    return {"status": "restored", "from": filename}


@router.post("/api/admin/run")
async def run_now(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """立即执行 pipeline，返回各场景结果。"""
    now = time.time()
    if now - _last_run["ts"] < _RUN_COOLDOWN_SEC:
        raise HTTPException(429, f"运行过于频繁，请 {_RUN_COOLDOWN_SEC} 秒后再试")
    _last_run["ts"] = now

    from cross_border_ai.config_loader import ensure_dirs, load_config
    from cross_border_ai.pipeline import run_pipeline

    try:
        cfg = load_config()
        ensure_dirs(cfg)
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(_executor, run_pipeline, cfg)
        return {
            "status": "done",
            "results": results,
            "output_dir": cfg["paths"]["output_dir"],
        }
    except Exception as e:
        raise HTTPException(500, f"执行失败：{e}") from e