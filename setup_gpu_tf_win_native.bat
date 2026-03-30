@echo off
chcp 65001 >nul
setlocal

set "ENV_NAME=scen_main_tf_gpu310"
set "ROOT_DIR=%~dp0"
set "CONDA_EXE="
set "CONDA_BAT="
set "CONDA_ROOT="
set "ENV_PATH="
set "ENV_PYTHON="
set "LOG_FILE=%ROOT_DIR%gpu_env_setup.log"
if not defined CONDA_FORGE_CHANNEL set "CONDA_FORGE_CHANNEL=conda-forge"
if not defined CONDA_REMOTE_CONNECT_TIMEOUT_SECS set "CONDA_REMOTE_CONNECT_TIMEOUT_SECS=30"
if not defined CONDA_REMOTE_READ_TIMEOUT_SECS set "CONDA_REMOTE_READ_TIMEOUT_SECS=120"
if not defined PIP_DEFAULT_TIMEOUT set "PIP_DEFAULT_TIMEOUT=120"
set "CUDA_SHARED_BIN=D:\IDE\miniconda3\pkgs\cudatoolkit-11.2.2-h7d7167e_13\Library\bin"
set "CUDA_SHARED_DLLS=D:\IDE\miniconda3\pkgs\cudatoolkit-11.2.2-h7d7167e_13\DLLs"
set "CUDNN_SHARED_BIN=D:\IDE\miniconda3\pkgs\cudnn-8.1.0.77-h3e0f4f4_0\Library\bin"
set "USE_SHARED_CUDA_RUNTIME=0"

if exist "D:\IDE\miniconda3\Scripts\conda.exe" set "CONDA_EXE=D:\IDE\miniconda3\Scripts\conda.exe"
if not defined CONDA_EXE if exist "%USERPROFILE%\miniconda3\Scripts\conda.exe" set "CONDA_EXE=%USERPROFILE%\miniconda3\Scripts\conda.exe"
if not defined CONDA_EXE if exist "%USERPROFILE%\anaconda3\Scripts\conda.exe" set "CONDA_EXE=%USERPROFILE%\anaconda3\Scripts\conda.exe"
if not defined CONDA_EXE where conda.exe >nul 2>nul
if not defined CONDA_EXE if not errorlevel 1 for /f "delims=" %%I in ('where conda.exe') do if not defined CONDA_EXE set "CONDA_EXE=%%I"

if exist "D:\IDE\miniconda3\condabin\conda.bat" set "CONDA_BAT=D:\IDE\miniconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%USERPROFILE%\miniconda3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\miniconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%USERPROFILE%\anaconda3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\anaconda3\condabin\conda.bat"
if not defined CONDA_BAT where conda >nul 2>nul
if not defined CONDA_BAT if not errorlevel 1 set "CONDA_BAT=conda"

if exist "D:\IDE\miniconda3\envs" set "CONDA_ROOT=D:\IDE\miniconda3"
if not defined CONDA_ROOT if exist "%USERPROFILE%\miniconda3\envs" set "CONDA_ROOT=%USERPROFILE%\miniconda3"
if not defined CONDA_ROOT if exist "%USERPROFILE%\anaconda3\envs" set "CONDA_ROOT=%USERPROFILE%\anaconda3"
if not defined CONDA_ROOT if defined CONDA_EXE (
    for %%I in ("%CONDA_EXE%") do set "CONDA_SCRIPTS_DIR=%%~dpI"
    for %%I in ("%CONDA_SCRIPTS_DIR%..") do set "CONDA_ROOT=%%~fI"
)
if not defined CONDA_ROOT if defined CONDA_BAT (
    for %%I in ("%CONDA_BAT%") do set "CONDA_CONDABIN_DIR=%%~dpI"
    for %%I in ("%CONDA_CONDABIN_DIR%..") do set "CONDA_ROOT=%%~fI"
)

if not defined CONDA_ROOT (
    echo [错误] 未找到 conda，请先安装 Miniconda/Anaconda 并确保 conda 可用
    echo [提示] 本脚本用于方案 1：Windows 原生 GPU TensorFlow 环境
    exit /b 1
)

set "ENV_PATH=%CONDA_ROOT%\envs\%ENV_NAME%"
set "ENV_PYTHON=%ENV_PATH%\python.exe"

if exist "%CUDA_SHARED_BIN%\cudart64_110.dll" if exist "%CUDNN_SHARED_BIN%\cudnn64_8.dll" (
    set "USE_SHARED_CUDA_RUNTIME=1"
)

> "%LOG_FILE%" echo [START] %date% %time%
>> "%LOG_FILE%" echo [INFO] setup_gpu_tf_win_native.bat

echo ========================================
echo   方案 1 - Windows 原生 GPU TensorFlow
echo ========================================
echo 环境名: %ENV_NAME%
echo 环境目录: %ENV_PATH%
echo 项目目录: %ROOT_DIR%
echo conda-forge 源: %CONDA_FORGE_CHANNEL%
if defined PIP_INDEX_URL echo pip 源: %PIP_INDEX_URL%
echo 超时设置: connect=%CONDA_REMOTE_CONNECT_TIMEOUT_SECS%s, read=%CONDA_REMOTE_READ_TIMEOUT_SECS%s
echo 日志文件: %LOG_FILE%
echo.
echo 前提条件:
echo 1. 已安装 NVIDIA 显卡驱动
echo 2. 计划使用 Python 3.10
echo 3. TensorFlow 2.10 GPU 只支持 Windows 原生旧方案
echo.

set "REBUILD_ENV=0"
if exist "%ENV_PYTHON%" (
    "%ENV_PYTHON%" --version >nul 2>nul
    if errorlevel 1 set "REBUILD_ENV=1"
) else (
    set "REBUILD_ENV=1"
)

if "%REBUILD_ENV%"=="1" (
    if exist "%ENV_PATH%" (
        echo [提示] 检测到残缺环境，正在清理后重建...
        rmdir /s /q "%ENV_PATH%"
    )
    echo [1/5] 创建 Python 3.10 环境...
    echo [提示] 首次创建环境可能需要几分钟
    >> "%LOG_FILE%" echo [STEP] create env
    call :run_conda create -y -n %ENV_NAME% --override-channels -c "%CONDA_FORGE_CHANNEL%" python=3.10 pip
    if errorlevel 1 goto :error
) else (
    echo [1/5] 检测到现有环境，继续复用...
    >> "%LOG_FILE%" echo [STEP] reuse env
)

echo [2/5] 准备 CUDA 11.2 / cuDNN 8.1 运行库...
if "%USE_SHARED_CUDA_RUNTIME%"=="1" (
    echo [提示] 已发现共享运行库，跳过 conda 安装：
    echo        %CUDA_SHARED_BIN%
    echo        %CUDNN_SHARED_BIN%
    >> "%LOG_FILE%" echo [STEP] reuse shared CUDA runtime
) else (
    echo [提示] 未发现共享运行库，开始通过 conda 下载
    >> "%LOG_FILE%" echo [STEP] install cudatoolkit cudnn
    call :run_conda install -y -n %ENV_NAME% --override-channels -c "%CONDA_FORGE_CHANNEL%" cudatoolkit=11.2 cudnn=8.1.0
    if errorlevel 1 goto :error
)

echo [3/5] 升级 pip...
>> "%LOG_FILE%" echo [STEP] upgrade pip
call :prepare_cuda_runtime
"%ENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [4/5] 安装 GPU 版 Python 依赖...
echo [提示] TensorFlow 2.10 安装阶段可能持续数分钟
>> "%LOG_FILE%" echo [STEP] pip install requirements-gpu-win-py310.txt
call :prepare_cuda_runtime
"%ENV_PYTHON%" -m pip install -r "%ROOT_DIR%requirements-gpu-win-py310.txt"
if errorlevel 1 goto :error

echo [5/5] 验证 TensorFlow GPU 设备...
>> "%LOG_FILE%" echo [STEP] verify tensorflow gpu
call :prepare_cuda_runtime
"%ENV_PYTHON%" "%ROOT_DIR%check_tensorflow_runtime.py" --require-gpu
if errorlevel 1 (
    echo.
    echo [警告] 依赖已安装，但 TensorFlow 还没有识别到 GPU
    echo [提示] 请检查 NVIDIA 驱动、CUDA/cuDNN 安装状态，以及当前显卡是否支持 CUDA
    echo [提示] 详细日志见: %LOG_FILE%
    exit /b 1
)

echo.
echo [完成] GPU 环境已准备就绪
if "%USE_SHARED_CUDA_RUNTIME%"=="1" (
    echo [提示] 当前使用共享 CUDA 运行库模式
)
echo [运行] 请使用 run_gpu_tf_win_native.bat 启动程序
echo.
exit /b 0

:prepare_cuda_runtime
if "%USE_SHARED_CUDA_RUNTIME%"=="1" (
    set "PATH=%CUDA_SHARED_BIN%;%CUDNN_SHARED_BIN%;%CUDA_SHARED_DLLS%;%PATH%"
)
exit /b 0

:error
echo.
echo [错误] GPU 环境安装失败
echo [提示] 详细日志见: %LOG_FILE%
exit /b 1

:run_conda
if defined CONDA_EXE (
    "%CONDA_EXE%" %*
) else (
    call "%CONDA_BAT%" %*
)
exit /b %errorlevel%
