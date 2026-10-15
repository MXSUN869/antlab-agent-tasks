"""核对「已有记录」的合并，并生成便于人工速览的复核表。

做两件事
--------
1. **自动核对（不需要人看）**：对 `manual_review.csv` 的 40 行，逐行拿 `run_id`
   回到 `runs/<run_id>.json` 重新解析，确认
   - 记录里的 `answer` 与日志中重新解析出的答案一致；
   - 记录里的 `citations` 与日志一致；
   - `citations_in_input` 的判断与日志中 `selected_passage_ids` 相符。
   这一步能直接发现「合并时 run_id 与判分错位」这类问题。
2. **生成速览**：把沿用本人旧判分记录的 24 行（R0 基线 8 + R0 改进 8 + K 8，
   其中 T05 改进版的口径已由本人裁定）整理成一份速览，只保留问题、答案、引用、
   原判结论、**原判理由原文**与被引段落的判别性首句，便于逐条抽查。

用法
----
    python tools/audit_existing_reviews.py
"""
import csv
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASIC = REPO / "基础"
SCORING = BASIC / "results" / "scoring"


def parse_answer(content):
    """与 build_main_results.py 的 parse_output 保持同一口径。"""
    if not content.strip():
        return None, []
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        return None, []
    if not isinstance(obj, dict):
        return None, []
    answer = obj.get("answer")
    citations = obj.get("citations")
    if not isinstance(citations, list):
        citations = []
    return (answer if isinstance(answer, str) else None), citations


def info(text, limit=170):
    first = re.split(r"\s+", text.strip())[0]
    return first if len(first) <= limit else first[:limit] + "…"


def audit(rows):
    """逐行回到原始日志核对。返回 (问题列表, 统计)。"""
    problems = []
    stats = {"checked": 0, "log_missing": 0}
    for row in rows:
        rid = row["run_id"]
        log = BASIC / "runs" / f"{rid}.json"
        if not log.is_file():
            stats["log_missing"] += 1
            problems.append(f"{row['case_id']}/{row['condition']}/{row['variant']}: 找不到日志 {rid}.json")
            continue
        stats["checked"] += 1
        run = json.loads(log.read_text(encoding="utf-8"))
        try:
            content = run["response"]["choices"][0]["message"]["content"] or ""
        except (KeyError, TypeError, IndexError):
            content = ""
        answer, citations = parse_answer(content)

        if (answer or "") != (row["answer"] or ""):
            problems.append(
                f"{row['case_id']}/{row['condition']}/{row['variant']}: 答案不一致 "
                f"记录={row['answer']!r} 日志={answer!r}")
        if json.dumps(citations, ensure_ascii=False) != (row["citations"] or "[]"):
            problems.append(
                f"{row['case_id']}/{row['condition']}/{row['variant']}: 引用不一致 "
                f"记录={row['citations']!r} 日志={json.dumps(citations, ensure_ascii=False)!r}")

        selected = set(run.get("selected_passage_ids") or [])
        expect = ("是" if set(citations).issubset(selected) else "否") if citations \
            else ("无引用" if answer is not None else "无法判断")
        if expect != row["citations_in_input"]:
            problems.append(
                f"{row['case_id']}/{row['condition']}/{row['variant']}: "
                f"citations_in_input 不符 记录={row['citations_in_input']} 应为={expect}")
    return problems, stats


def build_sheet(rows, cases, all_rows):
    lines = [
        "# 已有判分记录复核速览（24 行）",
        "",
        "这些行**沿用本人此前的判分记录**（`R0_manual_review.csv` 与 `K_manual_review.csv`），",
        "本轮只做合并与统一表头，**没有重新判分**。因此需要抽查的是：",
        "",
        "1. 合并有没有**错位**（`run_id` 与答案、引用是否还配得上）——已由脚本自动核对，见文件末；",
        "2. 你当时的判分结论与理由，放到统一表里以后是否仍然成立。",
        "",
        "速览只保留判断所需内容；完整原文见 `review_R1_R2.md`，完整理由见 `manual_review.csv`。",
        "",
        "---",
        "",
    ]
    for row in rows:
        case = cases[row["case_id"]]
        by_id = {p["id"]: p for p in case["passages"]}
        cites = json.loads(row["citations"])
        tag = "（口径已由本人裁定）" if row["reviewer"].startswith("本人已裁定") else ""
        lines += [
            f"### {row['case_id']} / {row['condition']} / {row['variant']}{tag}",
            "",
            f"- **run_id**：`{row['run_id']}`",
            f"- **问题**：{case['question']}",
            f"- **模型答案**：`{row['answer']}`　**引用**：`{row['citations']}`",
            f"- **技术状态**：JSON合法={row['json_valid']}，finish_reason={row['finish_reason']}，"
            f"{float(row['elapsed_seconds']):.2f}s",
            f"- **原判**：答案正确性=**{row['answer_correct']}**；引用语义支持=**{row['citation_support']}**",
            "",
            "  本次可见段落的判别性首句（★ = 模型引用）：",
            "",
        ]
        for pid in json.loads(row["selected_passage_ids"]):
            mark = "★" if pid in cites else "　"
            lines.append(f"  - {mark} `{pid}`：{info(by_id[pid]['text'])}")
        lines += ["", f"  <sub>原判理由（逐字保留）：{row['review_reason']}</sub>", ""]
    return "\n".join(lines)


def main():
    rows = list(csv.DictReader(
        (SCORING / "manual_review.csv").open(encoding="utf-8-sig", newline="")))
    cases = {c["id"]: c for c in json.loads((BASIC / "data" / "cases.json").read_text(encoding="utf-8"))}

    print("=" * 66)
    print("第 1 部分：自动核对（40 行逐行回到原始日志）")
    print("=" * 66)
    problems, stats = audit(rows)
    print(f"  打开并比对日志：{stats['checked']} 行；找不到日志：{stats['log_missing']} 行")
    if problems:
        print(f"  ✗ 发现 {len(problems)} 处不一致：")
        for p in problems:
            print("     -", p)
    else:
        print("  ✓ 全部一致：答案、引用、引用是否在输入内，三列都与原始日志对得上")
        print("    → 合并没有错位；40 行的 run_id 与判分结论是配对正确的")

    print()
    print("=" * 66)
    print("第 2 部分：生成「已有记录」速览")
    print("=" * 66)
    existing = [r for r in rows
                if r["reviewer"].startswith("已有记录") or r["reviewer"].startswith("本人已裁定")]
    import collections
    print("  涉及行数：", len(existing))
    for k, v in collections.Counter(
            f"{r['condition']}/{r['variant']}" for r in existing).most_common():
        print(f"    {k:16} {v} 行")
    out = SCORING / "已有记录复核速览.md"
    text = build_sheet(existing, cases, rows)
    footer = [
        "",
        "---",
        "",
        "## 自动核对结果（脚本输出，无需人工复核）",
        "",
        f"- 打开并比对原始日志：**{stats['checked']} 行**；找不到日志：{stats['log_missing']} 行",
    ]
    if problems:
        footer.append(f"- ✗ 发现 **{len(problems)}** 处不一致：")
        footer += [f"  - {p}" for p in problems]
    else:
        footer.append("- ✓ 答案、引用、引用是否在输入内三列，逐行与 `runs/<run_id>.json` 一致")
        footer.append("- ✓ 因此**合并没有错位**：40 行的 run_id 与判分结论配对正确")
        footer.append("- 复算命令：`python tools/audit_existing_reviews.py`")
    out.write_text(text + "\n".join(footer) + "\n", encoding="utf-8")
    print(f"  已写出：{out}")
    print(f"  篇幅：{len(text)} 字符")


if __name__ == "__main__":
    main()
