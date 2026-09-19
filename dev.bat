@echo off
setlocal EnableExtensions
rem ============================================================================
rem  Learning Guide · 学习讨论室 —— 一键启动开发环境（Windows）
rem
rem  用法：
rem    dev.bat            启动后端 :8000 + 前端 :5173（各开一个窗口）
rem    dev.bat check      只做环境自检，不启动任何进程
rem    dev.bat stop       按端口停掉这两个进程（含子进程）
rem
rem  约定（与 README / AGENTS 一致）：
rem    - 端口固定 8000 / 5173，不新增端口；前端 Vite 把 /api 代理到 8000；
rem    - 凭据只在仓库根 .env（本脚本不读取、不回显任何密钥）；
rem    - 后端解释器优先取环境变量 LG_PY，其次 conda 环境 learningguide，最后 PATH 里的 python。
rem ============================================================================

set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"
set "BACKEND=%HERE%\backend"
set "FRONTEND=%HERE%\frontend"
set "BACKPORT=8000"
set "FRONTPORT=5173"
set "PGSVC=postgresql-x64-17"
set "ENVFILE=%HERE%\.env"

set "PY=%LG_PY%"
if not defined PY if exist "C:\ProgramData\miniconda3\envs\learningguide\python.exe" set "PY=C:\ProgramData\miniconda3\envs\learningguide\python.exe"
if not defined PY set "PY=python"

set "MODE=%~1"
if "%MODE%"=="" set "MODE=start"

if not exist "%BACKEND%\app\main.py" (
  echo [x] 这个脚本要放在仓库根目录（找不到 %BACKEND%\app\main.py^）
  exit /b 1
)

if /i "%MODE%"=="stop"  goto :do_stop
if /i "%MODE%"=="check" goto :do_check
if /i "%MODE%"=="start" goto :do_start
echo [x] 未知参数：%MODE%（可用：无参数 / check / stop^）
exit /b 1

rem ---------------------------------------------------------------- 自检
:do_check
echo ==== 环境自检 ====
call :chk_python
call :chk_npm
call :chk_env
call :chk_pg
call :chk_port %BACKPORT% 后端
call :chk_port %FRONTPORT% 前端
echo.
echo 自检结束。启动：dev.bat    停止：dev.bat stop
exit /b 0

:chk_python
"%PY%" -V >nul 2>nul
if errorlevel 1 (
  echo [x] Python 不可用：%PY%   ^(设置 LG_PY，或装 conda 环境 learningguide^)
) else (
  for /f "delims=" %%v in ('"%PY%" -V 2^>^&1') do echo [ok] Python %%v  ^(解释器：%PY%^)
)
exit /b 0

:chk_npm
where npm >nul 2>nul
if errorlevel 1 (echo [x] npm 不在 PATH 里) else (echo [ok] npm 可用)
exit /b 0

:chk_env
if exist "%ENVFILE%" (echo [ok] 仓库根 .env 存在) else (echo [x] 缺 %ENVFILE%  —— 从 .env.example 复制并填 DATABASE_URL / SESSION_SECRET / LIVEKIT_*^(值只放本机，不入库^))
exit /b 0

:chk_pg
sc query %PGSVC% 2>nul | findstr /i "RUNNING" >nul
if errorlevel 1 (
  echo [!] PostgreSQL 服务 %PGSVC% 未在运行 —— 启动：net start %PGSVC%  ^(需管理员^)
) else (
  echo [ok] PostgreSQL 服务 %PGSVC% 正在运行
)
exit /b 0

:chk_port
set "P=%~1"
netstat -ano | findstr /i "LISTENING" | findstr ":%P%" >nul
if errorlevel 1 (
  echo [ok] 端口 %P% 空闲  ^(%~2^)
) else (
  echo [!] 端口 %P% 已被占用  ^(%~2^) —— 先执行 dev.bat stop
)
exit /b 0

rem ---------------------------------------------------------------- 启动
:do_start
echo ==== 启动开发环境 ====
call :chk_python
call :chk_npm
call :chk_env
call :chk_pg
call :chk_port %BACKPORT% 后端
call :chk_port %FRONTPORT% 前端
echo.

echo [..] 打开后端窗口：uvicorn app.main:app --reload --port %BACKPORT%
start "LG 后端 :%BACKPORT%" /d "%BACKEND%" cmd /k "%PY% -m uvicorn app.main:app --reload --port %BACKPORT%"

echo [..] 打开前端窗口：npm run dev  ^(Vite :%FRONTPORT%，/api 代理到 :%BACKPORT%^)
start "LG 前端 :%FRONTPORT%" /d "%FRONTEND%" cmd /k "npm run dev"

echo.
echo [..] 等待后端就绪（最多 45 秒）…
call :wait_http "http://127.0.0.1:%BACKPORT%/api/auth/me" 后端
echo [..] 等待前端就绪（最多 45 秒）…
call :wait_http "http://localhost:%FRONTPORT%/" 前端

echo.
echo ==== 就绪 ====
echo   前端（用它演示）：http://localhost:%FRONTPORT%
echo   后端（Vite 已代理 /api）：http://127.0.0.1:%BACKPORT%/api/auth/me
echo   演示账号（种子数据，口令 demo1234）：host@example.com / mod@example.com / part@example.com
echo   停止服务：dev.bat stop
exit /b 0

rem 参数：URL 与名字；Vite 默认只监听 IPv6 回环（::1），所以前端要用 localhost 探，不能用 127.0.0.1
:wait_http
set "URL=%~1"
if not exist "%SystemRoot%\System32\curl.exe" (
  echo [i] 没有 curl，跳过 %~2 的就绪等待（去看它自己的窗口输出^）
  exit /b 0
)
set /a WAIT_I=0
:wait_loop
set /a WAIT_I+=1
"%SystemRoot%\System32\curl.exe" -s -o nul -w "%%{http_code}" "%URL%" > "%TEMP%\lg_http_code.txt" 2>nul
set "CODE="
set /p CODE=<"%TEMP%\lg_http_code.txt"
if "%CODE%"=="200" (
  echo [ok] %~2 已就绪（HTTP 200）：%URL%
  exit /b 0
)
if "%CODE%"=="401" (
  echo [ok] %~2 已就绪（HTTP 401，未登录属正常）：%URL%
  exit /b 0
)
if %WAIT_I% GEQ 45 (
  echo [!] %~2 等待超时（45 秒）：%URL%  —— 看它自己的窗口里的报错
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto :wait_loop

rem ---------------------------------------------------------------- 停止
:do_stop
echo ==== 停止开发服务 ====
call :kill_port %FRONTPORT% 前端
call :kill_port %BACKPORT% 后端
exit /b 0

:kill_port
set "P=%~1"
set "FOUND="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /i "LISTENING" ^| findstr ":%P%"') do (
  set "FOUND=1"
  taskkill /PID %%a /T /F >nul 2>nul
  echo [ok] 已结束 %~2 进程 PID %%a ^(端口 %P%^)
)
if not defined FOUND echo [i] 端口 %P% 上没有监听进程（%2 未在跑^）
exit /b 0
