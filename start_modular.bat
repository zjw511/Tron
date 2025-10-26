@echo off
cd /d "%~dp0"
echo.
echo ========================================
echo   Modular ComfyUI Server
echo ========================================
echo.
echo 模块化节点版本，去除国际化代码
echo 端口: 8188
echo.
python modular_server.py
pause
