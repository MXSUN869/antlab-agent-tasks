# 文档阅读与信息核验 Agent 考核作品

本仓库是 ANTLab「文档阅读与信息核验方向 Agent 项目」应用层开发者考核的提交作品，
包含**基础题**（相近文档记录的核对与证据引用）与**进阶题 B**（源码审查、故障归因与修复）。

> 题包自带的根 `README.md`（考核说明）已被本文件取代，其原文完整保留在本文件末尾的
> 「附录：题包原始 README」。题包的其余说明文件 `开始阅读.md`、`基础/README.md`、
> `进阶/README.md` 与各题面均未改动。

- 整合报告：[report.md](report.md)
- 决策时间线：[decisions.md](decisions.md)
- AI 与完成度声明：[declaration.md](declaration.md)
- 提交安全说明（含哪些内容被排除）：[SECURITY.md](SECURITY.md)

---

## 1. 源码基点与本人改动

本作品**复用题包骨架**，题包来源为考核方发布的 `ANTLab-Agent-Tasks-main`。
按 `进阶/05_提交与报告格式.md` 的要求说明如下：

| 项 | 内容 |
|---|---|
| 上游来源 | 考核方发布的题包（随包提供 `基础/文件校验.json` 与 `进阶/文件校验.json` 逐文件 SHA256） |
| 源码基点 | **题包原始状态**。题包全部原始文件均保留，可用 `文件校验.json` 校验未被改动的部分 |
| 本仓库的改动 | 见下表 |

**相对题包骨架的改动（逐项）**

| 文件 | 改动 | 原因 |
|---|---|---|
| `基础/starter/student.py` | 实现 `prepare_messages()` 与 `improve()` | 题目要求的实现项 |
| `基础/starter/build_main_results.py` | **新增** | 从原始日志重建 40 次主结果并校验 messages 一致性 |
| `基础/starter/judge_and_summarize.py` | **新增** | 汇总 R0/R1/R2/K 与改进配对，产出可复算对照表 |
| `基础/starter/trace_one_request.py` | **新增** | 端到端追溯（证据 E1），可在干净环境重现 |
| `基础/starter/score_runs.py` | 沿用题包骨架的结果表口径 | 逐例判分表生成 |
| `基础/.gitignore` | 移除 `runs/` | 题目要求运行记录随仓库提交；题包原有设置与之冲突 |
| `进阶/challenge_b/my_engine.py` | **新增** | 进阶 B 的最小修复（兼容 Engine 实现） |
| `进阶/challenge_b/index.html` | 修复对比面板的中文乱码，补「修复前后行为对比」区块 | 题包页面原本只做 JSON 呈现，且对比区块以乱码字符写入 |
| `进阶/runs/test_variants.py`、`test_boundary.py` | 改为与当前工作目录无关，并同时测两个引擎 | 原脚本从仓库根目录运行时 `ModuleNotFoundError: challenge_b` |
| `进阶/runs/regression_and_variants.md` | **新增** | 回归、变体与未解决边界的证据集 |
| `tools/redact_endpoint.py` | **新增** | 提交前移除运行日志中的 Endpoint |
| `decisions.md`、`declaration.md`、`SECURITY.md`、`README.md`、`report.md` | **新增** | 题目要求的交付物 |

**未改动**：`基础/data/`（题目数据）、`进阶/materials/`（公开论文语料）、
以及 `基础/runs/` 与 `进阶/runs/` 中全部原始日志的**内容**
（提交前仅替换了其中的 Endpoint 字段，替换范围与验证方式见 `SECURITY.md`）。

---

## 2. 环境要求

- Python **3.10+**（实测 3.12.14）。基础题与进阶 B 均**只使用标准库**，无第三方依赖。
- 不需要 GPU、数据库或容器。
- 复算已有结果**完全离线**，不需要网络与 API 密钥。

---

## 3. 目录结构

```
.
├── README.md                  本文件：启动、测试、复算、完成度
├── report.md                  整合报告（固定六栏 + E1–E7 证据索引）
├── decisions.md               决策时间线、替代方案、AI 影响
├── declaration.md             AI / 他人 / 完成度声明（统一五项）
├── SECURITY.md                提交安全说明（排除项与脱敏方式）
├── tools/
│   └── redact_endpoint.py     从运行日志中移除 Endpoint
├── 基础/
│   ├── 01_考核题目.md …       题包原文（未改动）
│   ├── data/                  题目数据：cases.json、manifest.json、开发答案
│   ├── starter/               骨架 + 本人实现与新增脚本
│   ├── runs/                  173 条原始运行日志（含失败与重试）
│   ├── results/
│   │   ├── results.csv                       逐例判分表
│   │   ├── per_case_comparison.csv           逐题 × 条件对照
│   │   ├── request_trace_E1.md               端到端追溯记录（E1）
│   │   └── scoring/                          汇总、人工核查、诊断记录
│   └── templates/             题包模板
└── 进阶/
    ├── 00_…06_*.md            题包原文（未改动）
    ├── materials/             公开论文语料（P1/P2）与抽取数据
    ├── challenge_b/           故障样机、修复版引擎与页面
    └── runs/                  离线重放结果、诊断与回归记录
```

---

## 4. 启动与运行

### 4.1 基础题：页面 + 后端

```bash
# 仅预览，不调用模型、不产生费用
python 基础/starter/server.py --config 基础/config.example.json --port 8791
# 浏览器打开 http://127.0.0.1:8791
```

### 4.2 进阶 B：离线故障样机

```bash
# 原始样机（含预埋故障）
python 进阶/challenge_b/server.py --port 8766
# 修复版
python 进阶/challenge_b/server.py --engine my_engine:Engine --port 8767
```

浏览器打开对应端口。页面下方的「修复前后行为对比」会读取
`进阶/runs/baseline.json` 与 `repaired.json`，逐用例列出检索证据、引用定位状态、
语义支持状态、总体状态与缓存命中。

### 4.3 ⚠️ 会产生模型费用的命令

以下命令**只有显式加 `--paid`（或服务端 `--allow-paid`）才会真正发起付费请求**，
且需要环境变量 `ASSESSMENT_API_KEY`。默认行为是 `dry`，不产生费用。

```bash
# 预览将要发送的实际输入（不调用模型）
python 基础/starter/runner.py --case D01 --condition E --dry-run --config 基础/config.local.json

# 会产生费用：一次正式调用
python 基础/starter/runner.py --split evaluation --condition R0 --paid --config 基础/config.local.json
```

> **评审默认请使用已有结果离线回放**，无需运行上述付费命令。
> 仓库中的 `基础/config.example.json` 只有占位说明；真实配置 `config.local.json` 未提交。

---

## 5. 测试与复算（全部离线）

```bash
# 1) 从 173 条原始日志重建 40 次主结果（含 messages 一致性校验）
python 基础/starter/build_main_results.py

# 2) 汇总 R0/R1/R2/K 与 R0 改进配对，产出对照表
python 基础/starter/judge_and_summarize.py

# 3) 进阶 B：语义等价变体检查（两个引擎各跑一遍）
python 进阶/runs/test_variants.py

# 4) 进阶 B：自建边界检查（两个引擎各跑一遍）
python 进阶/runs/test_boundary.py

# 5) 进阶 B：按 CLI 顺序重放全部用例并写出结果文件
python 进阶/challenge_b/run_cases.py --engine challenge:Engine --output 进阶/runs/baseline.json
python 进阶/challenge_b/run_cases.py --engine my_engine:Engine  --output 进阶/runs/repaired.json

# 6) 端到端追溯（需要先按 4.1 启动服务端）
python 基础/starter/trace_one_request.py --port 8791

# 7) 提交安全自查（预演，不写入）
python tools/redact_endpoint.py
```

第 1–6 条命令都不调用模型，第 3–5 条无第三方依赖。

---

## 6. 结果速览

### 基础题：五组条件对照（评测题 T01–T08，每组 8 次）

| 条件 | 合法 JSON | 答案正确 | 准确率（含失败） | 引用语义支持 | 平均耗时 | 截断 |
|---|---|---|---|---|---|---|
| R0 baseline | 7/8 | 7/8 | 87.5% | 7/7 | 4.85s | 1 |
| R1 baseline | 7/8 | 7/8 | 87.5% | 7/7 | 4.12s | 1 |
| R2 baseline | 7/8 | 7/8 | 87.5% | 7/7 | 3.53s | 1 |
| K baseline | 4/8 | 4/8 | 50.0% | 不适用 | 6.04s | 4 |
| R0 improved | 7/8 | 7/8 | 87.5% | 7/7 | 3.93s | 1 |

三个要点：

1. **R0 / R1 / R2 逐题结果完全相同**：同一批段落换三种顺序，答案、引用与失败题目都不变
   （都是 T01 截断）。本样本 8 题上**没有观察到段落顺序效应**。
2. **K 的准确率下降不是「答错」**：4 次失败全部是输出截断（技术失败），
   4 次有效输出都是「证据不足」且经核查正确。K 同时改变了资料量与选择方式，
   按题目要求**不能把差异单独归因于位置**。
3. **改进版没有提高正确率**（7/8 与基线相同，失败题目由 T01 换成 T08），
   而「平均耗时更低」与 8 小时的执行时段差异完全混淆，**不可归因**。
   详见 `基础/results/scoring/timing_confound_check.md`。

汇总文件：`基础/results/scoring/condition_comparison.csv`、`final_summary.csv`；
逐题对照：`基础/results/per_case_comparison.csv`；复算命令见第 5 节第 1–2 条。

> **版本披露（请评委注意）**：上表 40 条主结果全部来自**冻结版本**
> `student.py sha256 = 893e1e16e1343ec2f8742f5aaad960910f821304ed47ba4df11585d269510a36`。
> 仓库当前的 `基础/starter/student.py` 是**更晚的版本**（`3a8c56bb7354…`），
> 提示词在 2026-10-14 被改写过，并据此整批重跑了一次（41 条，存放于
> `retry_runs_main.csv`）。那 41 条按题目要求标注为**冻结后的追加探索**，
> **不参与**主结果、也不用于修正主结果的数字。
> 冻结版的逐字提示词模板已导出为 `基础/results/scoring/frozen_prompt_893e1e16.txt`；
> 每条主结果的实际模型输入逐字保存在 `runs/<run_id>.json` 的 `messages` 字段，
> 因此**重放冻结实验不需要冻结版源码**。完整说明见
> `基础/results/scoring/frozen_version.md`。

### 进阶 B：修复前后逐用例（`runs/baseline.json` vs `runs/repaired.json`）

| 用例 | 修复前 | 修复后 | 性质 |
|---|---|---|---|
| R01 | `[b01]` / valid / ok | 一致 | 回归通过 |
| R02 | `[b01]` / valid / **cache_hit=True** | `[b02]` / valid / cache_hit=False | **主故障已修复**（跨版本缓存污染） |
| R03 | `[]` / invalid | `[b03]` / valid | **第二缺陷已修复**（范围外条目占用 k 名额） |
| R04 | `[b04]` / valid / ok | 证据与状态一致，support 改为如实标注 | 回归通过 |
| R05 | `[b05]` / valid / ok | 一致 | 回归通过 |
| R06 | `[b06]` / valid / ok | 一致 | 回归通过 |
| R07 | `[]` / invalid / **ok** | `[]` / invalid / **invalid_scope** | 未知范围不再显示为正常完成 |

对照组设计、预期依据与未解决边界见 `进阶/runs/regression_and_variants.md` 与
`进阶/runs/cache_diagnosis.md`。

---

## 7. 完成 / 未完成

| 要求 | 状态 | 证据 |
|---|---|---|
| 实现 `prepare_messages` / `improve` | ✅ 已实现并运行 | `基础/starter/student.py` |
| 端到端请求链（页面→后端→日志→原文） | ✅ 已运行 | `基础/results/request_trace_E1.md` |
| 40 次主请求（32 基线 + 8 改进） | ✅ 已运行 | `基础/runs/`、`main_runs_40.csv` |
| 失败与重试全部保留、不覆盖首次结果 | ✅ 已保留 | `retry_runs_main.csv`、`failure_index.md` |
| 逐题核查答案正确性与引用支持 | ✅ 已完成 | `results/scoring/manual_review.csv` |
| 自写判分脚本、注明人工调整 | ✅ 已完成 | `starter/score_runs.py`、`judge_and_summarize.py` |
| 一次诊断（其他原因） | ✅ 已完成 | `timing_confound_check.md`、`failure_index.md` |
| 一次不调模型的顺序/ID 重映射检查 | ✅ 已完成 | `diagnostic_notes.md` |
| ALCE 公开系统观察 | ✅ 已完成（未复现） | `ALCE_observation.md` |
| 进阶 B：故障复现 + 区分原因的干预 | ✅ 已完成 | `cache_diagnosis.md` |
| 进阶 B：2 个回归 + 2 个等价变体 + 1 个边界 | ✅ 已完成 | `regression_and_variants.md` |
| 进阶 B：页面展示请求/快照/证据/验证来源/修复前后 | ✅ 已完成 | `challenge_b/index.html` |
| 三项决定 + AI 影响 | ✅ 已完成 | `decisions.md` |
| AI 声明五项 | ✅ 已完成 | `declaration.md` |
| **R1/R2 判分由本人复核** | ⚠️ **待本人复核** | `reviewer` 列标为「AI辅助初判」 |
| 论文原文命题与位置（E2） | ✅ 已补 | `report.md` 第 2 节 |
| 加大 `max_tokens` 后重跑 | ❌ 未做（有意不做，见 D3） | `decisions.md` D3 |
| 同窗口交错 A/B 重复实验 | ❌ 未做 | `timing_confound_check.md` |
| 语义支持自动判定 | ❌ 未实现，如实标 `not_checked` | `进阶/challenge_b/spec.md` 第 4 条 |
| 多用户 / 多 worker 并发 | ❌ 未测 | `declaration.md` 第 5 项 |
| 题包文件完整性核查（逐文件 SHA256） | ✅ 已做：46 个一致、5 个不一致 | `进阶/runs/pack_integrity.md` |
| `challenge.py` / `server.py` 的原始版本与 diff | ⚠️ **缺口，需本人补** | `进阶/runs/pack_integrity.md`「未解决的缺口」 |

---

## 8. 证据索引

| 索引 | 指向 |
|---|---|
| E1 | 端到端执行路径：`基础/results/request_trace_E1.md`；脚本 `基础/starter/trace_one_request.py` |
| E2 | 论文命题与原文位置：`report.md` 第 2 节 |
| E3 | 逐例原始结果：`基础/results/scoring/manual_review.csv`、`进阶/runs/baseline.json`、`repaired.json` |
| E4 | 竞争解释与区分性检查：`进阶/runs/cache_diagnosis.md`、`基础/results/scoring/failure_index.md` |
| E5 | 反例 / 变体 / 回归与未解边界：`进阶/runs/regression_and_variants.md` |
| E6 | 三项决定及 AI 影响：`decisions.md` |
| E7 | 可定位配置与统一声明：`基础/config.example.json`、`declaration.md`、`SECURITY.md` |

简历与联系方式按题目要求只放在收集表中，不在本仓库。

---

## 附录：题包原始 README

> 以下为考核方随包提供的根 `README.md` 原文，为保留来源信息而附于此。

# ANTLab Agent Tasks

文档阅读与信息核验方向 Agent 项目的应用层开发者招募考核：先完成基础题，再从进阶 A/B/C 中选择一套完成。

**截止时间：北京时间 2026 年 10 月 16 日 23:59（UTC+8）。**

## 从哪开始

1. 先读 [开始阅读.md](开始阅读.md)（总体规则、时间、提交方式）。
2. 基础题（必做）：[基础/README.md](基础/README.md) 与 基础/01_考核题目.md。
3. 进阶题（三选一）：[进阶/README.md](进阶/README.md)，在 A / B / C 中选一套。

## 目录结构

```text
开始阅读.md              入口：总体规则、截止时间、提交方式
基础/                    基础题：12 题（4 开发题有公开答案 + 8 评测题），
                         R0/R1/R2/K 四种输入组织条件；模型 API 自费，
                         主请求量与运行命令见 基础/README.md
进阶/                    进阶题（A/B/C 三选一）
├─ 01_A_研究机制迁移.md        A：主张→证据→支持状态机制迁移与对照
├─ 02_B_系统失效诊断.md        B：源码审查、故障归因与修复
├─ 03_C_产品假设验证.md        C：围绕自选用户任务的产品假设验证
├─ materials/                 两份 CC Attribution 公开论文（P1/P2）及抽取数据
├─ challenge_b/               B 题文档查证样机（30 行 Engine，含预埋故障）
└─ templates/                 声明与整合报告模板
```

## 规则要点

- 准备时间为一周（包含基础题和进阶题）；模型调用使用自己的 API，费用自理；实验输入、原始响应、失败和前后对照须保留在仓库中。
- AI 可辅助阅读、实现和排错；需记录它对关键决定的影响、本人如何核验，以及实际完成和未完成的内容。
- 提交：把作品推送到自己的 GitHub 仓库，并在收集表登记仓库链接与最终 commit SHA；收集表地址与仓库评审账号见 Q 群公布（详见 进阶/05_提交与报告格式.md 与 进阶/06_收集表填写说明.md）。
- 本包不含评委参考答案、评测标签、内部开发教程或商业书籍全文。
- 文件完整性：`基础/文件校验.json` 与 `进阶/文件校验.json` 提供逐文件 SHA256，可自行校验。
