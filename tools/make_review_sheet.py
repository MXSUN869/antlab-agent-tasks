"""生成 R1 / R2 复核速览。

为什么需要
----------
`review_R1_R2.md` 把每段原文完整列出，但题目的段落里含大量重复填充文本，
逐条复核时噪音太大。本脚本只保留**判断所必需**的内容：
问题、模型答案、引用、以及被引段落的**判别性首句**。

判别性首句的取法：段落文本里，重复的填充内容都出现在第一个连续空白之后，
因此取第一个连续空白之前的部分作为该段的判别性内容。

用法
----
    python tools/make_review_sheet.py

输出 `基础/results/scoring/R1_R2_复核速览.md`。
修改判分后请重跑本脚本，使速览与 `manual_review.csv` 保持一致。
"""
import csv
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASIC = REPO / "基础"
SCORING = BASIC / "results" / "scoring"


def info(text, limit=170):
    """取段落的判别性首句。

    题目的段落由「判别性内容」+ 大量重复填充文本组成，两者之间是空白分隔；
    中文正文内部不含空白，因此按第一个空白切分即可。
    """
    first = re.split(r"\s+", text.strip())[0]
    return first if len(first) <= limit else first[:limit] + "…"


def main():
    cases = {c["id"]: c for c in json.loads((BASIC / "data" / "cases.json").read_text(encoding="utf-8"))}
    with (SCORING / "manual_review.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["condition"] in ("R1", "R2")]

    L = [
        "# R1 / R2 复核速览（16 条）",
        "",
        "这份文件只保留**判断所必需**的内容：问题、模型答案、引用、以及被引段落的**判别性首句**。",
        "完整段落原文见 `review_R1_R2.md`；逐条完整理由见 `manual_review.csv` 的 `review_reason` 列。",
        "",
        "**怎么核**：对每一行问自己两个问题 ——",
        "1. 这个答案能不能**从本次可见段落推出**？（→ 答案正确性）",
        "2. 每条引用的原文是不是**真的支持**这个结论？（→ 引用语义支持）",
        "",
        "两列独立判断。**引用 ID 在输入内，不等于内容被支持。**",
        "",
        "复核完成后，请把 `manual_review.csv` 里对应行的 `reviewer` 列改为你的结论，",
        "并在 `基础/starter/judge_and_summarize.py` 的 `R1_R2_JUDGMENTS` 中同步你改过的判断。",
        "",
        "---",
        "",
        "## 缩略记号",
        "",
        "先扫一眼每条问题的正确答案类型，便于快速发现异常：",
        "",
        "| 题号 | 问题要点 | R0 基线答案（已判） |",
        "|---|---|---|",
    ]
    allrows = list(csv.DictReader(
        (SCORING / "manual_review.csv").open(encoding="utf-8-sig", newline="")))
    for cid in [f"T{i:02d}" for i in range(1, 9)]:
        r0 = next((x for x in allrows if x["case_id"] == cid and x["condition"] == "R0"
                   and x["variant"] == "baseline"), None)
        ans = r0["answer"] if r0 and r0["answer"] else "（截断）"
        L.append(f"| {cid} | {cases[cid]['question'][:34]}… | `{ans}` |")
    L += ["", "---", ""]

    for cond in ("R1", "R2"):
        L += [f"## 条件 {cond}", ""]
        for cid in [f"T{i:02d}" for i in range(1, 9)]:
            r = next((x for x in rows if x["case_id"] == cid and x["condition"] == cond), None)
            if r is None:
                L += [f"### {cid} {cond} —— 缺记录", ""]
                continue
            case = cases[cid]
            by_id = {p["id"]: p for p in case["passages"]}
            cites = json.loads(r["citations"])
            L += [
                f"### {cid} {cond}",
                "",
                f"- **问题**：{case['question']}",
                f"- **模型答案**：`{r['answer']}`　**引用**：`{r['citations']}`",
                f"- **技术状态**：JSON合法={r['json_valid']}，"
                f"finish_reason={r['finish_reason']}，{float(r['elapsed_seconds']):.2f}s",
            ]
            if r["answer_correct"] == "无法评分":
                L.append("- **我的初判**：无法评分（输出被长度上限截断，正文为空）——"
                         "**这一行你只需确认「按题目要求保留在分母」这个处理**，没有语义可判。")
                L += ["", f"  <sub>理由：{r['review_reason']}</sub>", ""]
                continue
            L.append(f"- **我的初判**：答案正确性=**{r['answer_correct']}**；"
                     f"引用语义支持=**{r['citation_support']}**")
            L += ["", "  本次可见段落的判别性首句（★ = 模型引用）：", ""]
            for pid in json.loads(r["selected_passage_ids"]):
                mark = "★" if pid in cites else "　"
                L.append(f"  - {mark} `{pid}`：{info(by_id[pid]['text'])}")
            L += ["", f"  <sub>理由：{r['review_reason']}</sub>", ""]
        L += ["---", ""]

    out = SCORING / "R1_R2_复核速览.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out}")
    print(f"篇幅：{len('\n'.join(L))} 字符")


if __name__ == "__main__":
    main()
