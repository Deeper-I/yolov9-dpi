# README

## Linux

### 1. Create and activate a Conda environment
First, create a Conda environment with Python 3.8, then activate it.

```bash
conda create -n {env_name} python=3.8
conda activate {env_name}
```

### 2. Install required packages
Run the install script, then install the required Python packages.

```bash
./install
pip install -r requirements.txt
```

### 3. Prepare the optional files and run the compile setup
Move to the `yolov9-dpi` directory, download the required `.out` files, place them in the `optional` folder, and then run the setup script.

```bash
./setup_compile
```

For instructions on downloading the `.out` files, refer to the **Important note** section in the GitHub repository:
`https://github.com/Deeper-I/yolov9-dpi`

---

## Windows

### 1. Create and activate a Conda environment
Create the environment using `environment_gui.yml`, then activate it.

```bash
conda env create -f environment_gui.yml
conda activate yolov9_dpi
```

### 2. Install required packages
Install the required Python packages.

```bash
pip install -r requirements.txt
```

### 3. Prepare the optional files and run the compile setup
Move to the `yolov9-dpi` directory, download the required `.exe` files, place them in the `optional` folder, and then run the Python setup script.

```bash
python setup_compile.py
```

For instructions on downloading the `.exe` files, refer to the **Important note** section in the GitHub repository:
`https://github.com/Deeper-I/yolov9-dpi`

