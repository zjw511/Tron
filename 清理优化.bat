@echo off
cd /d "%~dp0"

echo ========================================
echo   ComfyUI 清理优化工具
echo ========================================
echo.

echo [1/5] 停止服务器...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/5] 清理temp目录...
if exist temp (
    del /Q temp\* >nul 2>&1
    echo   已清理 temp/ 目录
) else (
    echo   temp/ 目录不存在
)

echo [3/5] 清理output目录中的旧文件...
if exist output (
    forfiles /P output /D -7 /C "cmd /c del @path" >nul 2>&1
    echo   已清理7天前的文件
) else (
    echo   output/ 目录不存在
)

echo [4/5] 清理Python缓存...
if exist __pycache__ (
    rd /S /Q __pycache__ >nul 2>&1
    echo   已清理 __pycache__
)

echo [5/5] 优化完成！
echo.
echo ========================================
echo   优化建议：
echo ========================================
echo   1. 按 Ctrl+Shift+R 强制刷新浏览器
echo   2. 关闭其他不需要的标签页
echo   3. 使用较小的图片（建议 ^< 2048x2048）
echo   4. 简化工作流，减少节点数量
echo.
echo 是否立即启动服务器？
pause

echo.
echo 正在启动服务器...
python full_server.py

