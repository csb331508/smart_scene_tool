@echo off
chcp 65001 >nul
echo ========================================
echo   场景分割工具 - 打包脚本
echo ========================================
echo.

echo [1/4] 检查依赖...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [错误] PyInstaller 未安装
    echo 正在安装 PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] 安装 PyInstaller 失败
        pause
        exit /b 1
    )
)
echo [OK] PyInstaller 已安装

echo.
echo [2/4] 清理旧文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo [OK] 清理完成

echo.
echo [3/4] 开始打包...
echo 这可能需要几分钟，请耐心等待...
echo.
pyinstaller build.spec
if errorlevel 1 (
    echo.
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo [4/4] 打包完成！
echo.
echo ========================================
echo   打包成功！
echo ========================================
echo.
echo 可执行文件位置: dist\场景分割工具.exe
echo.
echo 提示: 
echo - 首次运行可能需要几秒钟初始化
echo - 确保系统已安装 FFmpeg
echo - 智能分割需要足够的内存（建议 8GB+）
echo.
pause
