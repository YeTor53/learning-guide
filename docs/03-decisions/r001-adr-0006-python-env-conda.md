---
title: r001-ADR-0006 运行环境与依赖管理：conda 环境 learningguide
description: 后端运行时改用 conda 环境 learningguide（取代总设计初稿的 backend/.venv），依赖经清华源 pip 安装。
type: adr
status: accepted
owner: 陀梓皓
updated: 2026-09-17
---

<!-- overview -->
用户 2026-09-17 指示「建 conda 环境后装依赖」。本 ADR 记录环境决策、实际安装事实与对已写文档的同步范围。

## 背景

- 本机已有 6 个 conda 环境（`base`、`AIsecurity`、`HuiZhenAI`、`automaticcrawler`、`hermes`、`huizhenai`、`parallel_lab_p-master`），用户日常在 PyCharm 里选 conda 解释器跑脚本。
- 总设计初稿写的是 `backend/.venv`（项目内 venv）；与本机惯例不一致，且 PyCharm 里需额外配置。
- 后端所需依赖（FastAPI/uvicorn/psycopg 等）不在 conda 渠道的常用包里，实际仍以 `pip` 安装，conda 只负责**解释器与隔离**。

## 决策

用 conda 环境 **`learningguide`**（Python 3.11.16，conda-forge）作为后端运行时；依赖用 `pip` 装入该环境（显式使用清华源）；PyCharm 里选该环境作解释器；**不再创建 `backend/.venv`**。

## 理由

1. 与本机惯例一致（用户既有项目同为 conda 环境），PyCharm 可直接选用，无需额外配置；
2. 隔离干净：不污染 `base`，也不污染 hermes 环境（后者是 agent 自己的运行时）；
3. conda 负责 Python 版本与隔离，pip 负责业务依赖，分工明确、命令短；
4. 交付可复现：环境创建命令 + `requirements.txt`（由 `pip freeze` 生成）随仓库提交。

## 被否的替代方案

- **`backend/.venv`（总设计初稿）**：与本机习惯不符，PyCharm 需另配；无额外收益。
- **Docker（容器化整个后端）**：本机无 Docker、WSL 无发行版，成本高；Compose 属 M5 加分项，届时再用镜像方式补，不影响本地 conda 开发。

## 实际安装事实（2026-09-17 实测）

| 项 | 值 |
| --- | --- |
| conda | `conda 25.9.1`（`C:\ProgramData\miniconda3\Scripts\conda.exe`） |
| 创建命令 | `conda create -n learningguide python=3.11 -y`（耗时 88.8 秒） |
| 环境路径 | `C:\ProgramData\miniconda3\envs\learningguide\python.exe` |
| Python | `3.11.16 | packaged by conda-forge` |
| 依赖安装 | `python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple fastapi "uvicorn[standard]" "psycopg[binary,pool]" python-dotenv pytest httpx`（耗时 11.3 秒，exit 0） |
| 关键版本 | fastapi 0.141.1 / starlette 1.6.0 / uvicorn 0.53.0 / psycopg 3.3.5（+binary+pool）/ pydantic 2.13.5 / python-dotenv 1.2.3 / pytest 9.1.1 / httpx 0.28.1 |
| 连接探测 | `psycopg.connect("postgresql://lg_app:__wrong__@127.0.0.1:5432/learning_guide")` → `OperationalError: password authentication failed`，证明**驱动、TCP、服务均通**；注意 PostgreSQL 对不存在的角色同样返回认证失败，故该探测**不能**证明 `lg_app` 已建（角色与库由用户按教程 §4 建，用户已确认完成） |
| 插曲 | pip 安装时输出 hermes-agent 的依赖冲突警告，原因是 `PYTHONPATH` 含 `C:\Users\Administrator\hermes-agent` 元数据；**包实际装入 learningguide 环境**（已核对 `fastapi.__file__`），hermes 环境未被污染（其 fastapi 0.133.1 / uvicorn 0.41.0 为原有版本） |

## 影响

- 已同步文档：总设计 `r001-app-architecture.md` §2/§4/§11/§12、需求单 §4/§8/§9（`backend/.venv` 的提法全部改为 conda 环境）。
- 运行方式：`conda activate learningguide` 后执行 `python scripts/...` 与 `python -m pytest`；agent 侧可直接用绝对路径 `C:\ProgramData\miniconda3\envs\learningguide\python.exe`（免激活，便于脚本化）。
- `requirements.txt` / `requirements-dev.txt` 由 cp-r001-1 用 `pip freeze` 生成并提交（运行依赖与开发依赖分开）。

## 变更记录

- 2026-09-17 建立（accepted）：conda 环境 `learningguide` 取代 `backend/.venv`，依赖已装并实测连接。
