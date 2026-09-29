@echo off
chcp 65001 >nul
echo ============================================
echo  跨境智能数据站点 · 环境安装
echo ============================================
python scripts\setup.py
if errorlevel 1 (
    echo.
    echo ❌ 安装失败，请确认已安装 Python 3.9+
    pause
    exit /b 1
)
echo.
echo ✅ 环境准备完成，现在可以双击 run.bat 运行
pause