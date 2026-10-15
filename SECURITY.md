# 提交安全：本仓库包含什么、排除了什么

## 排除在仓库之外的内容

| 内容 | 位置 | 排除方式 |
|---|---|---|
| API 密钥 | 环境变量 `ASSESSMENT_API_KEY` | 从未写入任何文件；`provider.py` 显式不保存错误页正文，避免意外收录凭据 |
| 本地配置（含真实 Endpoint 与模型标识） | `基础/config.local.json` | 列入 `.gitignore` |
| 环境文件 | `.env` | 列入 `.gitignore` |
| Python 缓存 | `__pycache__/`、`*.pyc` | 列入 `.gitignore` |
| 运行日志中内嵌的 Endpoint | `基础/runs/*.json` 的 `config.endpoint` | 由 `tools/redact_endpoint.py` 替换为占位符 |
| 简历与联系方式 | 不在仓库 | 按题目要求只放进收集表 |

## 关于运行日志中的 Endpoint

`runner.py` 会把整个 config 原样写入每条运行记录，因此归档的 `runs/*.json`
里带有当时使用的 API Endpoint。按 `进阶/05_提交与报告格式.md`
「提交前检查并移除 API 密钥、Endpoint、私人账号信息和本地配置」的要求，
这些值已被替换为

```
"endpoint": "<REMOVED_PER_SUBMISSION_REQUIREMENTS: see config.example.json>"
```

**替换只影响这一个字段。** 以下内容保持原样，因此 40 次主结果的任何数字都不变：

- `response`（模型原始响应）、`usage`、`elapsed_seconds`、`http_status`、`status`
- `messages`、`selected_passage_ids`、`original_passage_ids`
- `data_sha256`、`student_sha256`、`dataset_version`
- `config` 里的 `provider`、`model`、`parameters`、`timeout_seconds`

复算方式：

```bash
python tools/redact_endpoint.py            # 预演：只报告会改动多少文件
python tools/redact_endpoint.py --apply    # 实际写入
```

该脚本可重复执行（已经是占位符的记录会被跳过）。

被移除的 Endpoint 仍然保留在本机的 `基础/config.local.json` 中（该文件不提交），
因此本机仍可按原配置复跑；仓库里的 `基础/config.example.json` 只给占位说明。

## 关于 `runs/` 目录

题包自带的 `基础/.gitignore` 原本包含 `runs/`，会把运行记录整个排除。
但题目明确要求

> 「实验输入、原始响应、失败和前后对照须保留在仓库中」
> 「基础运行记录仍放在 `runs/` 下并与进阶分组」

两处要求冲突，本仓库以**题目要求为准**：已从 `基础/.gitignore` 中移除 `runs/`，
运行日志随仓库提交。这一步写在 `decisions.md`（D6）与 git 提交记录里，
避免被误认为是漏提交。

## 提交前自查命令

```bash
# 1) 仓库中不应出现任何 key-like 字符串
# 只查数据与代码文件：.md 里出现的同一串是说明文字，不是残留
grep -rInE "Bearer [A-Za-z0-9_-]{12,}|sk-[A-Za-z0-9]{16,}" --include="*.json" --include="*.py" .

# 2) 不应出现真实 Endpoint 主机名
grep -rIn "ark.cn-beijing.volces.com" --include="*.json" . && echo "仍有残留" || echo "已清理"

# 3) 确认本地配置没有被跟踪
git ls-files | grep -E "config\.local\.json|\.env$" && echo "错误：本地配置被跟踪" || echo "OK"

# 4) 确认运行记录确实被跟踪（应为非空）
git ls-files | grep -c "runs/.*\.json$"
```

## 一次事故的说明（如实记录）

在准备提交的过程中，一条 PowerShell 命令
`Get-ChildItem -Recurse -File -Include *.pyc | Remove-Item` 因为 `-Include` 在
`-LiteralPath` 下不生效而匹配了**全部文件**，删除了工作副本中的仓库内容。
桌面上的题包原件与一份运行日志备份均完好，仓库已从原件重建，
本文件与 `decisions.md` 中记录的全部改动已重新施加。
该事故不影响任何实验数据：`runs/` 的原始日志、`data/` 与代码均来自未被修改的原件。
如果 git 历史里看到一次较大范围的重新提交，原因即在此。
