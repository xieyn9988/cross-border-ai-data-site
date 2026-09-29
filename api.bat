@echo off
chcp 65001 >nul
echo ============================================
echo  跨境智能数据站点 · 启动配置面板
echo ============================================
echo  打开浏览器访问：http://localhost:8000/admin
echo  按 Ctrl+C 停止服务
echo ============================================
python scripts\api.py
pause