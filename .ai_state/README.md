# .ai_state — Athena PACE 项目状态 (导航)

> 本目录是 Athena 的 **Tier2 持久记忆**(数据平面)。续作先读 `_index.md`(当前状态) + 本 README。

## 当前状态 (2026-08-27)

> 权威值以 `_index.md` frontmatter 为准; 本节只给人读的概览, 不作机械消费。

- 版本: **Athena 9.9.8 "Thin PACE Control Plane"** 双端 (CC+CX), 发行源 `../vibeCoding/{claude,codex}/9.9.8`。9.9.6-hotfix2 为基线。
- 当前 sprint: `sprints/2026-08-27-athena-9-9-8` (System) — 已 ship 并推送 `origin/main` (`cdd639d` / `d832673`), roadmap `athena-9-9-8` 三项全 completed。
- `_index.md` 已迁到 9.9.8 形态: 项目处 **idle 态** (`path`/`stage`/`current_sprint_slug` 全空), 下一个 sprint 由 `/athena-dev` 路由开启。
- 已知残留: AC11 的冻结对照组在 `.runtime/baseline/` (gitignored, 仅本机); `.snapshots/` 已列入 `.gitignore` 但存量文件仍被 git 跟踪。

## 三层记忆 (9.9.8 design «`ai_state`：热状态、耐久知识、冷历史»)

| 层 | 内容 | 默认读取 |
|---|---|---|
| 热状态 | `_index.md` + 当前 sprint | 每轮只读 `_index`, 再跟当前 pointer |
| 耐久知识 | `requirements/` · `architecture/` · `compound/` · `roadmap/` | 只有当前任务命中时读取 |
| 冷历史 | `sprints/archive/{YYYY}/{slug}/` | **默认排除**; 按 slug/关键词显式查询 |
| 运行 telemetry | `.runtime/` | Git ignored, 不进上下文 |

## 目录结构
| 路径 | 内容 |
|---|---|
| `_index.md` | 状态入口 (path/stage/next_action/pointers/counts) — **续作先读**。上限 12 KiB / 列表 ≤10 条 / 单条 ≤160 B |
| `README.md` | 本导航 |
| `harness-patches.md` | **安装态补丁台账** — `~/.claude` / `~/.codex` 不是 git 仓, 本文件是那些改动唯一的仓内痕迹, 每条带可执行复核命令。⚠️ 有机械消费者: 两端 delivery-gate 的 `isLightShipFile` 按**文件名**匹配, diff 含它即取消 light-ship 资格、强制走全契约。**勿改名、勿挪出 `.ai_state/` 顶层** |
| `proposals.md` | **harness 进化提案** (铁律[Hook 是进化器]) — 在本项目实测发现的 P1-P9。无 hook 写它, 由主 agent 在 Stop 反思时手写; gate 白名单**故意不含**它 (加进去等于实质放宽) |
| `sprints/{date}-{slug}/` | **热 sprint** — route-note · design · review-packet · evidence.yaml · reviews/ · runtime-verify · cleanup-pass · index-overflow |
| `sprints/archive/{YYYY}/{slug}/` | **冷历史** — 已 ship 的 sprint 原样归档 (`git mv`, 历史保留)。SessionStart 与 index-updater **不递归此目录**, 所以 `_index.counts` 只反映热层, 不是项目累计值 |
| `roadmap/{slug}/` | 大需求拆分 (roadmap.md + items.yaml)。delivery-gate 只按 `current_roadmap_slug` 校验 item 状态, 不解析 `sprint_slug` 对应的目录 |
| `architecture/` | 系统架构真相 (ARCHITECTURE.md 入口 + athena-9.9.8.md 现状; 9.9.2/9.9.3/9.9.6 为 superseded) |
| `requirements/` | 长效需求档 (WHY) |
| `compound/` | 跨 sprint 复利: learning / trick / decision / explore |
| `.runtime/` | **gitignored 运行时数据** — `baseline/baseline-9.9.6-tokens.json` 是 AC11 的冻结对照组 (显式豁免 retention, 勿删); 其余 telemetry / 可重建 catalog 保留最近 20 次或 14 天 |
| `.snapshots/` | compaction 快照 (已 gitignore; 存量文件仍在 git 跟踪中) |

## 如何续作 (下次持续优化)
1. 读 `_index.md` → 看 `path` / `stage` / `next_action` / `pointers`。三者全空 = idle, 直接走 `/athena-dev` 路由开新 sprint。
2. 架构现状看 `architecture/athena-9.9.8.md`; 审查契约与门禁约束在同一文件的「审查契约」「门禁与状态」两节。
3. 9.9.8 的设计真相与 AC 全集: `sprints/2026-08-27-athena-9-9-8/design.md`; 派生契约 `review-packet.md`; 结果 `reviews/implementation-review.md`。
4. 决策与教训看 `compound/`; harness 本地补丁的复核命令看 `harness-patches.md`; 已 block 过的门禁提案看 `proposals.md`。
5. 找历史 sprint: 先按 slug 猜 `sprints/archive/2026/{slug}/`, 不要 glob 全扫 (铁律[文档即真相·索引先行])。
