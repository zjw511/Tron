@echo off
chcp 65001 >nul
echo ========================================
echo   测试表格节点功能
echo ========================================
echo.

echo [1/3] 安装依赖...
python -m pip install pandas openpyxl -q
if %errorlevel% neq 0 (
    echo [!] 依赖安装失败
    pause
    exit /b 1
)
echo [OK] 依赖已安装

echo.
echo [2/3] 启动服务器...
echo.
echo 请在浏览器中：
echo   1. 打开 http://127.0.0.1:8188
echo   2. 创建工作流: LoadCSV → PreviewTable
echo   3. LoadCSV节点设置: file_path = examples/sample_data.csv
echo   4. 点击 Queue Prompt
echo   5. 查看表格显示！
echo.

python full_server.py

