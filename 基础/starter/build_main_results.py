"""从原始运行日志重建基础题的正式结果结构。

用途
----
1. 只依赖 `runs/*.json` 原始日志与 `data/cases.json`，重新推导客观字段，
   不复用人工编辑过的中间表，保证「汇总数字 -> 原始响应」可追溯。
2. 按 (case_id, condition, variant) 分组，按 utc 排序编号首次/重试：
   第一次有效尝试 = 主结果，其余 = 重试（题目要求：技术失败仍保留，重试另列）。
3. 校验实际 messages 与 selected_passage_ids / 原文 / 顺序是否一致
   （题目第三步明确要求「确认实际messages和段落ID、原文、顺序与清单一致」）。
4. 输出 R1/R2 的判分工作表（含问题、实际可见段落原文、模型答案、引用原文），
   供人工判「答案正确性 + 引用语义支持」。

不读取 dev_answers.json 参与正式统计以外的用途；不修改任何原始日志。
"""
import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RUNS_DIR = BASE / "runs"
DATA_FILE = BASE / "data" / "cases.json"
OUT_DIR = BASE / "results" / "scoring"

MAIN_CONDITIONS = ["R0", "R1", "R2", "K"]


def load_cases():
    return {c["id"]: c for c in json.loads(DATA_FILE.read_text(encoding="utf-8"))}


def load_runs():
    records = []
    for path in sorted(RUNS_DIR.glob("*.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            records.append({"__file__": path.name, "__broken__": str(exc)})
            continue
        run["__file__"] = path.name
        records.append(run)
    return records


def message_content(run):
    try:
        return run["response"]["choices"][0]["message"]["content"] or ""
    except (KeyError, TypeError, IndexError):
        return ""


def finish_reason(run):
    try:
        return run["response"]["choices"][0].get("finish_reason") or ""
    except (KeyError, TypeError, IndexError):
        return ""


def parse_output(content):
    """返回 (answer 或 None, citations, 错误说明)。"""
    if not content.strip():
        return None, [], "正文为空（无可评分输出）"
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        return None, [], "回答不是合法JSON"
    if not isinstance(obj, dict):
        return None, [], "JSON根对象不是对象"
    answer = obj.get("answer")
    citations = obj.get("citations")
    if not isinstance(answer, str):
        return None, [], "answer缺失或不是字符串"
    if not isinstance(citations, list) or not all(isinstance(x, str) for x in citations):
        return answer, [], "citations缺失或格式错误"
    return answer, citations, ""


def verify_messages(run, case):
    """校验 messages 里的段落 ID/原文/顺序与 selected_passage_ids 清单一致。"""
    selected = run.get("selected_passage_ids") or []
    by_id = {p["id"]: p for p in case["passages"]}
    msgs = run.get("messages") or []
    user = next((m["content"] for m in msgs if m.get("role") == "user"), "")

    problems = []
    positions = []
    for pid in selected:
        p = by_id.get(pid)
        if p is None:
            problems.append(f"段落ID {pid} 不在 cases.json 中")
            continue
        marker = f"[{pid}]"
        idx = user.find(marker)
        if idx < 0:
            problems.append(f"messages 中找不到段落 {pid} 的ID标记")
            continue
        if p["text"] not in user:
            problems.append(f"messages 中找不到段落 {pid} 的原文")
        positions.append(idx)

    if positions != sorted(positions):
        problems.append("messages 中段落出现顺序与 selected_passage_ids 清单不一致")
    if case["question"] not in user:
        problems.append("messages 中找不到题目原文")
    return ("一致" if not problems else "不一致"), "; ".join(problems)


def build():
    cases = load_cases()
    runs = [r for r in load_runs() if "__broken__" not in r]

    paid = [r for r in runs if r.get("mode") == "paid"]
    groups = {}
    for run in paid:
        key = (run.get("case_id"), run.get("condition"), run.get("variant"))
        groups.setdefault(key, []).append(run)
    for key in groups:
        groups[key].sort(key=lambda r: r.get("utc", ""))

    rows = []
    for key, items in groups.items():
        for index, run in enumerate(items):
            attempt = "first" if index == 0 else f"retry_{index + 1}"
            case = cases.get(run.get("case_id"), {"passages": [], "question": ""})
            content = message_content(run)
            answer, citations, parse_error = parse_output(content)
            by_id = {p["id"]: p for p in case["passages"]}
            selected = run.get("selected_passage_ids") or []
            usage = run.get("usage") or {}
            consistent, note = verify_messages(run, case)
            in_input = (
                ("是" if set(citations).issubset(set(selected)) else "否")
                if citations
                else ("无引用" if answer is not None else "无法判断")
            )
            rows.append({
                "run_id": run.get("run_id", ""),
                "utc": run.get("utc", ""),
                "attempt": attempt,
                "case_id": run.get("case_id", ""),
                "condition": run.get("condition", ""),
                "variant": run.get("variant", ""),
                "json_valid": "否" if parse_error else "是",
                "empty_content": "是" if not content.strip() else "否",
                "finish_reason": finish_reason(run),
                "completion_tokens": usage.get("completion_tokens", ""),
                "reasoning_tokens": (
                    (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", "")
                    if isinstance(usage.get("completion_tokens_details"), dict) else ""
                ),
                "prompt_tokens": usage.get("prompt_tokens", ""),
                "elapsed_seconds": run.get("elapsed_seconds", ""),
                "max_tokens": (run.get("config", {}).get("parameters", {}) or {}).get("max_tokens", ""),
                "answer": answer if answer is not None else "",
                "citations": json.dumps(citations, ensure_ascii=False),
                "citations_in_input": in_input,
                "n_selected": len(selected),
                "selected_passage_ids": json.dumps(selected, ensure_ascii=False),
                "input_characters": run.get("input_characters", ""),
                "messages_consistent": consistent,
                "messages_note": note,
                "error": parse_error,
                "log_file": run.get("__file__", ""),
                "student_sha256": run.get("student_sha256", ""),
                "data_sha256": run.get("data_sha256", ""),
            })
    return cases, rows


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


def main():
    cases, rows = build()
    first_rows = [r for r in rows if r["attempt"] == "first"]
    retry_rows = [r for r in rows if r["attempt"] != "first"]

    # 正式主结果只含评测题 T01–T08（40 次）。D01–D04 属于开发调试调用，单独保存。
    main_rows = [r for r in first_rows if r["case_id"].startswith("T")]
    dev_rows = [r for r in first_rows if r["case_id"].startswith("D")]
    retry_main = [r for r in retry_rows if r["case_id"].startswith("T")]
    retry_dev = [r for r in retry_rows if r["case_id"].startswith("D")]

    fields = ["run_id", "utc", "attempt", "case_id", "condition", "variant",
              "json_valid", "empty_content", "finish_reason", "completion_tokens",
              "reasoning_tokens", "prompt_tokens", "elapsed_seconds", "max_tokens",
              "answer", "citations", "citations_in_input", "n_selected",
              "selected_passage_ids", "input_characters", "messages_consistent",
              "messages_note", "error", "log_file", "student_sha256", "data_sha256"]

    write_csv(OUT_DIR / "main_runs_40.csv", main_rows, fields)
    write_csv(OUT_DIR / "dev_runs_paid.csv", dev_rows, fields)
    write_csv(OUT_DIR / "retry_runs_main.csv", retry_main, fields)
    write_csv(OUT_DIR / "retry_runs_dev.csv", retry_dev, fields)

    # 一致性校验汇总
    bad = [r for r in rows if r["messages_consistent"] != "一致"]
    print(f"messages 一致性：{len(rows) - len(bad)}/{len(rows)} 条一致")
    for r in bad[:10]:
        print("  !!", r["run_id"], r["messages_note"])

    # shortfall report
    print()
    print(f"正式主结果（T01–T08 首次尝试）：{len(main_rows)} 条")
    print(f"开发集直接付费调用（D01–D04 首次尝试，不计入40次）：{len(dev_rows)} 条")
    print(f"评测题重试：{len(retry_main)} 条；开发题重试：{len(retry_dev)} 条")
    print()
    print("按条件统计首次尝试：")
    for cond in MAIN_CONDITIONS:
        sel = [r for r in main_rows if r["condition"] == cond and r["variant"] == "baseline"]
        print(f"  {cond} baseline: {len(sel)} 条, "
              f"合法JSON {sum(1 for r in sel if r['json_valid'] == '是')}, "
              f"空正文截断 {sum(1 for r in sel if r['empty_content'] == '是')}, "
              f"平均耗时 {sum(float(r['elapsed_seconds']) for r in sel) / len(sel):.2f}s")
    imp = [r for r in main_rows if r["variant"] == "improved"]
    print(f"  R0 improved: {len(imp)} 条, "
          f"合法JSON {sum(1 for r in imp if r['json_valid'] == '是')}, "
          f"空正文截断 {sum(1 for r in imp if r['empty_content'] == '是')}, "
          f"平均耗时 {sum(float(r['elapsed_seconds']) for r in imp) / len(imp):.2f}s")

    # R1/R2 判分工作表
    lines = ["# R1 / R2 人工判分工作表", "",
             "生成自 `runs/*.json` 原始日志与 `data/cases.json`，未使用任何中间表。",
             "判分口径：**答案正确性**（能否由本次可见段落推出）与**引用语义支持**"
             "（每条引用原文是否真的支持该结论）分开判断；引用ID在输入内不等于语义支持。", ""]
    for cond in ["R1", "R2"]:
        lines.append(f"## 条件 {cond}")
        lines.append("")
        for case_id in [f"T{i:02d}" for i in range(1, 9)]:
            row = next((r for r in main_rows
                        if r["case_id"] == case_id and r["condition"] == cond
                        and r["variant"] == "baseline"), None)
            if row is None:
                lines.append(f"### {case_id} {cond} —— 缺记录")
                lines.append("")
                continue
            case = cases[case_id]
            by_id = {p["id"]: p for p in case["passages"]}
            lines.append(f"### {case_id} / {cond} / run_id `{row['run_id']}`")
            lines.append("")
            lines.append(f"- 问题：{case['question']}")
            lines.append(f"- 耗时：{row['elapsed_seconds']:.3f}s；finish_reason="
                         f"{row['finish_reason']}；completion_tokens={row['completion_tokens']}")
            lines.append(f"- 模型答案：`{row['answer']}`")
            lines.append(f"- 模型引用：`{row['citations']}`")
            lines.append(f"- 引用ID是否都在本次输入内：{row['citations_in_input']}")
            lines.append("")
            lines.append("本次实际可见段落：")
            lines.append("")
            for pid in json.loads(row["selected_passage_ids"]):
                p = by_id.get(pid, {})
                lines.append(f"  - `{pid}`（{p.get('source','')} p{p.get('page','')}）：{p.get('text','')}")
            lines.append("")
    (OUT_DIR / "review_R1_R2.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_DIR / 'review_R1_R2.md'}")


if __name__ == "__main__":
    main()
