#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLOv9 -> TACHY compile pipeline (Windows v2).

``compile_linux.py`` 와 동일: PyPI ``tachy_compiler`` 를 ``python -m`` 으로 호출.

기존 ``compile_windows.py``(로컬 TACHY-Compiler 경로)는 건드리지 않고 이 파일만 사용.

실행 위치와 무관하게, 스크립트가 있는 ``compile/`` 폴더로 ``chdir`` 하여
``../runs/train/...``, ``./optional/...`` 경로가 Linux 스크립트와 같게 동작한다.
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
import time
from pathlib import Path


#######################################################
################### User Settings #####################
#######################################################
PRE_PARAM_DIR = "../runs/train/bsnet-t6/weights"
OPT_PARAM_DIR = "../runs/train/bsnet-t-op6/weights"
# OPT_PARAM_DIR = "../runs/train/bsnet-t-op/weights"

ONNX_INPUT_SHAPE = "1 3 256 416"  # (B,C,H,W)
TACHY_INPUT_SHAPE = "1 256 416 3"  # (B,H,W,C)
#######################################################

#######################################################
TRAIN_FILE_TYPE = "pt_yolov9"
ONNX_FILE_TYPE = "pt2onnx"

SRC_PRE_PATH = os.path.join(PRE_PARAM_DIR, "best.pt")
SRC_OPT_PATH = os.path.join(OPT_PARAM_DIR, "best.pt")

WORK_DIR = datetime.datetime.now().strftime("20%y%m%d_%H%M%S")
TEMP_DIR = os.path.join(WORK_DIR, "temp")
DST_EVAL_PATH = os.path.join(WORK_DIR, "eval.pt")
DST_COMP_PATH = os.path.join(WORK_DIR, "comp.pt")
DST_TEMP_PATH = ""

ONNX_EVAL_PATH = os.path.join(WORK_DIR, "eval.onnx")
ONNX_COMP_PATH = os.path.join(WORK_DIR, "comp.onnx")
#######################################################

#######################################################
LAYER_EVAL_PATH = os.path.join(WORK_DIR, "eval.tachy")
LAYER_COMP_PATH = os.path.join(WORK_DIR, "comp.tachy")
BLOCK_EVAL_PATH = os.path.join(WORK_DIR, "eval_block.tachy")
BLOCK_COMP_PATH = os.path.join(WORK_DIR, "comp_block.tachy")

DEFAULT_PAD_MODE = "--default_pad_mode=dynamic"
DEFAULT_PAD_ORDER = "--default_pad_order=up_left"
STRATEGY_GAP = "--strategy_gap=serial"
LOGIT_ORDER = "--logit_order 5 3 0 4 2 1"

FC_OUT = ".\optional\\fc.exe"
XWN_OUT = ".\optional\\block_4bit.exe"
#######################################################

_VERBOSE = False


def _remove_param_bin() -> None:
    p = Path("param.bin")
    if p.is_file():
        try:
            p.unlink()
            if _VERBOSE:
                print(f"[INFO] Removed {p.resolve()}")
        except OSError as e:
            print(f"[WARN] Could not remove {p}: {e}")


if __name__ == "__main__":
    _compile_dir = Path(__file__).resolve().parent
    os.chdir(_compile_dir)

    _remove_param_bin()
    env = os.environ.copy()

    if not os.path.isdir(WORK_DIR):
        os.mkdir(WORK_DIR)
        os.mkdir(TEMP_DIR)
    else:
        time.sleep(1)
        WORK_DIR = datetime.datetime.now().strftime("20%y%m%d_%H%M%S")
        TEMP_DIR = os.path.join(WORK_DIR, "temp")
        os.mkdir(WORK_DIR)
        os.mkdir(TEMP_DIR)

    DST_EVAL_PATH = os.path.join(WORK_DIR, "eval.pt")
    DST_COMP_PATH = os.path.join(WORK_DIR, "comp.pt")
    ONNX_EVAL_PATH = os.path.join(WORK_DIR, "eval.onnx")
    ONNX_COMP_PATH = os.path.join(WORK_DIR, "comp.onnx")
    LAYER_EVAL_PATH = os.path.join(WORK_DIR, "eval.tachy")
    LAYER_COMP_PATH = os.path.join(WORK_DIR, "comp.tachy")
    BLOCK_EVAL_PATH = os.path.join(WORK_DIR, "eval_block.tachy")
    BLOCK_COMP_PATH = os.path.join(WORK_DIR, "comp_block.tachy")

    print(f"[INFO]: {WORK_DIR} is created.")

    # Deploy
    deploy_mod = f"tachy_compiler.platform_converter.utils.yolov9.deploy_{TRAIN_FILE_TYPE}"
    deploy_cmd = [
        sys.executable,
        "-m",
        deploy_mod,
        SRC_PRE_PATH,
        SRC_OPT_PATH,
        DST_EVAL_PATH,
        DST_COMP_PATH,
        f"--DST_TEMP_PATH={DST_TEMP_PATH}",
    ]
    if _VERBOSE:
        print(f"[INFO] {' '.join(deploy_cmd)}")
    subprocess.run(deploy_cmd, check=True, env=env)

    # Convert
    convert_mod = f"tachy_compiler.platform_converter.utils.yolov9.convert_{ONNX_FILE_TYPE}"
    convert_eval_cmd = [
        sys.executable,
        "-m",
        convert_mod,
        DST_EVAL_PATH,
        ONNX_EVAL_PATH,
        *ONNX_INPUT_SHAPE.split(),
    ]
    if _VERBOSE:
        print(f"[INFO] {' '.join(convert_eval_cmd)}")
    subprocess.run(convert_eval_cmd, check=True, env=env)

    convert_comp_cmd = [
        sys.executable,
        "-m",
        convert_mod,
        DST_COMP_PATH,
        ONNX_COMP_PATH,
        *ONNX_INPUT_SHAPE.split(),
    ]
    if _VERBOSE:
        print(f"[INFO] {' '.join(convert_comp_cmd)}")
    subprocess.run(convert_comp_cmd, check=True, env=env)

    # Compile - Layer
    tachy_model_cmd = [
        sys.executable,
        "-m",
        "tachy_compiler.compiler.utils.tachy_model",
        ONNX_EVAL_PATH,
        LAYER_EVAL_PATH,
        *TACHY_INPUT_SHAPE.split(),
        DEFAULT_PAD_ORDER,
        DEFAULT_PAD_MODE,
    ]
    if _VERBOSE:
        print(f"[INFO] {' '.join(tachy_model_cmd)}")
    subprocess.run(tachy_model_cmd, check=True, env=env)

    tachy_model_cmd = [
        sys.executable,
        "-m",
        "tachy_compiler.compiler.utils.tachy_model",
        ONNX_COMP_PATH,
        LAYER_COMP_PATH,
        *TACHY_INPUT_SHAPE.split(),
        DEFAULT_PAD_ORDER,
        DEFAULT_PAD_MODE,
    ]
    if _VERBOSE:
        print(f"[INFO] {' '.join(tachy_model_cmd)}")
    subprocess.run(tachy_model_cmd, check=True, env=env)

    # Compile - Block
    tachy_block_cmd = [
        sys.executable,
        "-m",
        "tachy_compiler.compiler.utils.tachy_block",
        LAYER_EVAL_PATH,
        BLOCK_EVAL_PATH,
        *TACHY_INPUT_SHAPE.split(),
        DEFAULT_PAD_ORDER,
        DEFAULT_PAD_MODE,
        *LOGIT_ORDER.split(),
        f"--fc_out={FC_OUT}",
        f"--block_4bit_out={XWN_OUT}",
        f"--work_dir={TEMP_DIR}",
    ]
    if _VERBOSE:
        print(f"[INFO] {' '.join(tachy_block_cmd)}")
    subprocess.run(tachy_block_cmd, check=True, env=env)

    tachy_block_cmd = [
        sys.executable,
        "-m",
        "tachy_compiler.compiler.utils.tachy_block",
        LAYER_COMP_PATH,
        BLOCK_COMP_PATH,
        *TACHY_INPUT_SHAPE.split(),
        DEFAULT_PAD_ORDER,
        DEFAULT_PAD_MODE,
        *LOGIT_ORDER.split(),
        f"--fc_out={FC_OUT}",
        f"--block_4bit_out={XWN_OUT}",
        f"--work_dir={TEMP_DIR}",
        f"--ref_file={LAYER_EVAL_PATH}",
    ]
    if _VERBOSE:
        print(f"[INFO] {' '.join(tachy_block_cmd)}")
    subprocess.run(tachy_block_cmd, check=True, env=env)

    # Compile - Runtime
    compile_rt_cmd = [
        sys.executable,
        "-m",
        "tachy_compiler.compiler.utils.compile_runtime",
        BLOCK_COMP_PATH,
        WORK_DIR,
    ]
    if _VERBOSE:
        print(f"[INFO] {' '.join(compile_rt_cmd)}")
    subprocess.run(compile_rt_cmd, check=True, env=env)
