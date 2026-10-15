import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RUNS_DIR = BASE / "runs"
ANSWERS_FILE = BASE / "data" / "dev_answers.json"
OUTPUT_DIR = BASE / "results"
OUTPUT_FILE = OUTPUT_DIR / "results.csv"


def normalize(text):
    """仅做基础文本规范化，不擅自改变答案含义。"""
    return "".join(str(text).strip().lower().split())


def load_final_content(run):
    try:
        return run["response"]["choices"][0]["message"]["content"] or ""
    except (KeyError, TypeError, IndexError):
        return ""


def parse_model_output(content):
    try:
        obj = json.loads(content)
        if not isinstance(obj, dict):
            return None, [], "JSON根对象不是对象"
        answer = obj.get("answer")
        citations = obj.get("citations")
        if not isinstance(answer, str):
            return None, [], "answer缺失或不是字符串"
        if not isinstance(citations, list) or not all(
            isinstance(x, str) for x in citations
        ):
            return answer, [], "citations缺失或格式错误"
        return answer, citations, ""
    except (json.JSONDecodeError, TypeError):
        return None, [], "回答不是合法JSON"


def main():
    if not RUNS_DIR.exists():
        raise SystemExit(f"找不到运行日志目录：{RUNS_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    reference = {}
    if ANSWERS_FILE.exists():
        with ANSWERS_FILE.open(encoding="utf-8") as f:
            reference = {x["id"]: x for x in json.load(f)}

    fields = [
        "run_id", "case_id", "split", "condition", "variant",
        "mode", "status", "http_status", "model",
        "attempt", "elapsed_seconds", "prompt_tokens",
        "completion_tokens", "answer", "citations",
        "answer_match", "citation_ids_in_input",
        "json_valid", "manual_semantic_review",
        "error", "raw_content", "log_file"
    ]

    
    rows = []
    run_files = sorted(
        RUNS_DIR.glob("*.json"),
        key=lambda p: p.name
    )
    run_records = []

    # 先读取日志；不修改、不覆盖原始日志
    for path in run_files:
        try:
            with path.open(encoding="utf-8") as f:
                run = json.load(f)
            run_records.append((path, run))
        except (OSError, json.JSONDecodeError):
            run_records.append((path, None))

    # 仅对真实 paid 调用按时间排序并编号。
    # 同题、同条件、同版本分别计数。
    paid_groups = {}
    for path, run in run_records:
        if not run or run.get("mode") != "paid":
            continue

        key = (
            run.get("case_id", ""),
            run.get("condition", ""),
            run.get("variant", ""),
        )
        paid_groups.setdefault(key, []).append((path, run))

    attempt_by_file = {}
    for key, items in paid_groups.items():
        items.sort(key=lambda item: item[1].get("utc", ""))
        for index, (path, run) in enumerate(items, start=1):
            attempt_by_file[path.name] = (
                "first" if index == 1 else f"retry_{index}"
            )
    for path, run in run_records:
        if run is None:
            rows.append({
                "log_file": path.name,
                "error": "日志读取失败或JSON格式错误",
                "manual_semantic_review": "待人工核查"
            })
            continue
        content = load_final_content(run)
        answer, citations, parse_error = parse_model_output(content)
        case_id = str(run.get("case_id", ""))
        ref = reference.get(case_id, {})
        aliases = ref.get("aliases", [])
        expected = [ref.get("answer", "")] + aliases
        expected = [x for x in expected if isinstance(x, str) and x]

        selected_ids = set(run.get("selected_passage_ids") or [])
        citation_ids = set(citations)
        status = run.get("status", "")
        mode = run.get("mode", "")
        is_real_attempt = mode == "paid"

        if answer is None:
            answer_match = "格式错误/无答案"
        elif not expected:
            answer_match = "无参考答案"
        else:
            answer_match = (
                "匹配" if any(
                    normalize(answer) == normalize(x) for x in expected
                ) else "不匹配"
            )

        rows.append({
            "run_id": run.get("run_id", ""),
            "case_id": case_id,
            "split": run.get("split", ""),
            "condition": run.get("condition", ""),
            "variant": run.get("variant", ""),
            "mode": mode,
            "status": status,
            "http_status": run.get("http_status", ""),
            "model": run.get("config", {}).get("model", ""),
            "attempt": attempt_by_file.get(
                path.name,
                "不计入真实调用"
            ),
            "elapsed_seconds": run.get("elapsed_seconds", ""),
            "prompt_tokens": (run.get("usage") or {}).get("prompt_tokens", ""),
            "completion_tokens": (run.get("usage") or {}).get("completion_tokens", ""),
            "answer": answer or "",
            "citations": json.dumps(citations, ensure_ascii=False),
            "answer_match": answer_match,
            "citation_ids_in_input": (
                "是" if citation_ids.issubset(selected_ids) else "否"
            ) if citations else ("无引用" if answer is not None else "无法判断"),
            "json_valid": "是" if not parse_error else "否",
            "manual_semantic_review": "待人工核查",
            "error": parse_error or run.get("error", ""),
            "raw_content": content,
            "log_file": path.name,
        })

    with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"评分表已生成：{OUTPUT_FILE}")
    print(f"共读取 {len(rows)} 条日志。")
    print("注意：dry-run/mock 记录也会保留；正式统计时需区分真实调用。")
    print("答案匹配仅使用公开开发集参考答案；其他题目会标记为无参考答案。")
    print("语义支持、首次/重试判定仍需人工核查。")


if __name__ == "__main__":
    main()
