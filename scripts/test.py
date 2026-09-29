"""跨平台测试入口。用法：python scripts/test.py"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    print("🧪 运行测试…")
    result = subprocess.call([sys.executable, "-m", "pytest"], cwd=str(REPO_ROOT))
    sys.exit(result)


if __name__ == "__main__":
    main()