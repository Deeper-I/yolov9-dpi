#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compile.py

Windows port that mirrors the ORIGINAL linux `compile` script behavior as closely as possible.

Key points (matches original):
- Creates WORK_DIR (timestamp) and TEMP_DIR = WORK_DIR/temp
- deploy -> convert (eval/comp) -> tachy_model (eval/comp)
- tachy_block is run TWICE:
    1) eval.tachy -> eval_block.tachy  (no --ref_file)
    2) comp.tachy -> comp_block.tachy  (--ref_file=eval.tachy)
- compile_runtime runs on comp_block.tachy

Windows fixes:
- INPUT_SHAPE strings are split into separate ints when passing to argparse-based scripts.
- --logit_order is passed as separate tokens: --logit_order 5 3 0 4 2 1
- Adds PYTHONPATH so TACHY-Compiler imports (graph.py under src, etc.) work on Windows.

Run from YOLOv9 repo root (folder containing TACHY-Compiler/):
    python .\compile..py -v

Defaults can be overridden via CLI args.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], verbose: bool, *, cwd: Path, pythonpaths: list[Path] | None = None) -> None:
    if verbose:
        print("[CMD]", " ".join(cmd))
    env = os.environ.copy()
    if pythonpaths:
        env["PYTHONPATH"] = os.pathsep.join(str(p) for p in pythonpaths) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run(cmd, check=True, cwd=str(cwd), env=env)


def _make_unique_workdir(repo_root: Path, name: str) -> Path:
    """
    Original linux script:
      - WORK_DIR = timestamp string
      - if exists, sleep and regenerate
    We'll instead generate a unique suffix immediately if needed.
    """
    base = repo_root / name
    if not base.exists():
        base.mkdir(parents=True, exist_ok=False)
        return base
    for i in range(1, 10_000):
        cand = repo_root / f"{name}_{i}"
        if not cand.exists():
            cand.mkdir(parents=True, exist_ok=False)
            return cand
    raise RuntimeError(f"Could not create unique work dir for base name: {name}")


def main() -> int:
    p = argparse.ArgumentParser(
        description="YOLOv9 -> TACHY compile pipeline (Windows, mirrors original linux compile script)."
    )

    # Match original user settings (but allow override)
    p.add_argument("--pre-param-dir", default="D:/Cursor_AI/OJT/Tachy_GUI/example/yolov9-dpi/runs/train/bsnet-t/weights", help="Directory containing pre best.pt")
    p.add_argument("--opt-param-dir", default="D:/Cursor_AI/OJT/Tachy_GUI/example/yolov9-dpi/runs/train/bsnet-t-o/weights", help="Directory containing opt best.pt")

    p.add_argument("--onnx-input-shape", default="1 3 256 416", help='ONNX input shape (B C H W), e.g. "1 3 256 416"')
    p.add_argument("--tachy-input-shape", default="1 256 416 3", help='TACHY input shape (B H W C), e.g. "1 256 416 3"')

    p.add_argument("--default-pad-mode", default="dynamic", choices=["dynamic", "fixed"], help="default_pad_mode")
    p.add_argument("--default-pad-order", default="up_left", choices=["up_left", "down_right"], help="default_pad_order")

    # Original had STRATEGY_GAP defined, but did not pass it. Keep optional.
    p.add_argument("--strategy-gap", default="", help="Optional strategy_gap value, e.g. serial (passed as --strategy_gap=<value>)")

    # Original logit_order
    p.add_argument("--logit-order-str", default="5 3 0 4 2 1", help="logit_order string, e.g. '5 3 0 4 2 1'")

    # Types
    p.add_argument("--train-file-type", default="pt_yolov9", help="deploy script suffix: deploy_<type>.py")
    p.add_argument("--onnx-file-type", default="pt2onnx", help="convert script suffix: convert_<type>.py")

    p.add_argument("--work-dir", default="", help="Output directory name. Default: timestamp like 20260106_121725")
    p.add_argument("--dst-temp-path", default="", help="Optional DST_TEMP_PATH for deploy script (omit when empty)")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    repo_root = Path.cwd()

    tachy_root = repo_root / "TACHY-Compiler"
    if not tachy_root.exists():
        print("[ERROR] Could not find 'TACHY-Compiler' in current directory.")
        print("        Please 'cd' to the YOLOv9 repo root first.")
        return 2

    # Original script ran `rm -fv param.bin` in repo root.
    # On Windows, remove if present (param.bin or parameter.bin).
    for fname in ("param.bin", "parameter.bin"):
        f = repo_root / fname
        if f.exists():
            try:
                f.unlink()
                if args.verbose:
                    print(f"[INFO] Removed existing {f}")
            except Exception as e:
                print(f"[WARN] Could not remove {f}: {e}")

    # Resolve best.pt inputs (relative like original)
    src_pre_path = repo_root / args.pre_param_dir / "best.pt"
    src_opt_path = repo_root / args.opt_param_dir / "best.pt"
    if not src_pre_path.exists():
        print(f"[ERROR] Missing file: {src_pre_path}")
        return 2
    if not src_opt_path.exists():
        print(f"[ERROR] Missing file: {src_opt_path}")
        return 2

    # Work dir
    if args.work_dir.strip():
        work_name = args.work_dir.strip()
    else:
        work_name = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = _make_unique_workdir(repo_root, work_name)
    temp_dir = work_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Work dir created: {work_dir}")

    # Relative paths like the original compile script
    def rel(pth: Path) -> str:
        try:
            return str(pth.relative_to(repo_root))
        except Exception:
            return str(pth)

    dst_eval_pt = work_dir / "eval.pt"
    dst_comp_pt = work_dir / "comp.pt"
    onnx_eval = work_dir / "eval.onnx"
    onnx_comp = work_dir / "comp.onnx"

    layer_eval = work_dir / "eval.tachy"
    layer_comp = work_dir / "comp.tachy"
    block_eval = work_dir / "eval_block.tachy"
    block_comp = work_dir / "comp_block.tachy"

    # Tokenize shapes for Windows argparse scripts
    onnx_shape_tokens = str(args.onnx_input_shape).replace(",", " ").split()
    tachy_shape_tokens = str(args.tachy_input_shape).replace(",", " ").split()

    # Args as tokens (match how shell splits the original cmd strings)
    default_pad_mode_arg = f"--default_pad_mode={args.default_pad_mode}"
    default_pad_order_arg = f"--default_pad_order={args.default_pad_order}"

    logit_order_tokens = ["--logit_order"] + str(args.logit_order_str).strip().split()

    sg = str(args.strategy_gap).strip()
    strategy_gap_token = [f"--strategy_gap={sg}"] if sg else []  # optional

    # PYTHONPATHs for TACHY-Compiler internal imports
    compiler_dir = (tachy_root / "compiler").resolve()
    utils_dir = (compiler_dir / "utils").resolve()
    candidate_src_dirs = [
        (compiler_dir / "src").resolve(),
        (tachy_root / "src").resolve(),
        (tachy_root / "compiler" / "src").resolve(),
    ]
    tachy_pythonpaths = [repo_root.resolve(), tachy_root.resolve(), compiler_dir, utils_dir] + [pp for pp in candidate_src_dirs if pp.exists()]

    # Absolute paths for tachy_block helpers on Windows (avoid forward-slash parsing in cmd.exe)
    abs_temp_dir = temp_dir.resolve()
    abs_utils_dir = utils_dir.resolve()


    # 1) Deploy
    deploy_script = tachy_root / "platform_converter" / "utils" / "yolov9" / f"deploy_{args.train_file_type}.py"
    if not deploy_script.exists():
        print(f"[ERROR] Missing deploy script: {deploy_script}")
        return 2

    deploy_cmd = [
        sys.executable,
        str(deploy_script),
        rel(src_pre_path),
        rel(src_opt_path),
        rel(dst_eval_pt),
        rel(dst_comp_pt),
    ]
    # In bash, an empty variable expands to nothing (no extra argv). Passing '' on Windows becomes
    # an extra argument and breaks argparse. Only pass DST_TEMP_PATH when non-empty.
    if getattr(args, "dst_temp_path", "").strip():
        deploy_cmd += ["--DST_TEMP_PATH", args.dst_temp_path.strip()]

    _run(
        deploy_cmd,
        args.verbose,
        cwd=repo_root,
        pythonpaths=[repo_root],
    )

# 2) Convert to ONNX (eval + comp)
    convert_script = tachy_root / "platform_converter" / "utils" / "yolov9" / f"convert_{args.onnx_file_type}.py"
    if not convert_script.exists():
        print(f"[ERROR] Missing convert script: {convert_script}")
        return 2

    _run(
        [sys.executable, str(convert_script), rel(dst_eval_pt), rel(onnx_eval), *onnx_shape_tokens],
        args.verbose,
        cwd=repo_root,
        pythonpaths=[repo_root],
    )
    _run(
        [sys.executable, str(convert_script), rel(dst_comp_pt), rel(onnx_comp), *onnx_shape_tokens],
        args.verbose,
        cwd=repo_root,
        pythonpaths=[repo_root],
    )

    # 3) Compile - Layer (tachy_model)
    tachy_model = tachy_root / "compiler" / "utils" / "tachy_model.py"
    if not tachy_model.exists():
        print(f"[ERROR] Missing tachy_model script: {tachy_model}")
        return 2

    _run(
        [sys.executable, str(tachy_model), rel(onnx_eval), rel(layer_eval), *tachy_shape_tokens, default_pad_order_arg, default_pad_mode_arg],
        args.verbose,
        cwd=repo_root,
        pythonpaths=tachy_pythonpaths,
    )
    _run(
        [sys.executable, str(tachy_model), rel(onnx_comp), rel(layer_comp), *tachy_shape_tokens, default_pad_order_arg, default_pad_mode_arg],
        args.verbose,
        cwd=repo_root,
        pythonpaths=tachy_pythonpaths,
    )

    # 4) Compile - Block (tachy_block)  [MIRROR ORIGINAL: run twice]
    tachy_block = tachy_root / "compiler" / "utils" / "tachy_block.py"
    if not tachy_block.exists():
        print(f"[ERROR] Missing tachy_block script: {tachy_block}")
        return 2

    # Match original script_dir argument (relative string)
    script_dir_arg = None  # set later as absolute path tokens
    work_dir_arg = None  # set later as absolute path tokens

    # 4-1) EVAL BLOCK: no --ref_file (same as original)
    _run(
        [
            sys.executable,
            str(tachy_block),
            rel(layer_eval),
            rel(block_eval),
            *tachy_shape_tokens,
            default_pad_order_arg,
            default_pad_mode_arg,
            *logit_order_tokens,
            *strategy_gap_token,
            '--work_dir', str(abs_temp_dir),
            '--script_dir', str(abs_utils_dir),
        ],
        args.verbose,
        cwd=repo_root,
        pythonpaths=tachy_pythonpaths,
    )

    # 4-2) COMP BLOCK: with --ref_file=eval.tachy (same as original)
    _run(
        [
            sys.executable,
            str(tachy_block),
            rel(layer_comp),
            rel(block_comp),
            *tachy_shape_tokens,
            default_pad_order_arg,
            default_pad_mode_arg,
            *logit_order_tokens,
            *strategy_gap_token,
            '--work_dir', str(abs_temp_dir),
            '--script_dir', str(abs_utils_dir),
            '--ref_file', str(layer_eval.resolve()),
        ],
        args.verbose,
        cwd=repo_root,
        pythonpaths=tachy_pythonpaths,
    )

    # 5) Compile - Runtime (compile_runtime) uses COMP BLOCK like original
    compile_runtime = tachy_root / "compiler" / "utils" / "compile_runtime.py"
    if not compile_runtime.exists():
        print(f"[ERROR] Missing compile_runtime script: {compile_runtime}")
        return 2

    _run(
        [sys.executable, str(compile_runtime), rel(block_comp), rel(work_dir)],
        args.verbose,
        cwd=repo_root,
        pythonpaths=tachy_pythonpaths,
    )

    print("[DONE] All steps completed.")
    print(f"[INFO] Outputs under: {work_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
