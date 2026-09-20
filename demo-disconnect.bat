@echo off
REM r013 演示道具：**点一下**，把某个固定演示账号的窗口真断 N 秒再恢复（现场演「断线重连」）。
REM 用法：demo-disconnect.bat            默认断 part 10 秒
REM       demo-disconnect.bat 12 host    断 12 秒，目标是 host 角色窗口
REM       demo-disconnect.bat --list     只列出会被断的进程（不真断）
setlocal
if "%PY%"=="" set PY=C:\ProgramData\miniconda3\envs\learningguide\python.exe
cd /d %~dp0
if "%~1"=="" (
  "%PY%" backend\scripts\demo_disconnect.py --role part --seconds 10
) else (
  if "%~2"=="" (
    "%PY%" backend\scripts\demo_disconnect.py --role part --seconds %~1
  ) else (
    "%PY%" backend\scripts\demo_disconnect.py --role %~2 --seconds %~1
  )
)
echo.
pause
endlocal
