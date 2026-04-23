from __future__ import annotations

import sys
from pathlib import Path
import site


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    vendor_path = repo_root / ".vendor"
    deps_path = repo_root / ".deps"
    src_path = repo_root / "src"
    user_site = site.getusersitepackages()
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    if str(vendor_path) not in sys.path:
        sys.path.insert(1, str(vendor_path))
    if user_site and user_site not in sys.path:
        sys.path.append(user_site)
    if str(deps_path) not in sys.path:
        sys.path.append(str(deps_path))

    from cfb_rankings.cli import main as cli_main

    cli_main()
if __name__ == "__main__":
    main()
