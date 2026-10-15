# E1：一条可复算的端到端请求路径

对应证据索引 **E1**（「启动和一条前后端真实执行路径」）。
本记录**不调用模型、不产生费用**，可在干净环境里按下面的命令重现。

## 追溯链

```
浏览器页面 基础/starter/index.html
   │  选择 样例 / 条件 / 版本 / 模式，点击「执行一次」
   ▼
POST /api/run        （请求头带 X-Assessment-Session 会话令牌）
   │  基础/starter/server.py  Handler.do_POST
   │    · 校验令牌，不匹配返回 403
   │    · 校验 mode ∈ {dry, mock, paid}；paid 需服务端显式 --allow-paid
   ▼
基础/starter/runner.py  execute()
   │    · prepare() 取 cases.json 的原始段落，按 condition 决定顺序
   │    · variant=improved 时调用 student.improve()，并校验它只做重排/选择
   │    · student.prepare_messages() 组装 messages
   │    · 记录 data_sha256 / student_sha256 / messages / selected_passage_ids
   │    · dry 不调用模型；paid 走 provider.call_model()
   ▼
基础/runs/<run_id>.json     （UUID 文件名，永不覆盖，重试另存一份）
   │
   ▼
data/cases.json 的段落原文  +  data/manifest.json 的数据版本与哈希
```

## 实际执行记录

环境：Python 3.12.14（工作区自带运行时），Windows。
启动与追溯分两个终端执行：

```bash
# 终端 1
python 基础/starter/server.py --config 基础/config.example.json --port 8791

# 终端 2
python 基础/starter/trace_one_request.py --port 8791
```

`trace_one_request.py` 依次做四件事，并在任一步失败时以非零状态退出：

1. `GET /` 取回页面，从 HTML 中读出**本次进程用 `secrets.token_urlsafe(24)` 新生成的会话令牌**
   （令牌写在页面里而不是接口里）；
2. 故意用**不带令牌**的请求打一次 `/api/run`，确认被拒绝；
3. 带令牌发一次 `dry` 请求，拿到 `run_id`；
4. 打开 `runs/<run_id>.json`，把它的 `selected_passage_ids` 与 `messages`
   和 `data/cases.json` 的原文逐段比对。

### 输出（2026-10-15 实际运行）

```
[1] GET /             -> 页面 1836 字节；由页面注入的会话令牌已取得（NNIHBk…，仅前 6 位显示）
[2] 无令牌请求        -> HTTP 403 已拒绝，接口受会话保护
[3] POST /api/run     -> HTTP 200；run_id=0ff168e9-e8b7-4b07-87be-641f905e1990
    用例=D01 条件=R0 版本=baseline 模式=dry 状态=dry_run
[4] 日志文件          -> 基础/runs/0ff168e9-e8b7-4b07-87be-641f905e1990.json （存在=True）
    日志中的问题原文  与 cases.json 一致：True
    日志记录的数据哈希：c37cda40ada89a18…

    逐段核对（日志中的ID与原文 vs cases.json 原文）：
      P312446  在cases.json=是  在messages中=是  来源=模拟记录/D01/页1
      P133261  在cases.json=是  在messages中=是  来源=模拟记录/D01/页6
      P898100  在cases.json=是  在messages中=是  来源=模拟记录/D01/页2
      P191745  在cases.json=是  在messages中=是  来源=模拟记录/D01/页4
      P868948  在cases.json=是  在messages中=是  来源=模拟记录/D01/页7
      P771469  在cases.json=是  在messages中=是  来源=模拟记录/D01/页5
      P765807  在cases.json=是  在messages中=是  来源=模拟记录/D01/页3

    全部段落可追到原文：是
```

> **这次运行记录是 `dry` 模式**，`status=dry_run`、`elapsed_seconds=null`、`response=null`。
> 它只证明**前后端链路与记录契约可用**，不能当作任何模型效果的证据。
> 真实的 40 次付费调用记录在 `runs/` 中同样结构，只是 `mode=paid` 且带有 `response` 与 `usage`。

## 评委可以怎样抽查一个具体数字

以正式主结果里的 **R0 基线 T06（答案 25%）** 为例：

1. `results/scoring/manual_review.csv` 找到 `case_id=T06, condition=R0, variant=baseline` 一行，
   读出 `run_id=01111189-bddf-40a8-bade-e9ca150c468c`；
2. 打开 `runs/01111189-bddf-40a8-bade-e9ca150c468c.json`，可见
   `messages`（实际发出去的两条消息）、`selected_passage_ids`、
   `config`（模型与参数）、`response`（原始响应）、`usage`、`elapsed_seconds`、`http_status`；
3. 该行的 `answer=25%` 由 `response.choices[0].message.content` 解析而来，
   解析与判分逻辑在 `starter/build_main_results.py` 的 `parse_output()`；
4. 结论「25% 正确」的依据是两段引用原文
   ——P873502（60 项中 8 项超时、7 项格式不合法）与 P721388（两类均计技术失败、分母为 60 项）
   ——可在 `data/cases.json` 按 ID 检索到；
5. 复算命令：`python 基础/starter/build_main_results.py`（只读日志，不调用模型）。

## 需要说明的限制

- 页面只做 JSON 呈现，没有为「可见段落」「引用语义支持」做专门的可视化。
  基础题的要求是「界面简洁即可」，本项按此处理；呈现层的完整度不是本题的评分对象。
- 服务端只监听 `127.0.0.1`，单进程 `ThreadingHTTPServer`，不含账号、支付与外网部署，
  也没有并发安全设计。多用户/多 worker 下的行为**未被测试**。
- 会话令牌每次启动重新生成，因此上面记录里的 `NNIHBk…` 只对那次进程有效，
  重跑时会得到新值。
