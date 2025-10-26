@echo off
chcp 65001 > nul
echo ========================================
echo    Real-time Signal Data Sender
echo    实时信号数据发送器
echo ========================================
echo.
python send_signal_data.py
pause

