"""FastAPI 入口：把 Python 内核暴露为 HTTP API，供 Coze / Web 调用。"""
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from .routers import admin, files, health, scenarios, workspace

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

app = FastAPI(
    title="Cross-Border AI Data Site API",
    version="2.0.0",
    description="跨境电商 AI 数据站点内核 API",
)


@app.middleware("http")
async def admin_auth(request: Request, call_next):
    """只对 /admin 与 /api/admin 鉴权。设置 ADMIN_TOKEN 环境变量后生效。"""
    if request.url.path.startswith(("/admin", "/api/admin")):
        if ADMIN_TOKEN and request.headers.get("X-Admin-Token") != ADMIN_TOKEN:
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
    return await call_next(request)


# ---- 业务 API ----
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(scenarios.router, prefix="/api", tags=["scenarios"])
app.include_router(files.router, prefix="/api", tags=["files"])

# ---- 管理后台（配置面板） ----
app.include_router(admin.router, tags=["admin"])

# ---- 业务工作台（上传 → 处理 → 下载） ----
app.include_router(workspace.router, tags=["workspace"])


# ---- 页面路由 ----
@app.get("/app", include_in_schema=False, response_class=FileResponse)
def workspace_page() -> FileResponse:
    page = Path(__file__).resolve().parent / "static" / "app_v2.html"
    return FileResponse(
        page,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )