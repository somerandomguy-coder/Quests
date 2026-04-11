from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"

    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from main import App

    app = App()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
