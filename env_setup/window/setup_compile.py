#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_compile_win.py

Windows equivalent of the Linux setup_compile script.
Uses copy instead of cp/ln -s so the compile pipeline (compile_win.py) can run on Windows.

Run from the repository root (folder containing TACHY-Compiler/, models/, utils/):
    python setup_compile.py

Optional:
    python setup_compile.py --force   # overwrite existing models_compile, yolov9/utils, yolov9/models
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Windows setup for TACHY compile (replaces Linux setup_compile cp/ln with copy)."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing models_compile, yolov9/utils, yolov9/models",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Less output",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    if not (repo_root / "TACHY-Compiler").is_dir():
        print("[ERROR] TACHY-Compiler not found. Run this script from the repo root.")
        return 2
    if not (repo_root / "models").is_dir():
        print("[ERROR] models/ not found. Run this script from the repo root.")
        return 2
    if not (repo_root / "utils").is_dir():
        print("[ERROR] utils/ not found. Run this script from the repo root.")
        return 2

    def log(msg: str) -> None:
        if not args.quiet:
            print(msg)

    def _remove_if_exists(p: Path) -> None:
        """Remove path so we can put a real folder there. Handles file (e.g. symlink) or dir."""
        if not p.exists():
            return
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()

    # 1) models -> models_compile
    models = repo_root / "models"
    models_compile = repo_root / "models_compile"
    if models_compile.exists() and not args.force:
        log("[SKIP] models_compile already exists (use --force to overwrite)")
    else:
        if models_compile.exists():
            shutil.rmtree(models_compile)
        shutil.copytree(models, models_compile)
        log("[OK] Copied models -> models_compile")

    # 2) models_compile/yolo_compile.py -> models_compile/yolo.py
    yolo_compile = models_compile / "yolo_compile.py"
    yolo_py = models_compile / "yolo.py"
    if not yolo_compile.exists():
        print("[ERROR] models_compile/yolo_compile.py not found.")
        return 2
    shutil.copy2(yolo_compile, yolo_py)
    log("[OK] Copied yolo_compile.py -> yolo.py in models_compile")

    # 3) repo utils -> TACHY-Compiler/platform_converter/utils/yolov9/utils (real folder)
    yolov9 = repo_root / "TACHY-Compiler" / "platform_converter" / "utils" / "yolov9"
    yolov9_utils = yolov9 / "utils"
    _remove_if_exists(yolov9_utils)
    shutil.copytree(repo_root / "utils", yolov9_utils)
    log("[OK] Copied repo utils -> TACHY-Compiler/.../yolov9/utils")

    # 4) repo models_compile -> TACHY-Compiler/platform_converter/utils/yolov9/models (real folder)
    yolov9_models = yolov9 / "models"
    _remove_if_exists(yolov9_models)
    shutil.copytree(models_compile, yolov9_models)
    log("[OK] Copied models_compile -> TACHY-Compiler/.../yolov9/models")

    # 5) optional/block_4bit.* and optional/fc.* -> TACHY-Compiler/compiler/utils/
    optional = repo_root / "optional"
    compiler_utils = repo_root / "TACHY-Compiler" / "compiler" / "utils"
    # On Windows we need .exe; on Linux .out (tachy_block.py chooses by sys.platform).
    ext = ".exe" if sys.platform == "win32" else ".out"
    bin_names = ("block_4bit", "fc")
    for name in bin_names:
        src = optional / f"{name}{ext}"
        if not src.exists():
            print(f"[WARN] optional/{name}{ext} not found.")
            print("       Put block_4bit and fc binaries in optional/ and run again.")
            print("       compile_win.py will fail at tachy_block until these exist in compiler/utils.")
            continue
        dst = compiler_utils / f"{name}{ext}"
        shutil.copy2(src, dst)
        log(f"[OK] Copied optional/{name}{ext} -> compiler/utils/")

    log("[DONE] setup_compile_win finished. You can run: python compile.py -v")
    return 0


if __name__ == "__main__":
    sys.exit(main())
