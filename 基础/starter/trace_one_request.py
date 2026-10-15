"""E1：一条完整的「页面 → 后端 → 原始日志 → 原文」追溯。

做三件事，不调用模型、不产生费用：

1. 从 `/` 取回页面，并从 HTML 中读出本次进程生成的会话令牌
   （令牌由 `server.py` 用 `secrets.token_urlsafe(24)` 每次启动重新生成，
   写在页面里而不是接口里，因此拿不到该令牌就无法构造请求）；
2. 用令牌向 `/api/run` 发一次 **dry** 请求，拿到返回的 `run_id`；
3. 打开 `runs/<run_id>.json`，把它记录的 `selected_passage_ids` 与 `messages`
   和 `data/cases.json` 里的原文逐条对照，证明界面上的这一次点击确实能追到日志与原文。

用法（先另开一个终端启动服务端）
--------------------------------
    python 基础/starter/server.py --config 基础/config.example.json --port 8791
    python 基础/starter/trace_one_request.py --port 8791

`--case` / `--condition` / `--variant` 可换用例；默认用公开开发题 D01 的 R0 基线。
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]          # 基础/
sys.path.insert(0, str(BASE / "starter"))


def fetch_page(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10) as response:
        return response.read().decode("utf-8")


def post_run(port, token, payload):
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/run",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Assessment-Session": token},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8")), response.status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8791)
    parser.add_argument("--case", default="D01")
    parser.add_argument("--condition", default="R0")
    parser.add_argument("--variant", default="baseline")
    args = parser.parse_args()

    print("=" * 72)
    print("E1 端到端追溯（dry 模式，不调用模型）")
    print("=" * 72)

    # --- 1. 页面与会话令牌 -------------------------------------------------
    html = fetch_page(args.port)
    if re.search(r"__SESSION_TOKEN__", html):
        raise SystemExit("页面中的 __SESSION_TOKEN__ 未被替换，说明服务端没有正确注入令牌")
    token_match = re.search(r"X-Assessment-Session'\s*:\s*'([A-Za-z0-9_\-]+)'", html)
    if not token_match:
        raise SystemExit("未能从页面中解析出会话令牌")
    token = token_match.group(1)
    print(f"[1] GET /             -> 页面 {len(html)} 字节；由页面注入的会话令牌已取得"
          f"（{token[:6]}…，仅前 6 位显示）")

    # --- 2. 无令牌应当被拒绝，证明接口确实受保护 ---------------------------
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"http://127.0.0.1:{args.port}/api/run",
            data=b'{"case_id":"D01","condition":"R0","variant":"baseline","mode":"dry"}',
            headers={"Content-Type": "application/json"}),
            timeout=10)
        print("[2] 无令牌请求        -> 未被拒绝（异常，请检查服务端）")
    except urllib.error.HTTPError as exc:
        print(f"[2] 无令牌请求        -> HTTP {exc.code} 已拒绝，接口受会话保护")

    # --- 3. 带令牌发起一次 dry 请求 ---------------------------------------
    payload = {"case_id": args.case, "condition": args.condition,
               "variant": args.variant, "mode": "dry"}
    record, status = post_run(args.port, token, payload)
    run_id = record["run_id"]
    print(f"[3] POST /api/run     -> HTTP {status}；run_id={run_id}")
    print(f"    用例={record['case_id']} 条件={record['condition']} "
          f"版本={record['variant']} 模式={record['mode']} 状态={record['status']}")

    # --- 4. 从日志追到原文 -------------------------------------------------
    log_path = BASE / "runs" / f"{run_id}.json"
    print(f"[4] 日志文件          -> {log_path.relative_to(BASE.parent)}  "
          f"（存在={log_path.is_file()}）")
    if not log_path.is_file():
        raise SystemExit("日志未落盘，追溯中断")
    logged = json.loads(log_path.read_text(encoding="utf-8"))

    cases = {c["id"]: c for c in json.loads((BASE / "data" / "cases.json").read_text(encoding="utf-8"))}
    case = cases[logged["case_id"]]
    by_id = {p["id"]: p for p in case["passages"]}

    user_message = next(m["content"] for m in logged["messages"] if m["role"] == "user")
    print(f"    日志中的问题原文  与 cases.json 一致：{case['question'] in user_message}")
    print(f"    日志记录的数据哈希：{logged['data_sha256'][:16]}…")
    print()
    print("    逐段核对（日志中的ID与原文 vs cases.json 原文）：")
    all_ok = True
    for pid in logged["selected_passage_ids"]:
        original = by_id.get(pid)
        in_message = original is not None and f"[{pid}]" in user_message and original["text"] in user_message
        all_ok &= in_message
        print(f"      {pid}  在cases.json={'是' if original else '否'}  "
              f"在messages中={'是' if in_message else '否'}  "
              f"来源={original['source'] if original else '-'}")
    print()
    print(f"    全部段落可追到原文：{'是' if all_ok else '否'}")
    print("=" * 72)
    print("追溯链：页面按钮 -> POST /api/run(会话令牌) -> runner.execute()")
    print("        -> runs/<run_id>.json -> selected_passage_ids -> data/cases.json 原文")
    print("=" * 72)
    if not all_ok:
        raise SystemExit("存在无法追溯到原文的段落")


if __name__ == "__main__":
    main()
