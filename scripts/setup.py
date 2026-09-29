"""跨平台环境安装入口。用法：python scripts/setup.py"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    req = REPO_ROOT / "requirements.txt"
    if not req.exists():
        print(f"❌ 未找到 {req}")
        sys.exit(1)
    print(f"📦 安装依赖：{req}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req)])
    print("✅ 依赖安装完成")


if __name__ == "__main__":
    main()