@echo off
REM r010 转写 worker 启动脚本（ADR-0023）：独立环境 lg_agents，仅本机演示/开发用
REM 用法：agents.bat            走 LiveKit Inference（默认，消耗免费档额度）
REM       set AGENT_STT=fake && agents.bat   走离线假 STT（零配额，联调用）
setlocal
call C:\ProgramData\miniconda3\Scripts\activate.bat lg_agents
cd /d %~dp0
echo [agents] AGENT_STT=%AGENT_STT%  (inference=走 LiveKit Inference / fake=离线桩)
python backend\agents\transcriber.py dev
endlocal
