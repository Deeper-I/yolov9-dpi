#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_compile_v2.py

Windows setup helper for the compile pipeline.

This version is a minimal refactor of env_setup/window/setup_compile.py.
It only copies the local repo `utils/` folder into `compile/utils`.

The old `setup_compile.py` is kept as a reference and is not modified.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Windows setup for TACHY compile (copy repo utils/ into compile/utils)."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing target folder if it already exists.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Less output.",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[1]
    compile_dir = repo_root / "compile"
    src_utils = repo_root / "utils"
    target_utils = compile_dir / "utils"

    if not compile_dir.is_dir():
        print("[ERROR] compile/ folder not found. Run this script from the repo root.")
        return 2
    if not src_utils.is_dir():
        print("[ERROR] repo utils/ not found. Run this script from the repo root.")
        return 2

    def log(message: str) -> None:
        if not args.quiet:
            print(message)

    def remove_path(path: Path) -> None:
        if not path.exists():
            return
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    if target_utils.exists() and not args.force:
        log(f"[SKIP] {target_utils} already exists (use --force to overwrite)")
        print("[DONE] setup_compile finished. Only utils copy is needed.")
        return 0

    if target_utils.exists():
        remove_path(target_utils)

    target_utils.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_utils, target_utils)
    log(f"[OK] Copied repo utils -> {target_utils}")

    print("[DONE] setup_compile finished. Only utils copy is performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
