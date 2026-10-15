# 基础与进阶整合报告

报名编号：见收集表登记（提交时与最终 commit SHA 一并登记）　进阶选择：**B（源码审查、故障归因与修复）**
代码版本与数据/配置 hash：见 §3.4

---

## 1 完成概览

| 要求 | 已实现 | 已运行 | 未验证 / 失败 | 证据路径 |
|---|---|---|---|---|
| 基础：实现 `prepare_messages` / `improve` | ✅ | ✅ | — | `基础/starter/student.py` |
| 基础：页面→后端→日志→原文闭环 | ✅ | ✅ | 多用户/并发未测 | `基础/results/request_trace_E1.md` |
| 基础：40 次主请求（32 基线 + 8 改进） | ✅ | ✅ | 8 次输出截断无法评分 | `基础/results/scoring/main_runs_40.csv` |
| 基础：失败与第二次执行全部保留 | ✅ | ✅ | 第二次执行提示词已改，非重复测量 | `failure_index.md`、`frozen_version.md` |
| 基础：逐题核查正确性与引用支持 | ✅ | ✅ | 无（R1/R2 初判已由本人复核确认） | `results/scoring/manual_review.csv` |
| 基础：一次诊断（其他原因） | ✅ | ✅ | 耗时差异不可归因 | `timing_confound_check.md` |
| 基础：一次不调模型的顺序/ID 重映射检查 | ✅ | ✅ | 仅 3 段合成资料 | `diagnostic_notes.md` |
| 基础：公开系统观察（ALCE） | ✅ 阅读 | ❌ 未复现 | 未安装、未运行 | `ALCE_observation.md` |
| 进阶 B：故障复现 + 区分原因的干预 | ✅ | ✅ | — | `进阶/runs/cache_diagnosis.md` |
| 进阶 B：2 回归 + 2 等价变体 + 1 边界 | ✅ | ✅ | 边界仅部分解决 | `进阶/runs/regression_and_variants.md` |
| 进阶 B：页面展示请求/快照/证据/验证来源/修复前后 | ✅ | ✅ | 语义支持仍为 `not_checked` | `进阶/challenge_b/index.html` |
| 三项决定 + AI 影响 | ✅ | — | — | `decisions.md`、`declaration.md` |

### 最重要的三个结论（限定适用范围）

1. **在本样本 8 道评测题上，R0/R1/R2 三种段落顺序没有产生可观察的差异。**
   三者的答案、引用与失败题目逐题相同（都是 T01 截断），且在同一个 2 分钟窗口内执行、题序相同。
   **适用范围**：8 道中文模拟题、7 段资料、单一模型与单一提示词版本、每条件仅 1 次观测。
   这不足以支持任何「顺序不影响模型」的一般性主张。

2. **K 条件准确率减半（4/8）不是「答错」，而是资料覆盖与输出截断的结果。**
   4 次失败全部是技术失败（正文为空），4 次有效输出都是「证据不足」且经核查正确。
   K 同时改变了资料量与选择方式，按题目要求**不能把差异单独归因于位置**。

3. **进阶 B 的主故障是缓存身份不足以区分资料版本，而修复同时保住了「等价输入可复用」。**
   对照实验里只有「是否复用缓存」一个变量变化：新引擎单独跑 R02 得到 v2 的 b02，
   同一引擎先跑 R01 再跑 R02 则命中旧结果得到 v1 的 b01。
   修复后 R02 正确、R03 的范围名额问题同时修好、R07 的状态如实返回，其余 4 项回归逐字段不变。

---

## 2 阅读到命题

### 2.1 主论文的一项命题（含原文位置）

**文献**：Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua,
Fabio Petroni, Percy Liang. *Lost in the Middle: How Language Models Use Long Contexts.*
TACL Vol. 12 (2024), pp. 157–173；DOI 10.1162/tacl_a_00638。
实际阅读版本：https://arxiv.org/html/2307.03172v3 （v3，2023-11-20 修订）。

**命题**：在检索增强式问答中，**关键信息在输入上下文中的位置会影响模型使用该信息的能力
——位于中部时表现最差，形成 U 型曲线**。

**原文位置与引文**

- §2.3（小节标题 *Model performance is highest when relevant information occurs at the
  beginning or end of its input context*）：
  > "In particular, we see a distinctive U-shaped performance curve—models are often much better
  > at using relevant information that occurs at the very beginning (primacy bias) and very end of
  > contexts (recency bias), and suffer degraded performance when forced to use information within
  > the middle of its input context. For example, GPT-3.5-Turbo's multi-document QA performance can
  > drop by more than 20%—in the worst case, performance in 20- and 30-document settings is lower
  > than performance without any input documents (i.e., closed-book performance; 56.1%)."
- §1（把稳健性表述为**评估建议**，而非已证定理）：
  > "...to claim that a language model can robustly use information within long input contexts,
  > it is necessary to show that its performance is minimally affected by the position of the
  > relevant information in the input context..."

**作者证明的 / 只观察到的 / 推测的**

| 类别 | 内容 |
|---|---|
| **证明**（在其测试条件下可复现，含 Figure 5 与准确率数字） | 多文档问答与键值检索中，关键信息位置变化会显著改变准确率；多文档问答呈 U 型 |
| **只观察到、且有明确反例** | 「多种模型与任务普遍如此」**不成立**：Claude-1.3 与 Claude-1.3(100K) 在键值检索全部长度近乎完美；LongChat-13B(16K) 在 140 键值设置呈不同趋势；Flan-UL2 在 2048 token 训练窗内最好/最差仅差 1.9% |
| **推测**（作者自己标为 hypothese） | 成因。§4.1："We **hypothesize** that encoder-decoder models may make better use of their context windows because their bidirectional encoder allows processing each document in the context of future documents..."；§4.3："We **hypothesize** that non-instruction fine-tuned language models learn to use these long contexts from similarly-formatted data..." |

**必须澄清一点**：论文**没有**把 U 型归因于位置编码或注意力模式，也没有做相应实验。
位置编码只在 §2.2 作为**模型描述**出现（MPT-30B-Instruct 用 ALiBi、LongChat-13B 用
condensed rotary PE）。§6.3 只有一句"惊讶"式评论：
> "Observing a serial-position-like effect in language models is perhaps surprising, since the
> self-attention mechanisms underlying Transformer language models is technically equally capable
> of retrieving any tokens from their contexts."
把它写成"作者认为原因是位置编码"属于编造。另外，该论文**没有独立的 Limitations 小节**。

**本题保留与改变的条件**

| 论文 | 本题 | 是否可直接迁移 |
|---|---|---|
| 操纵**唯一含答案文档**在 k 篇文档中的位置 | 操纵**同一批 7 段资料的整体顺序**，没有"唯一关键段落"标签 | ❌ 不是同一构造。论文脚注 4 显示随机化干扰文档顺序不改变趋势，恰说明其效应来自关键文档位置而非列表顺序先验 |
| 因变量只有 accuracy | 还要看**引用语义支持**与**客户端完整耗时** | ❌ 论文只把延迟与成本作定性代价提及（§5），未把耗时当作被测量的因变量 |
| 效应在数千 token 的长上下文下测得（10/20/30 篇文档、75/140/300 键值对） | 7 段中文模拟资料 | ⚠️ 很可能落在"上下文短、效应小"的区间，**不能预设**会看到 U 型 |
| MPT-30B / LongChat-13B / GPT-3.5-Turbo(0613) / Claude-1.3，贪心解码 | 单一模型经 Chat Completions 非流式接口 | ❌ 模型与解码都不同，且非流式无法拆分首 token 延迟 |
| 唯一可迁移的是评估原则（§1）：判断稳健性要看最好/最差差距是否最小 | 用于设计 R0/R1/R2 的对照 | ✅ 这是评估协议，不是对本次数据的结果预测 |

### 2.2 随包真实语料的规则（含原文位置）

题包提供的两份 CC Attribution 公开论文，原文与来源见 `进阶/materials/sources.json`：

- **P1**：Sandve, Nekrutenko, Taylor, Hovig (2013). *Ten Simple Rules for Reproducible
  Computational Research.* PLOS Computational Biology 9(10): e1003285，
  DOI 10.1371/journal.pcbi.1003285。许可文字为 CC Attribution（原文未标版本，本报告不推定）。
- **P2**：Rule et al. (2019). *Ten simple rules for writing and sharing computational analyses
  in Jupyter Notebooks.* PLOS Computational Biology 15(7): e1007007，
  DOI 10.1371/journal.pcbi.1007007。许可为 **CC BY 4.0**。

题包 `进阶/02_B_系统失效诊断.md` 要求阅读「P1 规则 1/5/9 与 P2 规则 6/7」。
经核对 `sections.json`、`P1.xml`/`P2.xml` 的 `<title>Rule N: …</title>` 与 `04_阅读材料与项目背景.md`，
**「规则」指论文自身编号的 Rule N**（题包未附映射说明，本报告按论文编号解释）：

| 规则 | 标题与要点（原文引用，位置为 `P1.xml`/`P2.xml` 行号） |
|---|---|
| **P1 Rule 1** | *For Every Result, Keep Track of How It Was Produced.*（P1.xml:65–68）<br>"For every involved step, you should ensure that every detail that may influence the execution of the step is recorded. If the step is performed by a computer program, the critical details include the name and version of the program, as well as the exact parameters and inputs that were used."（P1.xml:66） |
| **P1 Rule 5** | *Record All Intermediate Results, When Possible in Standardized Formats.*（P1.xml:81–82）<br>"Quickly browsing through intermediate results can reveal discrepancies toward what is assumed, and can in this way uncover bugs or faulty interpretations that are not apparent in the final results."（P1.xml:82） |
| **P1 Rule 9** | *Connect Textual Statements to Underlying Results.*（P1.xml:93–97）<br>"you will have to connect a given textual statement (interpretation, claim, conclusion) to the precise results underlying the statement. Making this connection when it is needed may be difficult and error-prone, as it may be hard to locate the exact result underlying and supporting the statement from a large pool of different analyses with various versions."（P1.xml:95） |
| **P2 Rule 6** | *Use version control.*（P2.xml:222–224）<br>"since notebooks contain code and code inevitably contains bugs, being able to determine the history of when a given bug you have discovered was introduced to the code versus when it was fixed—and thus what analyses it may have affected—is a key capability in scientific computation."（P2.xml:223） |
| **P2 Rule 7** | *Build a pipeline.*（P2.xml:227–230）<br>"Once a notebook has been developed, it can be parameterized … Such notebooks can be used not only interactively but also as command-line tools that can be executed automatically—a great boon for pipelines!"（P2.xml:230） |

> **证据等级说明**：P1/P2 **不是**引文评价论文；两篇里 "citation" 只出现在版权/引用块。
> 上面的规则是**可复现性与工程规范**，本次用它支撑"留痕、可复算、版本记录"的做法，
> 不把它当作引用支持判定的理论依据。

### 2.3 公开系统：ALCE（观察性质须如实标注）

对象：Gao, Yen, Yu, Chen. *Enabling Large Language Models to Generate Text with Citations.*
EMNLP 2023（https://aclanthology.org/2023.emnlp-main.398/ ，代码
https://github.com/princeton-nlp/ALCE ）。

**完成方式**：阅读论文摘要与公开仓库说明，观察其评估维度与引用核查思路。
**没有安装 ALCE、没有下载其数据集、没有运行其模型，本报告不声称完成代码复现。**
完整记录见 `ALCE_observation.md`。

借鉴到本项目的三点：

1. 生成质量分成流畅度、**正确性**与**引用质量**等维度，而不是一个总分代表全部质量
   → 本项目把 `answer_correct` 与 `citation_support` **分开判断**。
2. 引用质量不只是"引用格式是否存在"，还要检查引用的文档是否**支持**对应陈述
   → 本项目的 `citation_ids_in_input` 只检查 ID 是否在输入内，**不能**替代语义支持核查。
3. 自动评估能扩大规模但需留意评估器本身的局限，人工核查可补充个案解释
   → 本项目保留 `review_reason` 逐例理由，并保留原始响应与失败记录。

**不可直接类比**：ALCE 使用其论文定义的数据集、任务与自动评估指标；本项目使用中文模拟文档、
8 道正式题与人工语义核查。两者数据、任务与指标实现不同，**分数不可比较**，也未复现其结果。

### 2.4 学习材料实际改变的两个决定

**决定一（P1 Rule 9 → 证据链的组织方式）**
Rule 9 要求把文本陈述连接到支撑它的**精确结果**，并指出"在需要时才去建立这个连接会困难且易错"。
据此决定：每一条结论都必须能落到 `run_id`。因此 `results/scoring/manual_review.csv` 的每一行
都带 `run_id`，报告里的每个数字都给出汇总文件、复算命令与所用 run ID。
这一步直接暴露了一个真实缺陷：原 `R0_improved_manual_review.csv` 的 `run_id` 列**全为空**，
追溯链断裂；重建后它与上游记录一致，该文件被标记为已被取代。

**决定二（P1 Rule 5 + P2 Rule 7 → 汇总表改为由脚本从原始日志重建）**
Rule 5 指出浏览中间结果能发现"在最终结果里看不出来的 bug 或错误解释"；
Rule 7 要求把分析做成可自动执行的管线。据此决定：不再把 `results.csv` 当唯一事实来源，
而是新增 `build_main_results.py` 从 `runs/*.json` **重新推导**全部客观字段。
这样做的直接收益有三个：
(a) 发现并量化了 `messages` 与清单的一致性（116/116 一致）；
(b) 发现 41 条所谓"重试"其实用了**改后的提示词**（`student_sha256` 不同），
原结论"同参数重试"被撤回，见 `frozen_version.md`；
(c) 逐题配对差值可复算，从而使"改进版更快"这一说法被证伪为不可归因
（见 `timing_confound_check.md`）。

> **第三项决定**（题目要求三项，基础题另有两项见 `decisions.md` D2/D3）：
> 依据 Lost-in-the-Middle §1 的评估原则（判断稳健性要看最好/最差差距），
> 决定在汇总表中**同时给出** `accuracy_all` 与 `accuracy_valid_only` 两个口径。
> 只报后者会把技术失败掩盖成"模型都答对了"（K 在两个口径下分别是 50.0% 与 100%）。

---

## 3 预期与实验

### 3.1 假设与竞争解释

| 假设 | 竞争解释 | 自变量 | 因变量 / 分母 | 控制 / 基线 | 区分观察 | 否定条件 |
|---|---|---|---|---|---|---|
| H1：同一批资料换整体顺序会改变模型使用信息的效果 | H1′：四种条件的差异来自资料量与选择方式，而非位置 | 条件（R0/R1/R2 为顺序，K 为选段） | 答案正确性（分母 8 题，技术失败计入）、引用语义支持、客户端完整耗时 | 同批资料、同模型、同参数、同题序；基线为 R0 | R1/R2 与 R0 的逐题答案是否出现差异 | 若 R1/R2 与 R0 逐题完全相同，则本样本上无顺序效应 |
| H2：按问题与段落文本的关键词/字段重合度重排，能改善证据使用 | H2′：重排只是改变了输入顺序，效果来自随机性 | 版本（baseline / improved） | 答案正确性、引用语义支持、耗时、额外调用（均为 0） | 同一资料集合，只改顺序；与 R0 基线逐题配对 | 8 对配对差值是否集中且同向 | 若正确率或引用支持下降，或用例间差值方向不一致 |
| H3（B）：R02 返回旧版本是因为**缓存身份不足以区分资料版本** | H3′：检索或范围筛选本身就错 | 是否复用缓存（新引擎单独跑 / 同引擎先跑 R01 再跑 R02） | evidence 的 ID 与快照、`cache_hit`、`locator_status` | 同一 `corpus` 与 `draft`，只有引擎实例与调用序列不同 | 新引擎单独跑 R02 是否返回 b02 | 若新引擎单独跑 R02 仍返回 b01 或错误版本，则缓存不是原因 |

### 3.2 开发与评测的接触说明

- **开发题 D01–D04** 有公开参考答案，用于调试实现与选择方案；共 20 次直接付费调用 + 15 次
  第二次执行调用，**不计入 40 次主结果**，单独存放于 `dev_runs_paid.csv` / `retry_runs_dev.csv`。
- **评测题 T01–T08** 只有输入。本轮**没有**用开发答案去构造答案，
  `student.py` 的 `prepare_messages` / `improve` 只接收问题与本次可见段落；
  `runner.py` 会校验 `improve` 的输出是原始段落的子集且不重复。
- **接触情况如实披露**：评测集可见，作答过程中本人可以查看模型输出并做人工判分，
  这本身构成了对评测集的接触。因此**本报告不声称盲测**；
  40 次主结果在 2026-10-10 一次性完成后即冻结，之后没有据此调参。
  10-14 的提示词改写与整批重跑已标注为**冻结后的追加探索**，未混入主结果。

### 3.3 停止条件

- 主结果：T01–T08 × {R0,R1,R2,K} 各 1 次首次尝试 + R0 改进 8 次，共 **40 次**即停止，
  不因失败而追加调用。
- 第二次执行：因提示词改写而整批重跑一次即停止，结果单独存放，不用于修正主结果。
- 进阶 B：主故障与第二缺陷各自定位到唯一原因、且回归全部通过即停止。

### 3.4 冻结时间与版本

| 项 | 值 |
|---|---|
| 冻结时间 | 2026-10-10 02:12:54Z（首次主请求）— 10:29:14Z（最后一次改进请求） |
| **冻结的 `student.py` sha256** | **`893e1e16e1343ec2f8742f5aaad960910f821304ed47ba4df11585d269510a36`**（40 条记录唯一取值） |
| 数据 sha256 | `c37cda40ada89a18630dd7be098672f7e942e6f57e6199fe1aa2d6046e2b4961`（`data/cases.json`） |
| 数据版本 | `basic-context-v1.2`（`data/manifest.json`，`fictional: true`） |
| 模型与参数 | `deepseek-v4-1-flash-260910`，`temperature=0`、`max_tokens=1024`、`timeout_seconds=90` |
| 配置路径 | `基础/config.example.json`（占位）；真实配置 `config.local.json` 未提交，密钥在环境变量 `ASSESSMENT_API_KEY` |

> **版本不一致披露**：仓库当前的 `基础/starter/student.py` 哈希是
> `3a8c56bb7354a5e7d2b7f63be69a5d776c8cf9e8a6557688c9e2ba35e9834d43`，
> **不是**冻结版本。冻结版与 10-14 版的实际 `messages` 逐条不同（提示词被改写）。
> 41 条第二次执行因此按追加探索处理，不参与主结果。
> 冻结版的提示词模板已导出为 `基础/results/scoring/frozen_prompt_893e1e16.txt`，
> 而每条主结果的实际模型输入已逐字保存在 `runs/<run_id>.json` 的 `messages` 字段，
> 因此**重放冻结实验不需要冻结版源码**。详见 `frozen_version.md`。

> **题包文件完整性核查**：用题包自带的逐文件 SHA256 核对，**47 个文件完全一致**
> （含全部题目数据、题面、`challenge_b/spec.md` 与归位后的 `challenge.py`），
> **4 个文件不一致**：`基础/.gitignore`、`基础/starter/student.py`、
> `进阶/challenge_b/index.html`、`进阶/challenge_b/server.py`，
> **四者都是本次或按要求应由候选人完成的改动，且都留有记录**
> （`server.py` 的题包原件完整保留为 `server_before_comparison.py`，字节一致）。
>
> 核查中还发现并修复了一处严重不一致：工作副本里的 `challenge.py` 曾被改过，
> 把 `spec.md` 第 5 条的**预埋故障**（缓存键只含 query）改掉了，
> 导致 `runs/baseline.json` 无法复现。已按题包原件归位，
> 归位后回放与基线记录 **7/7 用例逐字段一致**；`baseline.json` 本身未改写。
> 详见 `进阶/runs/pack_integrity.md`。
> 需要强调的是：**判据 `spec.md` 始终未被改动**，本次 B 的全部结论都是对照它得出的。

---

## 4 实现与复现

### 4.1 一条完整请求链（证据 E1）

```
页面 基础/starter/index.html
  → POST /api/run（请求头带 X-Assessment-Session 会话令牌）
  → 基础/starter/server.py  Handler.do_POST（校验令牌与模式；paid 需 --allow-paid）
  → 基础/starter/runner.py  execute()
        · prepare()：取 data/cases.json 原始段落，按 condition 决定顺序
        · variant=improved 时调用 student.improve()，并校验只做重排/选择
        · student.prepare_messages() 组装 messages
        · 记录 data_sha256 / student_sha256 / messages / selected_passage_ids
        · dry 不调用模型；paid 走 provider.call_model()
  → 基础/runs/<run_id>.json（UUID 文件名，永不覆盖）
  → data/cases.json 的段落原文
```

**实际运行结果**（2026-10-15，`dry` 模式，不产生费用）：
页面 1836 字节、无令牌请求被拒（HTTP 403）、带令牌请求返回 HTTP 200 与
`run_id=0ff168e9-e8b7-4b07-87be-641f905e1990`，该日志中的 7 段 ID 与原文
**全部可追到 `data/cases.json`**。完整输出见 `基础/results/request_trace_E1.md`，
复现脚本 `基础/starter/trace_one_request.py`。

**关键模块**

| 模块 | 职责 |
|---|---|
| `基础/starter/runner.py` | 取数据、按条件组织段落、调用 `student`、写运行记录 |
| `基础/starter/student.py` | 本候选人实现：`prepare_messages()` 与 `improve()` |
| `基础/starter/provider.py` | HTTPS + Bearer + Chat Completions；不保存错误页正文以免收录凭据 |
| `基础/starter/build_main_results.py` | 从原始日志重建 40 次主结果，校验 messages 一致性 |
| `基础/starter/judge_and_summarize.py` | 五组对照、逐题配对、改善配对差值 |
| `进阶/challenge_b/challenge.py` | 原始样机 Engine（含预埋故障，不改写） |
| `进阶/challenge_b/my_engine.py` | 本候选人实现的最小修复 Engine |
| `进阶/challenge_b/server.py` + `index.html` | 离线重放 UI 与 `/api/comparison` 修复前后对比 |

### 4.2 一次实际请求能否从界面追到日志和原文

可以。以 R0 基线 T06（答案 25%）为例：
`manual_review.csv` 中该行 `run_id=01111189-bddf-40a8-bade-e9ca150c468c`
→ 打开 `runs/01111189-….json`，可见实际 `messages`、`selected_passage_ids`、
`config`、`response`、`usage`、`elapsed_seconds`、`http_status`
→ 答案 25% 由 `response.choices[0].message.content` 解析（`build_main_results.py` 的 `parse_output()`）
→ 判分依据是 P873502（60 项中 8 项超时、7 项格式不合法）与 P721388（两类均计技术失败、
分母为 60 项）两段原文，可在 `data/cases.json` 按 ID 检索。
**复算命令**：`python 基础/starter/build_main_results.py`（只读日志，不调用模型）。

### 4.3 用到 AI 与开源的部分

- **AI**：`student.py` 的提示词初版、判分脚本初版由 ChatGPT 协助；本轮的日志重建、
  R1/R2 判分初判、诊断、进阶 B 的缓存身份修正与页面修复、本报告起草由 DeepSeek Harness 协助。
  逐项对应见 `declaration.md` 第 3 项。AI 未用于生成模型回答、编造引用或修改原始日志。
- **开源/公开资料**：只作为**阅读对象**使用（Lost in the Middle、P1/P2、ALCE）。
  **没有安装或复现其中任何一个**，代码与数据依赖只有题包自带内容与 Python 标准库。
- **源码基点**：题包原始状态；相对骨架的逐文件改动见 `README.md` 第 1 节。

### 4.4 模型、配置与环境；Token 量级

真实 API 模型名称：**`deepseek-v4-1-flash-260910`**（116 次付费调用全部使用该模型）。
配置路径：`基础/config.example.json`（占位）；密钥只在环境变量 `ASSESSMENT_API_KEY`。
环境：Python 3.12.14 / Windows，基础题与进阶 B 均**只用标准库**。

Token 消耗量级（由 `usage` 字段汇总，非估算）：

| 分组 | 次数 | prompt | completion | 合计 |
|---|---|---|---|---|
| 40 次主结果 | 40 | 59,126 | 22,807 | 81,933 |
| 第二次执行（评测题） | 41 | 60,832 | 22,494 | 83,326 |
| 开发题调用 + 第二次执行 | 35 | 34,683 | 15,033 | 49,716 |
| **合计** | **116** | **154,641** | **60,334** | **214,975** |

量级约 **21.5 万 tokens**；另有 57 次 `--dry-run` 与 1 次 `--mock`，不产生费用。

---

## 5 结果

### 5.1 基础题：五组条件对照（评测题 T01–T08）

汇总文件 `基础/results/scoring/condition_comparison.csv`；
**复算命令**：`python 基础/starter/build_main_results.py && python 基础/starter/judge_and_summarize.py`。
分组分母为 8，每个条件计入其 8 条首次尝试（含技术失败）。

| 条件 | 合法 JSON | 答案正确 | 准确率（含失败） | 仅计技术成功 | 引用语义支持 | 平均秒 | 中位秒 | 截断 | 计入分母的 run ID（首条/末条） |
|---|---|---|---|---|---|---|---|---|---|
| R0 baseline | 7/8 | 7/8 | 87.5% | 100% | 7/7 | 4.85 | 4.33 | 1 | `cba12f60…` → `5c12b3af…` |
| R1 baseline | 7/8 | 7/8 | 87.5% | 100% | 7/7 | 4.12 | 3.30 | 1 | `3dabb4f6…` → `15dccf19…` |
| R2 baseline | 7/8 | 7/8 | 87.5% | 100% | 7/7 | 3.53 | 3.30 | 1 | `b04bda85…` → `9b3e91fc…` |
| K baseline | 4/8 | 4/8 | 50.0% | 100% | 不适用 | 6.04 | 6.97 | 4 | `efa68b86…` → `a61b59df…` |
| R0 improved | 7/8 | 7/8 | 87.5% | 100% | 7/7 | 3.93 | 3.46 | 1 | `a31834d7…` → `6b8b604b…` |

> 上表的 run ID 列是该条件内**按 `utc` 排序的首条与末条完整 run ID 前缀**，
> 完整 40 个 ID 见 `results/scoring/manual_review.csv` 的 `run_id` 列。

> 上表的完整 40 个 run ID 见 `results/scoring/manual_review.csv` 的 `run_id` 列，
> 逐题答案、引用与理由见同表的 `answer` / `citations` / `review_reason` 列。
> 任意一个 run ID 都能在 `runs/` 中找到实际输入、原始响应与当时配置。

**逐题对照**（附件 `基础/results/per_case_comparison.csv`）：R0/R1/R2 三列在 8 行上完全相同；
K 列在 T04/T06/T07/T08 上为空（截断），其余 4 题均为「证据不足」；
R0 改进列与 R0 基线列只在 T01（改进后变为正确）与 T08（改进后变为截断）两处不同。

### 5.2 基础题：R0 基线与改进版的同题配对

汇总文件 `基础/results/scoring/improvement_pairing.csv`。

| 题号 | 基线 run ID | 改进 run ID | 基线答案 | 改进答案 | 支持（基线→改进） | 基线秒 | 改进秒 | 差值 |
|---|---|---|---|---|---|---|---|---|
| T01 | `03473df0…` | `e7ed6cce…` | （截断） | S24 | 不适用→是 | 7.04 | 6.04 | −1.00 |
| T02 | `cba12f60…` | `a31834d7…` | 76% | 76% | 是→是 | 3.92 | 3.83 | −0.09 |
| T03 | `3a77ba4d…` | `12ba9ab1…` | 2.6 | 2.6 | 是→是 | 3.51 | 3.35 | −0.16 |
| T04 | `93c7332b…` | `a92a226f…` | 流程乙 | 流程乙 | 是→是 | 2.85 | 3.07 | **+0.21** |
| T05 | `18c52a9a…` | `a673b25e…` | 证据不足 | 证据不足 | 是→是※ | 4.33 | 3.46 | −0.87 |
| T06 | `01111189…` | `4a3f8993…` | 25% | 25% | 是→是 | 8.14 | 2.81 | **−5.34** |
| T07 | `709b57b1…` | `d8d7dd22…` | 丙 | 丙 | 是→是 | 3.42 | 3.04 | −0.38 |
| T08 | `5c12b3af…` | `6b8b604b…` | K17 | （截断） | 是→不适用 | 5.55 | 5.83 | **+0.28** |

※ T05 的引用支持存在两种判断口径（`R0_manual_review.csv` 记"是"、旧 `R0_improved_manual_review.csv` 记"否"）。
**本人已于 2026-10-15 裁定采用「是」**，依据是题目「证据不足时引用列出支持这种判断的检查来源」
——P452207 就是该检查来源，故改进版的引用语义支持为 **7/7**。
两份旧文件的冲突作为判分历史保留在仓库中；若改用严格逐条口径则为 6/7，
即**改进在覆盖上出现一次退步**。见 `decisions.md` D3。

**结论**：答案正确数基线与改进版**同为 7/8**，失败题目由 T01 换成 T08；
8 个耗时差值合计 −7.35 秒，其中 **T06（−5.34）与 T01（−1.00）占 86%**，
且有 3 题改进版更慢。**不声称改进提高了正确率或降低了耗时。**

### 5.3 进阶 B：同用例修复前后配对

配对文件 `进阶/runs/baseline.json` 与 `repaired.json`（相同数据、相同 CLI 顺序与
`reset_before` 语义）；**复算命令**：`python 进阶/challenge_b/run_cases.py --engine my_engine:Engine --output 进阶/runs/repaired.json`。

| 用例 | 修复前 evidence / locator / support / status / cache_hit | 修复后 | 判定 |
|---|---|---|---|
| R01 | `[b01]` / valid / supported / ok / False | `[b01]` / valid / not_checked / ok / False | 回归通过 |
| R02 | `[b01]` / valid / supported / ok / **True** | `[b02]` / valid / not_checked / ok / False | **主故障已修复** |
| R03 | `[]` / invalid / not_checked / ok / False | `[b03]` / valid / not_checked / ok / False | **第二缺陷已修复** |
| R04 | `[b04]` / valid / supported / ok / False | `[b04]` / valid / not_checked / ok / False | 回归通过 |
| R05 | `[b05]` / valid / supported / ok / False | `[b05]` / valid / not_checked / ok / False | 回归通过 |
| R06 | `[b06]` / valid / supported / ok / False | `[b06]` / valid / not_checked / ok / False | 回归通过 |
| R07 | `[]` / invalid / not_checked / **ok** / False | `[]` / invalid / not_checked / **invalid_scope** / False | 状态区分已修复 |

七项用例中只有 R02、R03、R07 三处行为变化，其余四项逐字段一致。
`support_status` 由 `supported` 改为 `not_checked` 是**评价口径的修正**，不是修复带来的提升：
原实现把"引用 ID 属于本次证据"直接当作"语义已被支持"，而源码中不存在任何语义比较
（`challenge.py` 中 `'support_status': 'supported' if valid else 'not_checked'`）。
一个可复现的具体反例是 **R04**：draft 声称"点击取消就保证 GPU 立即停止计算并释放资源"，
而其证据 b04 原文为"客户端取消仅停止本地结果展示；本文没有测量服务端是否释放 GPU 计算资源"
——**语义相反**，原实现却标为 `supported`。

### 5.4 判别实验、反例、变体与回归

**主故障的判别实验**（详见 `进阶/runs/cache_diagnosis.md`）

| 对照 | 输入 | 结果 | 说明 |
|---|---|---|---|
| 对照一 | 新引擎**只**执行 R02 | `cache_hit=false`，evidence=`b02`，答案 12 秒 | 无缓存时结果正确 |
| 对照二 | 另一新引擎**先** R01 **再** R02 | R01 `cache_hit=false`（30 秒 / b01）；R02 `cache_hit=true`，答案仍 30 秒、证据仍 b01 | 只有缓存状态一个变量变化 |

**反例（必须同时看数据）**

- 不是所有题都会被截断：同一条件内 7/8 成功，只有 T01 在 R0/R1/R2 三个顺序下都失败
  ——说明失败与**题目**相关，而**与段落顺序无关**。
- 一个提示词版本下失败并不等于另一个版本也失败：改了提示词后整批重跑，
  8 个原有失败用例中有 6 个产出合法输出，但**这 6 次不是同条件重复测量**
  （提示词已改），因此不能据此声称"原失败是随机的"。见 `failure_index.md` 第四节。
- 「引用 ID 有效」不等于「内容被支持」：R04 即反例（见 §5.3）。

**语义等价变体**（`进阶/runs/test_variants.py`，两个引擎各跑一遍）

| 变体 | 改了 | 原始样机 evidence / locator / cache_hit | 修复版 |
|---|---|---|---|
| V1 原始 | — | `[b05]` / valid / False | `[b05]` / valid / False |
| V2 查询改大写 | 大小写 | `[b05]` / valid / **True** | `[b05]` / valid / **True** |
| V3 反转 doc_ids | 集合顺序 | `[b05]` / valid / **True** | `[b05]` / valid / **True** |

两引擎下三个变体的（证据集合, 定位状态）都只有一个取值 → 等价性成立。
这一项同时证明修复**没有用"关闭缓存复用"换取安全**。

**回归**：R01（单文档单快照）、R05（多文档范围排序）预期均由 `spec.md` 第 1、2 条推出，
实测逐字段不变；R04、R06 同样不变。

**未解决边界**（`进阶/runs/test_boundary.py`）：doc_ids=`beta`、snapshot=`v999`（不存在）。
两个引擎都**没有**跨快照回退（未把 v1 的 b05 当证据），修复版把 `status` 从 `ok` 改为
`invalid_scope`。但 `spec.md` 第 3 条要求的"引用缺失与越界分别标识"只实现了三态
（`missing`/`invalid`/`valid`）而无专门用例固定；`scoped` 非空但正分证据为空时仍返回 `ok`。
两处均登记为**未解决**。

### 5.5 失败、未检查与代价

- **基础主结果 8/40 无法评分**（`finish_reason=length`、正文为空），按题目要求计入分母。
  机制是 `max_tokens=1024` 被推理部分耗尽（13 条的
  `completion_tokens = reasoning_tokens = max_tokens = 1024`）。详见 `failure_index.md`。
- **参数不一致 1 处**：第二次执行中有 1 条 `max_tokens=512`（其余 80 条为 1024）。
- **版本不一致 1 处**：第二次执行的 `student_sha256` 与冻结版不同（提示词已改）。
- **未检查**：`support_status` 的自动判定未实现，基础题与 B 样机都如实标 `not_checked`；
  多用户/多 worker 并发未测；服务端分段时间（排队、prefill、decode）未观测。
- **代价**：13 条截断各消耗 1024 个输出 token 而无产出；截断请求耗时反而偏高
  （6.7–9.0 秒），因此耗时数据中混有"生成到一半被砍"的样本。

### 5.6 尚不能排除的解释

1. **R0/R1/R2 的耗时递减**（4.85 → 4.12 → 3.53 秒）既可能来自服务端时段漂移，
   也可能来自段落顺序；8 个观察、无重复、题序固定，**无法区分**。
   但 K 紧接 R2 执行（相隔 17 秒）耗时反而升到 6.04 秒，说明并非单纯的时段上升趋势。
2. **改进版耗时更低**：与 8 小时的时段差异完全混淆，**不可归因**。
3. **K 的截断率更高**：与"资料不足时模型在推理里反复查找"相符，但本轮没有做能区分
   该解释与"K 的提示词更短导致输出更长"等替代解释的实验。
4. **`temperature=0` 下输出仍不确定**：两版提示词下都观察到 `reasoning_tokens` 的大幅波动
   （同题从 393 到 1024），但本轮没有同条件重复测量，因此不对随机性作任何主张。

---

## 6 决定与后续

### 6.1 保留 / 修改 / 停止

| 对象 | 决定 | 证据 |
|---|---|---|
| 关键词/字段重排的改进方法 | **保留为待评估**，不声称提升 | 正确数与基线同为 7/8；配对差值方向不一致（3 题更慢） |
| 输出上限 1024 | **保留冻结设置** | 事后改参数会让基线与改进不同条件；如需重做须整批重跑并标注追加探索 |
| 主故障的修复方案（缓存身份按语义规范化） | **保留** | R02 修复、R03/R07 同时修好、4 项回归不变、等价变体仍可复用缓存 |
| 直接删除缓存的做法 | **停止（舍弃）** | 会把"等价输入可复用"的契约一并去掉，使变体检查失去对象 |
| 语义支持自动判定 | **暂不实现**，如实标 `not_checked` | 无独立验证手段时冒充"已验证"是更危险的失败（R04 即反例） |
| 「改进版更快」这一结论 | **停止使用** | 与执行时段完全混淆，且 86% 的差值来自两道题 |

### 6.2 两个相关系统的具体比较与来源

| 项 | ALCE | Semantic Reader |
|---|---|---|
| 类型 | 学术基准 + 开源实现 | 研究论文 + 官方在线阅读界面 |
| 来源 | 论文 https://aclanthology.org/2023.emnlp-main.398/ ；代码 https://github.com/princeton-nlp/ALCE | 论文 https://arxiv.org/abs/2303.14334 ；入口 https://openreader.semanticscholar.org/ |
| 服务谁 | 评估方：需要可规模化比较"带引用的生成" | 读者：需要在论文原文里定位与阅读 |
| 输入 / 输出 | 问题 + 检索文档 → 生成文本 + 引用，再由自动指标打分 | PDF 论文 → 结构化阅读界面与原文区域定位 |
| 已披露证据 | 评估维度（流畅度、正确性、引用质量）；`eval.py` / `compute_autoais` 检查句子与引用文档的支持关系 | 论文与官方入口披露的是阅读交互与定位；**本次未访问、未亲测** |
| 适用限制 | 指标实现与数据集绑定；自动评估器本身有局限 | 面向论文阅读场景；**未亲测，无法评价其工程限制** |
| 本项目可借鉴 | **正确性与引用支持分开评价**；保留逐例理由 | 关注"原文定位与阅读交互"，与本项目的 `page` / 段落 ID 定位同向 |
| 不照搬 | 不复现其 NLI 整套指标，分数不可比 | 不把其界面设计当作本项目已验证的能力 |
| **本报告的证据等级** | 阅读论文摘要与仓库说明，**未安装、未运行、未复现** | **未访问**，仅依据题包 `04_阅读材料与项目背景.md` 第 27 行的说明与论文入口；属"文献/官方分析"，非亲测 |

两者面向的**不是同一类用户**：ALCE 服务评估者，Semantic Reader 服务阅读者。
本项目的用户任务是"在相近文档记录中核对证据并给出可追溯的引用"，
因此**把 ALCE 的评价结构借来当作核查口径**（正确性与引用支持分开），
而**把 Semantic Reader 的定位交互当作呈现层的方向**。两者都不是本项目的竞品。

### 6.3 应用端可见 / 服务端未知；下一项联合实验

**应用端可见**：问题与本次可见段落、条件与版本、模型与参数、原始响应与 `usage`、
客户端完整耗时、`data_sha256` / `student_sha256`、缓存的 `request_id` 与 `cache_hit`。

**服务端未知**：排队时间、prefill 与 decode 的分段耗时、KV Cache 命中、
推理资源是否真正释放、并发下的行为。本次只能测量客户端完整耗时，
它包含网络、排队、服务与输出传输，**无法拆分**。

**下一项应用—推理联合验证问题（可执行方案）**

> 当页面要求"每条引用都必须给出语义支持判定"时，
> **"已验证"覆盖率与单请求的服务端成本如何共同变化？**

- **自变量**：引用语义支持判定的实现方式（不判定 / 规则判定 / 模型判定），分三组；
- **因变量**：应用端 —— 标为"已验证"的引用比例、被标为 `insufficient` / `contradicted` 的比例；
  推理端 —— 首 token 延迟、decode 吞吐、单请求显存峰值；
- **控制**：同一批文档与同一批主张、同一模型、同一输出上限；每组至少 30 条配对主张；
- **停止条件**：若模型判定组相对规则判定组的"已验证"比例提升不足 5 个百分点，
  或首 token 延迟中位数增加超过 100%，则停止该路线并改回 `not_checked` + 人工抽查。
- **需要先补埋点**：服务端分段时间与缓存命中字段（当前样机完全没有）。

### 6.4 持续维护与交接约束

1. **缓存身份必须随语义变化，而不是随请求字符串变化。** 本次修复把
   `request`（按语义规范化）+ `corpus` + `draft` 一起纳入哈希；在真实语料规模下
   这一做法开销过大，需要改成"资料版本号 + 内容寻址"的形式，并补一条回归测试锁住行为。
2. **逻辑取消不等于停止计算。** 样机资料明确指出客户端取消只停止本地展示；
   多用户环境下"取消即释放资源"的假设会失效，需要服务端的取消语义与真实资源观测。
3. **单进程样机没有并发安全设计。** 缓存是实例状态，多 worker 下每个 worker 各有一份，
   `reset_before` 这样的调用序列语义在并发下不再成立。
4. **`support_status` 必须保持"不冒充已验证"。** 当前实现只给 `not_checked`；
   一旦接入自动判定，必须同时给出 `judgment_source` 与依据，否则会重现 R04 那类评价错误。
5. **输出预算需要按"推理 + 正文"规划。** 本次 20% 的主结果因共享预算被推理耗尽而不可用；
   接真实推理服务时应把推理与正文的预算分开度量，并监控 `finish_reason=length` 的比例。
6. **可复现性的最低要求**：保留 `runs/<run_id>.json` 的完整 `messages` 与 `usage`。
   本次即使冻结版源码未归档，仍能凭 `messages` 重放全部 40 次主结果。

### 6.5 E1–E7 索引

| 索引 | 指向 |
|---|---|
| **E1** | 启动与一条前后端真实执行路径：`基础/results/request_trace_E1.md`；脚本 `基础/starter/trace_one_request.py` |
| **E2** | 论文命题及原文位置：本报告 §2.1（含 §2.3 小节标题与原文引文）；`进阶/materials/sources.json` |
| **E3** | 基线/改进的逐例原始结果：`基础/results/scoring/manual_review.csv`、`improvement_pairing.csv`；`进阶/runs/baseline.json`、`repaired.json` |
| **E4** | 竞争解释和有辨别力的检查：`进阶/runs/cache_diagnosis.md`（两组对照）；`基础/results/scoring/failure_index.md`（截断机制） |
| **E5** | 反例/变体/回归与未解边界：`进阶/runs/regression_and_variants.md`；`基础/results/scoring/diagnostic_notes.md` |
| **E6** | 三项决定及 AI 影响：`decisions.md`（D1–D6） |
| **E7** | 可定位配置、统一 AI 声明：`基础/config.example.json`、`declaration.md`、`SECURITY.md`；简历在收集表中 |

---

## AI声明索引

以下五项统一填写在 `declaration.md`，本报告直接引用，不重复抄写：
真实 API 模型名称；Token 消耗量级（可选）；AI 工具与主要用途；
本人核验并承担的关键判断及核验方法；未实现、未运行或未验证的内容。
