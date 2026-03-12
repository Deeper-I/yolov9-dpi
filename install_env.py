"""
install.py — Cross-platform environment setup
==============================================
Usage:
  python install_env.py

Project structure:
  yolov9-dpi/
  ├── install_env.py
  └── env_setup/
      ├── linux/
      │   ├── install
      │   ├── setup_compile
      │   └── requirements.txt
      └── window/
          ├── environment_gui.yml   (contains: name: yolov9_dpi)
          ├── setup_compile.py
          └── requirements.txt
"""

import subprocess
import sys
import platform
import shutil
import re
from pathlib import Path

OS       = platform.system()   # "Linux" or "Windows"
ROOT     = Path(__file__).parent.resolve()
LINUX_DIR  = ROOT / "env_setup" / "linux"
WINDOW_DIR = ROOT / "env_setup" / "window"

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
CONDA = None  # check_conda() 에서 설정

def run(cmd, desc="", check=True, cwd=None):
    print(f"\n▶ {desc or ' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, check=check, cwd=cwd)
    return result.returncode == 0


def conda_run(env_name, cmd, desc="", cwd=None, check=True):
    full_cmd = [CONDA, "run", "--no-capture-output", "-n", env_name] + cmd
    return run(full_cmd, desc=desc, cwd=cwd, check=check)


def find_conda():
    """Windows/Linux 모두에서 conda 실행 경로 찾기"""
    import os

    # Linux/Mac: bin/conda 우선 탐색
    if OS != "Windows":
        candidates = []
        for base in [os.environ.get("HOME", ""), "/opt"]:
            for sub in ["anaconda3", "miniconda3", "anaconda", "miniconda"]:
                candidates.append(Path(base) / sub / "bin" / "conda")
        for p in candidates:
            if p.exists():
                return str(p)

    # PATH 에서 찾기
    conda = shutil.which("conda") or shutil.which("conda.bat")
    if conda:
        return conda

    # Windows 기본 설치 경로 탐색
    if OS == "Windows":
        candidates = []
        for base in [os.environ.get("USERPROFILE", ""), "C:\\", "D:\\"]:
            for sub in ["anaconda3", "miniconda3", "Anaconda3", "Miniconda3"]:
                candidates.append(Path(base) / sub / "Scripts" / "conda.bat")
                candidates.append(Path(base) / sub / "condabin" / "conda.bat")
        for p in candidates:
            if p.exists():
                return str(p)

    return None


def check_conda():
    global CONDA
    conda = find_conda()
    if conda is None:
        print("❌ conda not found. Please install Anaconda or Miniconda first.")
        print("   https://docs.conda.io/en/latest/miniconda.html")
        sys.exit(1)
    CONDA = conda
    print(f"✅ conda found: {CONDA}")


def env_exists(env_name):
    result = subprocess.run(
        [CONDA, "env", "list"], capture_output=True, text=True
    )
    return env_name in result.stdout


def get_env_name_from_yml(yml_path):
    """environment_gui.yml 에서 name: xxx 파싱"""
    text = Path(yml_path).read_text(encoding="utf-8")
    match = re.search(r"^name:\s*(\S+)", text, re.MULTILINE)
    if match:
        return match.group(1)
    return None


# ─────────────────────────────────────────────
# Linux install
# ─────────────────────────────────────────────
def install_linux(env_name):
    print("\n[Linux] Starting installation...")

    install_script = LINUX_DIR / "install"
    setup_script   = LINUX_DIR / "setup_compile"
    requirements   = LINUX_DIR / "requirements.txt"

    for f in [install_script, setup_script]:
        if not f.exists():
            print(f"❌ Not found: {f}")
            sys.exit(1)
        f.chmod(0o755)

    conda_run(env_name, ["bash", str(install_script)],
              desc=f"Running {install_script}", cwd=LINUX_DIR)

    if requirements.exists():
        conda_run(env_name, ["pip", "install", "-r", str(requirements)],
                  desc="pip install -r requirements.txt")
    else:
        print(f"  ⚠ requirements.txt not found — skipping ({requirements})")

    conda_run(env_name,
              ["bash", "-c", f"bash {str(setup_script)} ; exit 0"],
              desc=f"Running {setup_script}", cwd=LINUX_DIR)


# ─────────────────────────────────────────────
# Windows install
# ─────────────────────────────────────────────
def install_windows(env_name):
    print("\n[Windows] Starting installation...")

    yml          = WINDOW_DIR / "environment_gui.yml"
    setup_script = WINDOW_DIR / "setup_compile.py"
    requirements = WINDOW_DIR / "requirements.txt"

    for f in [yml, setup_script]:
        if not f.exists():
            print(f"❌ Not found: {f}")
            sys.exit(1)

    run([CONDA, "env", "update", "-n", env_name, "-f", str(yml)],
        desc="conda env update -f environment_gui.yml")

    if requirements.exists():
        conda_run(env_name, ["pip", "install", "-r", str(requirements)],
                  desc="pip install -r requirements.txt")
    else:
        print(f"  ⚠ requirements.txt not found — skipping ({requirements})")

    conda_run(env_name, ["python", str(setup_script)],
              desc=f"Running {setup_script}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  BSNet Eval — Environment Installer")
    print(f"  Platform : {OS}")
    print("=" * 55)

    check_conda()

    # env 이름 결정
    if OS == "Windows":
        yml_path = WINDOW_DIR / "environment_gui.yml"
        yml_env  = get_env_name_from_yml(yml_path) if yml_path.exists() else None
        if yml_env:
            print(f"\n  environment_gui.yml env name: '{yml_env}'")
            ans = input(f"  Use '{yml_env}' as env name? (y/n): ").strip().lower()
            env_name = yml_env if ans == "y" else input("  Enter env name: ").strip()
        else:
            env_name = input("\nEnter conda environment name: ").strip()
    else:
        env_name = input("\nEnter conda environment name: ").strip()

    if not env_name:
        print("❌ Environment name cannot be empty")
        sys.exit(1)

    # 이미 존재하면 확인
    if env_exists(env_name):
        ans = input(f"\n  ⚠ Environment '{env_name}' already exists. Recreate? (y/n): ").strip().lower()
        if ans == "y":
            run([CONDA, "env", "remove", "-n", env_name, "-y"],
                desc=f"Removing existing env: {env_name}")
        else:
            print(f"\n✅ Using existing environment '{env_name}'")
            print(f"\nTo get started:")
            print(f"  conda activate {env_name}")
            return

    # conda env create
    run([CONDA, "create", "-n", env_name, "python=3.8", "-y"],
        desc=f"Creating conda env: {env_name} (python=3.8)")

    # OS 분기
    if OS == "Linux":
        install_linux(env_name)
    elif OS == "Windows":
        install_windows(env_name)
    else:
        print(f"❌ Unsupported OS: {OS}")
        sys.exit(1)

    # 완료
    print("\n" + "=" * 55)
    print("✅ Installation complete!")
    print(f"\nTo get started:")
    print(f"  conda activate {env_name}")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()
