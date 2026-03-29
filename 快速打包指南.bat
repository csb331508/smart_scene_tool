@echo off
chcp 65001 >nul
echo.
echo ╔══════════════════════════════════════════╗
echo ║     场景分割工具 - 快速打包指南         ║
echo ╚══════════════════════════════════════════╝
echo.
echo 📦 打包配置说明
echo ═══════════════════════════════════════════
echo.
echo ✅ 已配置为单文件模式
echo    - 所有依赖打包到一个 .exe 文件中
echo    - 输出文件: dist\场景分割工具.exe
echo.
echo ✅ 已隐藏控制台窗口
echo    - 主程序运行无控制台窗口
echo    - FFmpeg 处理时也无控制台窗口
echo.
echo ✅ 包含所有必要组件
echo    - Python 运行时
echo    - TensorFlow AI 库
echo    - TransNetV2 模型权重
echo    - MoviePy 视频处理
echo    - PyQt6 图形界面
echo.
echo ─────────────────────────────────────────
echo.
echo 🚀 开始打包
echo.
echo 1. 双击运行 build.bat
echo 2. 等待 5-15 分钟（取决于电脑性能）
echo 3. 完成后在 dist 文件夹找到 .exe 文件
echo.
echo ─────────────────────────────────────────
echo.
echo 📝 打包文件说明
echo.
echo build.spec        - PyInstaller 配置文件（单文件打包）
echo build.bat         - 自动打包脚本
echo 打包说明.md       - 详细打包文档
echo 快速打包指南.bat  - 本文件
echo.
echo ─────────────────────────────────────────
echo.
echo ⚠️  注意事项
echo.
echo - 确保已激活虚拟环境（如果使用）
echo - 首次打包会下载 PyInstaller（如未安装）
echo - 打包后的 .exe 文件较大（500MB-1GB）是正常的
echo - 运行打包的程序仍需系统安装 FFmpeg
echo.
echo ─────────────────────────────────────────
echo.
echo 📖 查看详细文档: 打包说明.md
echo.
echo 按任意键关闭...
pause >nul
