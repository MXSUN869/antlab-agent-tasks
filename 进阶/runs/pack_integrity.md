# 题包文件完整性核查（逐文件 SHA256）

题包自带 `基础/文件校验.json` 与 `进阶/文件校验.json`，其中给出每个原始文件的 SHA256。
本文件记录提交前的核查结果，并逐项说明**哪些文件与题包不一致、是谁改的、有无记录**。

## 核查命令

```bash
python - <<'PY'
import json, hashlib, os
repo = "."
same = changed = 0
for part in ["基础", "进阶"]:
    idx = json.load(open(os.path.join(repo, part, "文件校验.json"), encoding="utf-8"))
    for rel, expect in idx.items():
        p = os.path.join(repo, part, rel.replace("/", os.sep))
        actual = hashlib.sha256(open(p, "rb").read()).hexdigest()
        ok = actual == expect
        same += ok; changed += (not ok)
        if not ok:
            print("DIFF", part + "/" + rel)
print("一致:", same, "不一致:", changed)
PY
```

## 核查结果

**47 个文件与题包 SHA256 完全一致**，包括全部题目数据、题面、模板、公开语料，
以及**归位后的 `challenge_b/challenge.py`**。

**4 个文件不一致**，逐项说明如下：

| 文件 | 不一致的原因 | 是否有记录 |
|---|---|---|
| `基础/.gitignore` | 本仓库移除其中的 `runs/`，因为题目要求运行记录随仓库提交 | ✅ 有：`SECURITY.md`、`decisions.md` D6、git 提交记录 |
| `基础/starter/student.py` | 题目要求的实现项（`prepare_messages` / `improve`） | ✅ 有：`decisions.md` D1、`frozen_version.md`（五个版本的哈希与时间线）、git 提交记录 |
| `进阶/challenge_b/index.html` | 候选人的呈现层实现。`spec.md` 明确写「初始只显示JSON。提升到题目要求的差异/来源/状态展示由候选人完成」，因此**这个文件本来就应当被修改** | ✅ 有：`README.md` 第 1 节改动表、`index_before_comparison.html` 作为改前快照、git 提交记录 |
| `进阶/challenge_b/server.py` | 同上：候选人为页面新增 `/api/comparison` 查询接口 | ✅ 有：题包原件**完整保留**为 `server_before_comparison.py`，且与其**字节一致**（`8386dc43…`），可直接 `diff` |

核查同时确认：`进阶/challenge_b/spec.md`、`run_cases.py`、`data.json` 与
`基础/data/` 全部内容**未被改动**（哈希一致）。这一点很重要——
**本次 B 的全部结论都是对照未改动的 `spec.md` 契约得出的**，
而不是对照某个被改过的标准。

## 换行符与 Git 设置（曾导致校验在 clone 后失效）

核查过程中发现一个会让上述校验在别人机器上失效的问题，已修复并记录在此：

- 本机与多数 Windows 安装的 Git 在系统级设置了 `core.autocrlf=true`
  （本机来自 `C:/Program Files/Git/etc/gitconfig`）。
- 该设置会在**入库时把 CRLF 归一为 LF**、在**检出时把 LF 转成 CRLF**。
  题包校验值是按原始字节算的，因此首次提交后立即出现：
  `基础/data/cases.json` 的工作区哈希与题包一致，但**已提交的 blob 哈希不一致**
  （918 个 CRLF 被归一为 0 个），clone 之后无法再复现题包校验值。
- **修复方式**：新增根目录 `.gitattributes`，把**仍与题包校验值一致的文件**
  逐条标记为 `-text`（不做换行符转换），并在仓库内设置 `core.autocrlf=false` 作为双保险。
  标记是按 `文件校验.json` 的清单自动生成的，因此不会漏项。
- **修复后验证**（在提交对象层面对每个文件重新计算）：
  `git cat-file -p HEAD:<文件>` 的 SHA256 与题包 `文件校验.json` **47/47 一致**。
- 被修改过的 4 个文件与本次新增文件**不**标记为 `-text`，
  保持文本处理，以便评审直接阅读 `git diff`。

复算方式：

```bash
git config core.autocrlf false   # 若你的环境默认开启
python - <<'PY'
import json, hashlib, subprocess, os
same = 0
for part in ["基础", "进阶"]:
    idx = json.load(open(os.path.join(part, "文件校验.json"), encoding="utf-8"))
    for rel, expect in idx.items():
        blob = subprocess.run(["git", "cat-file", "-p", f"HEAD:{part}/{rel}"],
                              capture_output=True).stdout
        same += hashlib.sha256(blob).hexdigest() == expect
print("已提交 blob 与题包 SHA256 一致:", same)
PY
```

## 已修复的一处严重不一致：`challenge.py` 曾被改掉预埋故障

核查中发现 `进阶/challenge_b/challenge.py` 与题包原件不同，差异正好落在**缓存键**上：

| 版本 | 缓存键 | 后果 |
|---|---|---|
| **题包原件**（30 行） | `key = request['query'].strip().lower()` | 仅按 query 缓存，即 `spec.md` 第 5 条描述的预埋故障：R01(alpha/v1) 与 R02(alpha/v2) 的 query 相同 → R02 命中 R01 的旧结果 |
| 仓库当时版本（35 行） | `key = (query, doc_ids, snapshot, k)` | snapshot 已进键 → **预埋故障消失**，R02 不再复现跨版本错误 |

决定性证据是时间顺序与回放对照：`runs/baseline.json` 的修改时间是 **2026-10-14 22:32**，
而那个改过的 `challenge.py` 是 **2026-10-14 23:36**——**基线记录先生成，样机故障事后被改掉**。

| 用哪份代码回放 `challenge:Engine` | R02 结果 | 能否复现 `runs/baseline.json` |
|---|---|---|
| 题包原件 | evidence=`b01`、`cache_hit=True` | ✅ **7/7 用例逐字段一致** |
| 仓库当时版本 | evidence=`b02`、`cache_hit=False` | ❌ 不能（且 R03 的 `[]`/invalid 仍能复现，说明只改掉了缓存那一处故障） |

**处理方式**：已把 `challenge.py` **归位为题包原件**（现哈希 `b84a035957ac457f…`，
与 `进阶/文件校验.json` 一致）。于是 `runs/baseline.json` 成为可复现的记录，
`cache_diagnosis.md` 的两组对照实验也能被评委原样重放。
`runs/baseline.json` **未改写**——题目要求不改写基线记录，而它本来就是用原件跑出来的。

归位后重跑等价变体与边界检查，数值与此前记录的**完全一致**：两个引擎下三个变体的
（证据集合, 定位状态）各自唯一；边界用例 `status` 在原样机为 `ok`、在修复版为
`invalid_scope`。因此 `cache_diagnosis.md` 与 `regression_and_variants.md` 的数值无需修改。

## 仍然存在的一处小缺口：`index.html` 的题包原件

`challenge.py` 与 `server.py` 的原件现已齐备（前者已归位，后者保留为
`server_before_comparison.py` 且字节一致），但 **`index.html` 的题包原件仍未留存**：

- 题包清单中 `index.html` 的哈希是 `a7de999ef4aa6f3f…`；
- 仓库中的 `index_before_comparison.html` 是候选人的**改前快照**（哈希 `318a60ff…`），
  做换行符归一后仍不等同于题包原件；
- 桌面只提供了 `challenge.py` 与 `server.py`，没有 `index.html`。

**影响有限**：`spec.md` 与 `进阶/02_B_系统失效诊断.md` 都把「差异/来源/状态的展示」
交给候选人实现，因此 `index.html` 本来就应当被修改；这里缺的只是**修改前那份基线页面的副本**，
不影响本次工作的成果。若要从零核查这一处，需从题包原始来源取回该文件。
在此之前，本仓库**不声称** `index_before_comparison.html` 等于题包原件。

## 可以确信的部分

- 仓库中的 `challenge_b/challenge.py` **就是题包原件**（哈希与清单一致），
  因此 `runs/baseline.json` 是可复现的基线记录，
  `cache_diagnosis.md` 的两组对照实验可被原样重放。
- 题包描述的故障症状在原件上可复现，且与 `进阶/README.md` 的描述一致：
  「换了资料版本却显示旧结论」（R02）、「指定了文档却漏掉证据」（R03）。
  见 `runs/baseline.json` 与 `cache_diagnosis.md`。
- 用于判定的公开行为契约 `challenge_b/spec.md` **哈希一致，未被改动**。
- 全部 40 次基础题主结果所依赖的 `基础/data/` 与 `基础/starter/` 骨架中
  除 `student.py`（实现项）与 `.gitignore` 外的文件，**哈希一致**。
