@echo off
chcp 65001 >nul
echo ============================================
echo  跨境智能数据站点 · 运行全部场景
echo ============================================
python scripts\run.py
echo.
echo 输出文件在 output\ 目录
pause