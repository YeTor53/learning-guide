@echo off
REM r013 演示道具：开一个**受脚本控制的演示账号窗口**（固定 profile + 固定调试端口）。
REM 用法：demo-window.bat part          角色：host / mod / part / admin
REM       demo-window.bat part room_xxx  顺带直接打开某房间的交流页
REM 为什么单独开：演示「断线重连」时要精确断**某一个账号**，只有脚本自己开的窗口才能被精确定位；
REM               profile 会记住登录态，第一次登录过以后再来就是已登录。
setlocal
set ROLE=%1
if "%ROLE%"=="" set ROLE=part
set ROOM=%2
set PROFILE=%TEMP%\lg_demo\%ROLE%
set PORT=9400
if "%ROLE%"=="host"  set PORT=9401
if "%ROLE%"=="mod"   set PORT=9402
if "%ROLE%"=="part"  set PORT=9403
if "%ROLE%"=="admin" set PORT=9404
set URL=http://localhost:5173/login
if not "%ROOM%"=="" set URL=http://localhost:5173/rooms/%ROOM%/live
echo [demo-window] 角色=%ROLE%  profile=%PROFILE%  调试端口=%PORT%
echo [demo-window] 打开 %URL%
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%PROFILE%" --remote-debugging-port=%PORT% --no-first-run --no-default-browser-check --window-size=1440,900 --window-position=0,0 "%URL%"
endlocal
