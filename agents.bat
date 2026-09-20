@echo off
REM r010 转写 worker 启动脚本（ADR-0023）：独立环境 lg_agents，本机演示/开发用
REM 用法：agents.bat                         走 LiveKit Inference（默认，消耗免费档额度）
REM       set AGENT_STT=fake && agents.bat    走离线假 STT（零配额，联调/演示降级）
REM 说明：worker 实测会因 LiveKit FFI 一次性 panic 退出（room connect 超时，见 review 未闭合 ①），
REM       故这里带**自动重启**；生产环境请交给进程管理器（systemd / 任务计划 / 容器）。
setlocal
call C:\ProgramData\miniconda3\Scripts\activate.bat lg_agents
cd /d %~dp0
echo [agents] AGENT_STT=%AGENT_STT%  (inference=走 LiveKit Inference / fake=离线桩)
:loop
python backend\agents\transcriber.py dev
echo [agents] 进程退出（code %ERRORLEVEL%），3 秒后自动重启…（Ctrl+C 停止）
timeout /t 3 /nobreak >nul
goto loop
