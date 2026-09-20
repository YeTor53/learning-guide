@echo off
REM r010 转写 worker 启动脚本（ADR-0023）：独立环境 lg_agents，本机演示/开发用
REM 用法：agents.bat                          默认走 LiveKit Inference（消耗免费档额度）
REM       set AGENT_STT=fake && agents.bat     走离线假 STT（零配额，联调/演示降级）
REM
REM 2026-09-20 修两处：
REM   ① 换行曾写成「双 CR」且以 UTF-8 存盘 —— cmd 按 GBK 读会把中文注释拆出来当命令执行
REM      （报「不是内部或外部命令」），现改回 GBK + 标准 CRLF。
REM   ② lg_agents 环境没装 python-dotenv，worker 自己不会读 .env —— 所以这里先把仓库根
REM      .env 注入环境变量再启动；否则 worker 报 "ws_url is required"，然后退出-重启循环。
setlocal enabledelayedexpansion
cd /d %~dp0
if not exist ".env" (
  echo [agents] 找不到仓库根的 .env —— worker 需要 LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET
  pause
  exit /b 2
)
for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do (
  set "AGENT_ENV_VAL=%%b"
  set "AGENT_ENV_VAL=!AGENT_ENV_VAL:"=!"
  for /f "tokens=* delims= " %%c in ("!AGENT_ENV_VAL!") do set "%%a=%%c"
)
if not defined AGENT_STT set "AGENT_STT=inference"
if not defined AGENT_BACKEND_URL set "AGENT_BACKEND_URL=http://127.0.0.1:8000"
echo [agents] AGENT_STT=%AGENT_STT%   （inference=走 LiveKit Inference / fake=离线桩）
if defined LIVEKIT_URL (echo [agents] LIVEKIT_URL 已从 .env 注入) else (echo [agents] ！LIVEKIT_URL 缺失，worker 会起不来)
if defined LIVEKIT_API_KEY (echo [agents] LIVEKIT_API_KEY 已注入) else (echo [agents] ！LIVEKIT_API_KEY 缺失)
echo [agents] 心跳上报目标 AGENT_BACKEND_URL=%AGENT_BACKEND_URL%（后端要在跑）
echo.
call C:\ProgramData\miniconda3\Scripts\activate.bat lg_agents
:loop
python backend\agents\transcriber.py dev
echo.
echo [agents] 进程退出（code %ERRORLEVEL%），3 秒后自动重启…（Ctrl+C 停止）
timeout /t 3 /nobreak >nul
goto loop
