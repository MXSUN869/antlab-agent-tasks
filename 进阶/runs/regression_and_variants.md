# 进阶 B：回归、语义等价变体与未解决边界

本文件补齐 `02_B_系统失效诊断.md` 要求提交的证据集：**两个原本正常的回归**、
**两个语义等价变体**、**一个仍未解决的边界**，每项都先写预期依据再给实际结果。
主故障的原因区分实验另见 `cache_diagnosis.md`。

所有命令在仓库根目录执行，**不调用模型 API，无第三方依赖**。

> 记录时点：本文件写于原始样机（`challenge_b/challenge.py`）与修复版
> （`challenge_b/my_engine.py`）都已可运行之后。**预期依据来自 `spec.md` 的条文**，
> 而非来自运行结果；但完整的运行结果是在同一轮里一并取得的，因此本文件属于
> **事后整理**，不主张这些预期曾作为预注册预测被冻结。

---

## 一、被修复的原始失败（复现方式）

```bash
python 进阶/challenge_b/run_cases.py --engine challenge:Engine --output 进阶/runs/baseline.json
python 进阶/challenge_b/run_cases.py --engine my_engine:Engine  --output 进阶/runs/repaired.json
```

`baseline.json` 与 `repaired.json` 使用相同 `data.json`、相同 CLI 顺序与相同 `reset_before`
语义，因此逐用例可直接比较。原始样机的可复现失败为：

| 用例 | 症状 | 原始样机结果 | 修复版结果 |
|---|---|---|---|
| R02 | 换了资料版本却返回旧结论 | evidence=`b01`（v1）、cache_hit=**True**、答案 30 秒 | evidence=`b02`（v2）、cache_hit=False |
| R03 | 指定了文档却漏掉证据 | evidence=`[]`、locator=invalid | evidence=`b03`、locator=valid |
| R07 | 未知范围被当作正常完成 | status=**ok** | status=**invalid_scope** |

---

## 二、两个原本正常的回归

回归的意义：确认最小修复没有破坏原本正确的行为。两项的**预期都来自 `spec.md` 的条文**，
不是"看代码觉得应该一样"。

### 回归 1：R01 单文档、单快照的正常检索

- **预期依据**：`spec.md` 第 1 条（范围由 doc_ids 与 snapshot 共同确定）、
  第 2 条（按 tags 交集降序）。R01 请求 alpha/v1/`k=2`，query=`timeout request threshold`，
  v1 下只有 b01 命中 tags（`timeout`、`request`、`threshold`），正分证据应为 `[b01]`；
  引用 `b01` 在证据内，故 locator 应为 `valid` 且缓存未命中。
- **实际**：原始样机 `[b01] / valid / hit=False`；修复版 `[b01] / valid / hit=False`。
  **一致，回归通过。**

### 回归 2：R05 多文档范围下的正确排序

- **预期依据**：`spec.md` 第 2 条——doc_ids 为 beta、snapshot v1、query=`metadata beta`，
  v1 的 beta 资料只有 b05（tags=`metadata`、`beta`），交集为 2；正分证据应为 `[b05]`
  且引用 `b05` 有效。
- **实际**：原始样机 `[b05] / valid / hit=False`；修复版 `[b05] / valid / hit=False`。
  **一致，回归通过。**

### 附：另外两项同样未变化（R04、R06）

| 用例 | 原始样机 | 修复版 | 说明 |
|---|---|---|---|
| R04 | `[b04] / valid / ok` | `[b04] / valid / ok` | 取消与 GPU 释放，单段证据 |
| R06 | `[b06] / valid / ok` | `[b06] / valid / ok` | 单进程与多 worker，单段证据 |

七项用例里只有 R02、R03、R07 三处行为变化，**其余四项逐字段一致**，
说明修复的作用范围被限制在缓存身份与范围筛选，没有波及正常检索路径。

---

## 三、两个语义等价变体

```bash
python 进阶/runs/test_variants.py            # 两个引擎一起跑
```

两个变体都**不改变语义与证据关系**，只改写法：

| 变体 | 改了什么 | 为什么语义未变（预期依据） |
|---|---|---|
| V2 | query 改成 `METADATA BETA` | `spec.md` 第 2 条的排序输入是 query 的**空格分词**与 tags 的交集；样例数据里 query 与 tags 都是英文小写，大小写规范化不改变分词集合，故命中集合与排序不变 |
| V3 | doc_ids 从 `["alpha","beta"]` 改成 `["beta","alpha"]` | `spec.md` 第 1、2 条中 doc_ids 是**范围集合**，不规定顺序；排序按键是"交集数量降序、同分按 id 字典序"，与请求里 doc_ids 的书写顺序无关 |

**预期**：三个请求应得到**相同的证据集合与相同的 locator_status**。
`cache_hit` **允许不同**（`spec.md` 第 5 条只规定"可以复用等价输入"，未规定必须复用）。

**实际（两个引擎分别跑）**：

| 变体 | 原始样机 evidence / locator / cache_hit | 修复版 evidence / locator / cache_hit |
|---|---|---|
| V1 原始请求 | `[b05]` / valid / False | `[b05]` / valid / False |
| V2 查询改大写 | `[b05]` / valid / **True** | `[b05]` / valid / **True** |
| V3 反转 doc_ids | `[b05]` / valid / **True** | `[b05]` / valid / **True** |

**结论**：两个引擎下三个变体的（证据集合, 定位状态）都只有一个取值，等价性成立。

这一项同时验证了修复的**第二条性质**：修复版把请求按 `spec.md` 的语义规范化后再计算缓存身份
（query 去空白并小写、doc_ids 去重并排序），因此
**(a) 跨 snapshot 的请求不会命中旧结果**（R02 已证），
**(b) 语义等价的请求仍然可以复用缓存**（V2/V3 的 cache_hit 仍为 True）。
两半都保住了，而不是用"关闭复用"换安全。

---

## 四、一个仍未解决或已明确拒绝的边界

### 用例

查询 `metadata beta`、doc_ids=`beta`、snapshot=`v999`（`data.json` 中不存在该快照）、`k=2`、
draft 引用 `b05`。

```bash
python 进阶/runs/test_boundary.py
```

### 预期依据

- `spec.md` 第 1 条：未知的 doc_ids 与 snapshot 组合应返回 `invalid_scope`，不得回退另一快照。
- `spec.md` 第 3 条：引用越界须标识，不能把错误来源显示为当前版本。

### 实际

| 引擎 | evidence | locator_status | status | 是否回退到 v1 的 b05 |
|---|---|---|---|---|
| 原始样机 | `[]` | invalid | **ok** | 否 |
| 修复版 | `[]` | invalid | **invalid_scope** | 否 |

### 判定：**部分解决，仍有未解决问题**

- **已解决**：两个引擎都没有跨快照回退（b05 未被当作本次证据）；
  修复版把总体状态从 `ok` 改为 `invalid_scope`，使"该范围没有任何可用证据"
  不再与"正常完成"混为一谈。
- **仍未解决**：`spec.md` 第 3 条要求"引用**缺失**或**越界**须分别标识"。
  这里的 citations 非空但全部越界，因此 `invalid` 是正确的；
  但当 citations 为空时，原始样机同样返回 `invalid`，无法区分
  "没有给出引用"与"给出的引用越界"。修复版改用 `missing` / `invalid` / `valid` 三态，
  但**这一点没有被单独测试用例固定下来**（现有用例的 citations 都不为空）。
  因此这里登记为：**三态区分已实现但未逐一验证**，属于尚未闭环的边界。
- **明确拒绝的做法**：不回退到其他快照"尽量给出答案"。理由是那会让
  "页面显示对应当前请求"这一条失效，而这正是本题要诊断的用户任务伤害。

---

## 五、另外两个症状的风险与依据

主问题是**缓存身份不完整导致的跨版本污染**。按 `02_B` 的要求，另登记两个症状的风险与依据，
不把它们混进主问题的结论。

### 症状 2：把"引用可定位"直接当成"语义已被支持"（评价错误）

- **风险**：页面会向用户声称结果"已验证"，而系统实际只检查了引用 ID 是否属于本次证据。
  用户据此信任一条内容其实并不成立的结论——这是比"找不到证据"更危险的失败，
  因为它给出的是**虚假的确定性**。
- **依据（代码级）**：原始样机 `challenge.py:30`
  `'support_status': 'supported' if valid else 'not_checked'` —— `supported` 完全由
  ID 有效性推导，源码中不存在任何语义比较。
- **依据（运行级）**：`baseline.json` 中 R01/R04/R05/R06 四项全部为 `supported`，
  而它们的 draft 中 R04 的答案是"点击取消就保证 GPU 立即停止计算并释放资源"，
  其证据 b04 原文为"客户端取消仅停止本地结果展示；本文没有测量服务端是否释放 GPU 计算资源"
  —— **该答案与证据语义相反**，却被标为 `supported`。这是一个可复现的具体反例。
- **修复后的行为**：四个用例都改为 `not_checked`（无语义检查时不冒充已验证），
  并保留 `judgment_source='not_checked'` 供页面区分。
- **仍缺什么**：真正的 `supported` / `contradicted` / `insufficient` 判定需要独立验证，
  本次未实现，页面如实显示未核验。

### 症状 3：范围合法但检索不到正分证据时，状态无法区分

- **风险**：当 doc_ids 与 snapshot 都合法、但按 query 分词算不出任何正分 tag 时，
  系统会返回空证据且状态为 `ok`。用户无法判断是"确实没有相关资料"，
  还是"检索逻辑没匹配上"。前者是可接受的拒答，后者是功能性缺陷。
- **依据**：`spec.md` 第 2 条要求"只保留正分证据"，
  但未规定此时总体状态应取什么值；原始样机在 `scoped` 非空时一律给 `status='ok'`，
  即使 `positive` 为空（`challenge.py:24-31`）。
  本文件第四节的 v999 用例覆盖了 `scoped` 为空的情形，
  但 **`scoped` 非空且 `positive` 为空的组合没有被单独用例覆盖**。
- **当前处理**：登记为风险，不声称已修复。修复版把 `scoped` 为空映射为
  `invalid_scope`，但 `positive` 为空仍返回 `ok` 加空证据，与原始样机一致
  —— 这一点在报告中如实标注为未解决。

---

## 六、与主故障的边界

以上两个症状**不是**主故障的原因，也不由同一次修复解决：

- 症状 2 是**评价口径错误**（把可定位当成被支持），与缓存无关；
- 症状 3 是**状态语义不完备**，与缓存无关。

把它们并入"缓存修复"的成效叙述会使结论超出证据，因此分列。
主故障的因果判断只依赖 `cache_diagnosis.md` 中"新引擎单独跑 R02 vs 同一引擎先 R01 再 R02"
这一组对照，其中只有"是否复用缓存"一个变量发生变化。
