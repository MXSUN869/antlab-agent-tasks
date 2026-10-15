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

**46 个文件与题包 SHA256 完全一致**，包括全部题目数据、题面、模板与公开语料。

**5 个文件不一致**，逐项说明如下：

| 文件 | 不一致的原因 | 是否有记录 |
|---|---|---|
| `基础/.gitignore` | 本仓库移除其中的 `runs/`，因为题目要求运行记录随仓库提交 | ✅ 有：`SECURITY.md`、`decisions.md` D6、git 提交记录 |
| `基础/starter/student.py` | 题目要求的实现项（`prepare_messages` / `improve`） | ✅ 有：`decisions.md` D1、`frozen_version.md`（五个版本的哈希与时间线）、git 提交记录 |
| `进阶/challenge_b/index.html` | 修复对比面板的中文乱码，并补「修复前后行为对比」区块 | ✅ 有：`README.md` 第 1 节改动表、git 提交记录 |
| `进阶/challenge_b/challenge.py` | **不是本次报告所做的改动。** 该文件的修改时间为 2026-10-14 23:36（本地），早于本报告的编写时间；工作副本与桌面原件一致，因此改动来自此前的准备工作 | ❌ **无 diff 可用**，见下方「未解决的缺口」 |
| `进阶/challenge_b/server.py` | **不是本次报告所做的改动。** 修改时间为 2026-10-15 11:23（本地） | ❌ **无 diff 可用**，同上 |

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
- **修复方式**：新增根目录 `.gitattributes`，把**仍与题包校验值一致的 46 个文件**
  逐条标记为 `-text`（不做换行符转换），并在仓库内设置 `core.autocrlf=false` 作为双保险。
  标记是按 `文件校验.json` 的清单自动生成的，因此不会漏项。
- **修复后验证**（在提交对象层面对每个文件重新计算）：
  `git cat-file -p HEAD:<文件>` 的 SHA256 与题包 `文件校验.json` **46/46 一致**。
- 被本人修改过的 5 个文件与本次新增文件**不**标记为 `-text`，
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

## 未解决的缺口（需本人处理）

`进阶/challenge_b/challenge.py` 与 `server.py` 与题包原始版本不同，而**原始版本没有留在
工作副本里，也没有 .pyc 可用作还原依据**：

- `__pycache__/challenge.cpython-312.pyc` 的头部记录的源文件 mtime 与大小
  与**当前**（改动后）的 `challenge.py` 完全一致（1663 字节，2026-10-14 15:36 UTC），
  其代码对象签名也与当前源码编译结果完全一致。
  因此该 `.pyc` 是**改动之后**生成的，不能用来还原改动前的版本。
- 因此无法提供这两处改动的 diff，也无法断言改动只是格式性的。

**这为什么需要处理**：`进阶/02_B_系统失效诊断.md` 要求「保存原样机代码或差异文件」，
并且「不改写基线记录」。而 `进阶/runs/baseline.json` 是用**当前版本**的
`challenge:Engine` 生成的。如果 `challenge.py` 在 10-14 被实质性改动过，
那么这份「基线」就不是题包作者的原始样机。

**建议的处理方式（约 5 分钟）**：从题包原始来源（Q 群下载或本地备份）取回
`进阶/challenge_b/challenge.py` 与 `server.py` 的原始版本，两者对比后：

1. 若差异只是格式/注释 → 在仓库中恢复为原始版本，重跑 `baseline.json` 并更新本文件；
2. 若有实质性差异 → 把原始版本另存为 `challenge_b/original/`，提交 diff，
   并把 `baseline.json` 重新用原始版本生成，以保证「基线」名副其实。

在此之前，本仓库**不对这两处改动做任何推测**，也不声称当前 `challenge.py`
与题包作者原始样机逐字相同。

## 可以确信的部分

- 题包描述的故障症状在**当前版本**上可复现，且与 `进阶/README.md` 描述的一致：
  「换了资料版本却显示旧结论」（R02）、「指定了文档却漏掉证据」（R03）。
  见 `runs/baseline.json` 与 `cache_diagnosis.md`。
- 用于判定的公开行为契约 `challenge_b/spec.md` **哈希一致，未被改动**。
- 全部 40 次基础题主结果所依赖的 `基础/data/` 与 `基础/starter/` 骨架中
  除 `student.py`（实现项）与 `.gitignore` 外的文件，**哈希一致**。
