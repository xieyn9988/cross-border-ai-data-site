"""跨平台 API 启动入口。用法：python scripts/api.py"""
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"


def main() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    print("🚀 启动 API：http://localhost:8000/admin")
    print("   按 Ctrl+C 停止服务")
    subprocess.call(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--reload", "--port", "8000"],
        cwd=str(REPO_ROOT),
        env=env,
    )


if __name__ == "__main__":
    main()