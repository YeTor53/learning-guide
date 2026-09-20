@echo off
REM r013 演示道具（网络层真断，观感最好）：临时防火墙掐断本机到 LiveKit 的出网 N 秒，然后自动删规则。
REM 用法：demo-firewall-cut.bat            默认 12 秒
REM       demo-firewall-cut.bat 10         断 10 秒
REM       demo-firewall-cut.bat --status   只看状态（解析到的 IP / 有没有残留规则）
REM       demo-firewall-cut.bat --remove   手动清残留规则（万一脚本被强杀）
REM 需要管理员：不是管理员会自动弹 UAC 提权。
setlocal
if "%~1"=="" ( set ARGS=--seconds 12 ) else ( set ARGS=%* )
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo [demo] 需要管理员权限，正在弹 UAC 提权...
  powershell -NoProfile -Command "Start-Process -Verb RunAs -FilePath '%~f0' -ArgumentList '%ARGS%'"
  goto :eof
)
set PY=C:\ProgramData\miniconda3\envs\learningguide\python.exe
cd /d %~dp0
"%PY%" backend\scripts\demo_firewall_cut.py %ARGS%
echo.
pause
endlocal
