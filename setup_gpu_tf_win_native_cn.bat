@echo off
chcp 65001 >nul
setlocal

set "CONDA_FORGE_CHANNEL=https://mirrors.ustc.edu.cn/anaconda/cloud/conda-forge"
set "PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple"
set "PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn"
cmd /c setup_gpu_tf_win_native.bat
