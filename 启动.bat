@echo off
chcp 65001 >nul
echo ========================================
echo   双星科技场景智能分割工具 v1.1
echo ========================================
echo.
echo 正在启动程序...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python
    echo 请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM 检查依赖是否安装
python -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo [提示] 检测到首次运行，正在安装依赖...
    echo 这可能需要几分钟，请耐心等待...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [错误] 依赖安装失败
        echo 请手动运行: pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [成功] 依赖安装完成
    echo.
)

REM 启动程序
python main.py

if errorlevel 1 (
    echo.
    echo [错误] 程序运行出错
    echo.
    pause
)
