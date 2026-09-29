"""统一运行入口。用法：python scripts/run.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cross_border_ai.config_loader import load_config
from cross_border_ai.pipeline import run_pipeline


def main() -> None:
    cfg = load_config()
    results = run_pipeline(cfg)
    print("\n==== 执行结果 ====")
    for name, status in results.items():
        icon = "✅" if status == "success" else ("⏭️" if status == "disabled" else "❌")
        print(f"  {icon} {name}: {status}")


if __name__ == "__main__":
    main()