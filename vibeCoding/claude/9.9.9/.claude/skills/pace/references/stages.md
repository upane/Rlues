# PACE References · Stages (v9.9.9)

> 从 pace/SKILL.md 下沉的 stage 详解. 进入某 stage 前 Read 对应段即可, 不必全读.

## brainstorm (借 CodeStable + Superpowers)

**触发**: 用户描述模糊 / 显式说 "想法不清楚" / 无法直接写出可验收标准
**职责**: 多轮对话理清楚, 不评估不约束
**产出**: `sprints/{date}-{slug}/brainstorm.md`
**出口**: 足以形成可观察验收即结束，无固定追加问数。
**路由**: → plan (清晰) / → roadmap (≥2 独立验收切片) / → design (System 路径需求清晰)
**详**: `~/.claude/skills/brainstorm/SKILL.md`

## roadmap (借 CodeStable)

**触发**: ≥2 个可独立验收、可独立 ship 的切片 / 显式 "拆分" (hotfix2: 模块数只定风险等级, 不单独触发)
**职责**: 拆 feature 序列, 产出 items.yaml + roadmap.md
**调度**: delivery-gate 与主 agent 在 ship 后核对并推进下一 item
**详**: `~/.claude/skills/roadmap/SKILL.md`

## plan

**进入条件**: brainstorm/roadmap 完成, 或需求清晰直接进
**工作流**:
1. 作者写 `design.md`（含验收标准 / Done Contract）
2. 机械派生 `review-packet.md`（hash + 完整 AC ID，≤80 行）。作者不 spawn critic，不给自己的设计打 VERDICT
3. Feature 默认无独立设计审查；Refactor/System 或用户显式要求：由**非作者会话**执行 packet → `reviews/design-review.md`
4. 进 impl 前 spec-gate 验 AC + packet 双射

**例外**: Hotfix 可省略 design

## design (System 路径)

System 路径专用, plan 通过后进 design 出详细架构. 可 spawn `architect` subagent.

## impl (铁律[零写入] 按区路由)

**工作流**:
1. **done_contract 写进 design.md 的 `## Done Contract` 段** (2026-07-28 gate-descaling: 不再单立 checklist.yaml, 消灭双写):
   逐条把验收标准写成**可机械判定**的完成条件 (命令 + 期望输出 / 文件 + 断言)。
   铁律: generator 与一轮 reviewer 判的是**同一份 done_contract**; 不得在 review 时另造判据,
   generator 也不得自行放宽。判据要改 → 回 design 改, 不在 impl 里私改。
   checklist.yaml 降为**可选** (超大 sprint 需要任务推进表时才建; 存在则 delivery-gate 照旧验全绿)
2. 绿区任务 (≤3 文件且合计 ≤150 行, 或 Hotfix/Quick/Bugfix): 主 agent 直接做, 不强制 subagent
3. 黄区: 调用 generator subagent (TDD: 测试先, 代码后); Feature+ 必须留下 generator 的 Stop 完成记录, 仅 Start 不算完成；writer 派发先完成 orchestration.md 的 spawn-binding-handshake
4. 红区 (Refactor/System): generator **必须 `isolation: worktree`**
5. 并行多 generator (大改): 也强制 worktree
6. 超大规模 (≥5 独立同构子任务): 评估 ultracode, 见 `references/orchestration.md`
7. PostToolUse 对 validation command 写脱敏 evidence.yaml; 普通工具不写 raw tool-trace (W35)
8. v9.9.0: index-updater 检测改动文件数超路径上限 (Quick>3/Feature>10) → next_action=re-route,
   主 agent 停当前 task 重走路由审议 (只升不降, 补新路径欠的 stage)

## runtime-verify (v9.8.0, System/Refactor 强制 · Feature 可选)

impl 与适用单测完成后，按 design 与 runtime-env 运行真实场景：
- 本机满足合同即可；VM 是否 required 由验收决定，配置存在或 SSH 可达不等于项目 scenario ready。
- 当前原生 `/goal` 可用且已授权时可承载长任务；不可用则沿本端会话执行，不依赖另一平台或自造循环。
- 前端用 playwright，后端真实 API，CLI 用实际命令与退出码断言；产物为 `runtime-verify.md`，含 `## 测试场景`。
- 证据有效性见 [state-contract.md](state-contract.md)；全栈准入见 [fullstack-contract.md](fullstack-contract.md)，runner 细节由 `/athena-runtime-verify` 与 `/athena-vm` 执行。
- 问题回 impl 修复并复验相关场景；R/S 下一步 polish，Feature 下一步 review。已过检查只因变化/失败/剩余风险重复。

## review（一次独立多维审查）

1. 审查最终整合代码；Refactor/System 已完成 runtime-verify → polish。CC 原生 review 可用优先，否则本端只读 reviewer/独立会话。
2. 派发、真实 target、packet/输入/证据绑定与接收仅按 [execution-contracts.md](execution-contracts.md)。只读 reviewer 不写共享状态，由主 agent 保存原始结果和接收封装。
3. 仅实际异步调用设 `next_action=await-review-result`，Stop 放行且不续跑；前台返回直接接受校验。等待不重复派发；缺结果不能 ship。
4. 结果为 `reviews/implementation-review.md`，含现有 frontmatter/hash、review_run_id、native_output_ref 与原文 findings。run/packet/内容失配保持未完成，旧结果保存 superseded。
5. 待审内容变化才针对性复核；同因新 P0 第二次复核仍出现交还用户。

VERDICT: **PASS | CONCERNS | REWORK | FAIL**。PASS 后才进入 ship；其余按 findings 回对应 impl/design。禁止调度 critic/evaluator/spec-compliance，禁止作者伪造独立 PASS。

## polish (Refactor/System 强制，且在 review **之前**)

主 agent 派发有界 `polish-worker`，沿既有实现 worktree 串行清理：
- 临时代码、注释、冗余、低效、过度设计五项；只修与当前合同有关的内容。
- 主 agent 根据返回与实际 diff 写 `cleanup-pass.md`，维护所需 architecture/ 与有价值 compound。
- 清理改动运行相关检查；失败回 impl/runtime-verify。完成设置下一步 review，不能直接 ship。
- 使用现有 worktree 不额外嵌套隔离；writer 绑定与例外按 orchestration。合并、PR、推送、worktree 清理留到 ship 按有效授权处理。

## ship

主 agent 按用户有效授权 commit、push 或提交可审查产物；无发布授权保留 candidate。delivery-gate 检查 (2026-07-28 gate-descaling 后):
- Refactor/System: 必须有 cleanup-pass.md
- Refactor/System (≥5 文件): 必须更新 architecture/ (铁律[门禁])
- design_changed_after_impl=true: block 直到重新 review
- Feature/Refactor/System: `reviews/implementation-review.md` frontmatter `verdict: PASS`，含 `review_run_id` 与 `native_output_ref`；packet/diff hash 与现场重算一致
- Feature+ 必须有共享 assignments/events JSONL 中完整 generator Start→assignment→Stop 链 (逃生: skip_impl_subagent_check)
- 不再用 Critic Findings 标题计数；design.md >300 行 stderr 警告
- 已有 review-manifest 存在时继续验全链（design.md 与 R/S runtime-verify.md）；当前审查派发/接受的最小持久绑定不得因 manifest 可选而省略，见 execution-contracts.md
- hotfix2 (2026-07-29): AC11/12 保留标号豁免废除; token/tool-trace/snapshot/continuator 已退出默认 lifecycle (只在 ship 或显式采集); next_action 仅机器枚举
- checklist.yaml 存在才验; 记账文件 (token-usage/tool-trace/stop-failures/harness-patches/proposals) 不受 post-review drift 拦截
- 完整派工任务内联 Agent message；assignment/session-log 保存必要恢复事实，禁止 CODEX-TASK.md 类第二任务文档
- AC 证据记法 (2026-07-28 W23): 跑真实验证命令后 evidence-collector 已自动落记录, agent 在该记录**补一行 `covers: [ACn]`** 即 admissible; 十字段手写 artifact 记录仅当命令证据不适用 (source: artifact/review) 时用
- design.md mtime 晚于 implementation-review.md → block 重新 review
- current_roadmap_slug 非空: 提示主 agent 继续下个 item
- 长任务只在原生入口可用且已授权时使用 `/goal`；Done Contract 在 design.md，checklist 若存在也必须全绿

### 推送门禁 (pre-bash-guard) 与合法放行

两道独立门禁, 合法推送均无需伪造产物:

- **pre-bash-guard** (Bash 前置) 拦 `git push`: 当前项目 stage 非 ship 且非空 (idle) → BLOCK。放行 = 走到 ship 再推, 或 `ATHENA_ALLOW_PUSH=1 git push …` (认命令内联标直接放行)。后者用于**推非当前 sprint 的维护性改动** (Athena 源仓自身 / 跨仓同步 / sprint 未 ship 但需推的记账 commit) —— **取代"切 stage=ship→推→回 plan"绕行**, 该绕行会连带触发下面的 ship 契约、制造记账噪声。
- **delivery-gate 轻门禁 (v9.9.6)**: ship 时若净 diff (对 upstream) ≤60 行且仅触及文档 / 配置 / 依赖 / `.ai_state` / 测试 (排除 hooks/settings/源码逻辑) → 只校验 roadmap 一致性, 跳过 review-manifest / tdd-evidence / 当前实现审查; 源码 / harness / 超预算仍走完整契约 (fail-closed)。让纯文档 / 依赖类 ship 不再被迫产出机械改动无法诚实给出的 red→green。

## 文书预算 (2026-07-28 gate-descaling — 反"程序员变文员")

实测病灶: 9.9.6 主 sprint 写入操作里 `.ai_state` 记账 102 次 vs 代码 15 次 (8.4%)。规则:

- **手写文档白名单**: design.md / review-packet.md / reviews/implementation-review.md / (Bugfix) issue-report+fix-note / (R/S) runtime-verify.md + cleanup-pass.md + 可选 session-log.md。route_history 单条 >160B 溢出搬到 route-note，不丢弃
- **体积预算**: design.md 目标 ≤200 行 (System) / ≤80 行 (Feature); 超 300 行 stderr 警告 (不 block)
- **判据**: 一个 sprint 内 agent 手写 md 字节数不应超过代码 diff 字节数; 超了 = 文书跑赢了产出, 停下反省而不是继续写

## 新数据目录 (v9.6.4 起)

```
.ai_state/
├── _index.md                          # 项目状态 + frontmatter
├── sprints/
│   └── YYYY-MM-DD-{slug}/             # 一个 sprint 一目录
│       ├── route-note.md              # (可选, 2026-07-28 起) 默认并入 _index.route_history 一行; 仅复杂 re-route 才单立
│       ├── brainstorm.md              # (可选) brainstorm 产出
│       ├── design.md                  # 含 ## Done Contract / 验收标准
│       ├── review-packet.md           # 派生投影，≤80 行
│       ├── checklist.yaml             # (可选, 2026-07-28 起) 超大 sprint 才建; 存在则验全绿
│       ├── issue-report.md            # v9.8.0 Bugfix: 可复现报告 (athena-issue)
│       ├── fix-note.md                # v9.8.0 Bugfix: 修复记录+验证 (delivery-gate 验)
│       ├── runtime-verify.md           # v9.8.0 运行时自测自改 (delivery-gate 验)
│       ├── reviews/implementation-review.md
│       ├── cleanup-pass.md            # polish 产出
│       ├── subagent-log.md            # 历史兼容视图, 默认不生成
│       ├── subagent-events.jsonl      # CC/CX 共享 raw lifecycle schema
│       ├── subagent-assignments.jsonl # 主 agent Start→任务意图握手
│       ├── evidence.yaml              # validation success/failure 证据
│       └── tool-trace.jsonl           # 仅 release-eval/显式采集, 默认不生成
├── roadmap/
│   └── {slug}/
│       ├── roadmap.md
│       └── items.yaml
├── architecture/
│   ├── ARCHITECTURE.md
│   └── {type}-{slug}.md
├── requirements/                     # v9.8.0 长效需求档 (WHY, 逃生通道)
│   └── {slug}.md
├── compound/
│   ├── YYYY-MM-DD-learning-{slug}.md
│   ├── YYYY-MM-DD-trick-{slug}.md
│   ├── YYYY-MM-DD-decision-{slug}.md
│   └── YYYY-MM-DD-explore-{slug}.md
└── .snapshots/                        # PreCompact 快照
```
