@echo off
chcp 65001 >nul
setlocal

set "ENV_NAME=scen_main_tf_gpu310"
set "ROOT_DIR=%~dp0"
set "CONDA_ROOT=D:\IDE\miniconda3"
if not exist "%CONDA_ROOT%\envs" if exist "%USERPROFILE%\miniconda3\envs" set "CONDA_ROOT=%USERPROFILE%\miniconda3"
if not exist "%CONDA_ROOT%\envs" if exist "%USERPROFILE%\anaconda3\envs" set "CONDA_ROOT=%USERPROFILE%\anaconda3"
set "ENV_PATH=%CONDA_ROOT%\envs\%ENV_NAME%"
set "ENV_PYTHON=%ENV_PATH%\python.exe"
set "LOG_FILE=%ROOT_DIR%gpu_env_run.log"
set "CUDA_SHARED_BIN=D:\IDE\miniconda3\pkgs\cudatoolkit-11.2.2-h7d7167e_13\Library\bin"
set "CUDA_SHARED_DLLS=D:\IDE\miniconda3\pkgs\cudatoolkit-11.2.2-h7d7167e_13\DLLs"
set "CUDNN_SHARED_BIN=D:\IDE\miniconda3\pkgs\cudnn-8.1.0.77-h3e0f4f4_0\Library\bin"
set "CUDA_CACHE_PATH=%ROOT_DIR%.cuda_cache"
set "CUDA_CACHE_MAXSIZE=2147483647"

if not exist "%ENV_PYTHON%" (
    echo [错误] 未找到 GPU 环境 %ENV_NAME%
    echo [提示] 请先运行 setup_gpu_tf_win_native.bat
    exit /b 1
)

if not exist "%CUDA_CACHE_PATH%" mkdir "%CUDA_CACHE_PATH%"

> "%LOG_FILE%" echo [START] %date% %time%
>> "%LOG_FILE%" echo [INFO] run_gpu_tf_win_native.bat

echo ========================================
echo   使用 GPU TensorFlow 环境启动
echo ========================================
echo 环境名: %ENV_NAME%
echo CUDA 缓存目录: %CUDA_CACHE_PATH%
echo 日志文件: %LOG_FILE%
echo.

if exist "%CUDA_SHARED_BIN%\cudart64_110.dll" if exist "%CUDNN_SHARED_BIN%\cudnn64_8.dll" (
    set "PATH=%CUDA_SHARED_BIN%;%CUDNN_SHARED_BIN%;%CUDA_SHARED_DLLS%;%PATH%"
)

"%ENV_PYTHON%" "%ROOT_DIR%check_tensorflow_runtime.py"
if errorlevel 1 (
    echo.
    echo [错误] TensorFlow 运行时检查失败
    echo [提示] 请查看日志: %LOG_FILE%
    exit /b 1
)

echo.
"%ENV_PYTHON%" "%ROOT_DIR%main.py"
exit /b %errorlevel%
