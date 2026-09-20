# 给 AI 的项目规则（AGENTS.md）

本仓库按四阶段工作流推进：**澄清 → 文档先行 → 增量实现 → 审查**。每一阶段需人确认后才放行。

## 硬规矩

1. 未获批准的规划 / 需求单不做实现；每处代码改动必须挂在某个 `rNNN` 需求上。
2. 一次提交 = 一个逻辑增量；提交信息 `type(scope): ≤50字 [Req: rNNN]`。
3. `git add` 只写具体路径，禁用 `git add -A`。
4. 分支 `req/rNNN-短名`；实现期打 `cp-rNNN-N` checkpoint tag；人审通过后由人 `merge --no-ff` 并打 `round-rNNN-done`。
5. 历史 append-only：禁 amend / rebase -i / squash；回退一律 revert。
6. 文档与代码同一次提交；行为或接口变更必须记 ADR + 模块页「变更记录」小节。
7. 轮次结束时文档 = 代码真相；验收清单必须逐条给出实现位置 + 证据（命令输出），不许只写「已实现」。

## 禁区

- 密钥永不入库：`.env`（仅 `.env.example` 可入库）、任何 API Key / Secret、数据库文件、`node_modules/`。
- LiveKit `API_SECRET` 只允许存在于服务端进程环境变量：前端代码、前端产物、日志、错误响应中都不得出现。
- 不擅自增删依赖、改端口、改目录结构；需要时先在需求单登记并获批准。
- 不采用 LiveKit Meet 默认页面；不使用来源不明的模板代码而不注明出处。

## 提交前检查（`<check>`，r001 口径，详见 `docs/01-architecture/r001-app-architecture.md` §11）

在 conda 环境 `learningguide`（ADR-0006）下、于仓库根目录与 `frontend/` 下依次执行，全绿才提交：

- [ ] `python backend/scripts/db_init.py --reset --seed`（打印各表行数）
- [ ] `pytest backend/tests -q`（schema 断言 + 服务层 + 接口层）
- [ ] `python backend/scripts/smoke.py`（真实 HTTP 冒烟：注册 → 建房 → 申请 → 批准 → 离开 → 结束）
- [ ] `cd frontend && npx tsc --noEmit && npm run build`
- [ ] `git grep -nE "API_SECRET|API_KEY" -- backend/app frontend/src`（除 `config.py` 变量名外无命中）
- [ ] 文档已更新且与代码一致；`git status --porcelain` 为空

## 文档纪律

- 文档名携带出现轮次：单轮产物 `rNNN-<短名>`，跨轮/项目级用 `global-` 前缀。
- 新建文档写 front matter：`title / description / type / status / owner / updated`。
- 一个概念只在一处讲，别处链接（禁双源）。
- 仓库文档只写本项目方案与决策，不夹带外部出处、研究笔记、外部案例对照。

## r002 起新增的验证命令（实时房间）

```bash
pytest backend/tests -q                                  # 191 项（2026-09-20 实测；数字会漂，以命令输出为准）
npx tsc --noEmit --project frontend                      # 前端类型
python backend/scripts/smoke.py --base-url http://127.0.0.1:8000   # PASS 46/46（2026-09-20 实测）
```

- 实时凭据只在 `.env`（`LIVEKIT_MODE` / `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET`）；**不得写进代码、文档、提交信息或聊天**。
- 禁区不变：装依赖需先问；helper 不接触明文密钥；不用 `git commit --amend`。
- **本机地址口径（r011 redirect-03）**：后端 `127.0.0.1:8000`（用 `localhost:8000` 每次多等约 2 秒，实测 2070ms vs 6ms）；前端 `localhost:5173`（安全上下文 + Vite 只绑 `::1`）。
- 现状口径（改动前必读）：房间 = **一次性讨论**（ADR-0012）；治理动作**只在交流页抽屉**（房间管理页已删除，redirect-06）；容量按**本库在册成员**（ADR-0016 取代 ADR-0012 的 D1/D2/D3/D5）：满员时**申请与批准都被挡**（`POST /join-requests` 与 `/approve` 均 409 `ROOM_FULL`）；取票不再查 LiveKit（r005，1650ms → 3.2ms）。
