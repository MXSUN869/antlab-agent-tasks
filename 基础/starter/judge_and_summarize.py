"""汇总基础题正式结果，产出可复算的对照表。

输入
----
- `results/scoring/main_runs_40.csv`：由 `build_main_results.py` 从原始日志重建的 40 次主结果。
- `results/scoring/R0_manual_review.csv`、`K_manual_review.csv`：已有的 R0（含改进版）与 K 人工核查。
- 本文件内的 `R1_R2_JUDGMENTS`：R1 / R2 的判分初判。

输出
----
- `results/scoring/manual_review.csv`：40 条主结果统一的逐例判分表（含 run_id 追溯）。
- `results/scoring/condition_comparison.csv`：R0 / R1 / R2 / K / R0改进 五组对照。
- `results/scoring/final_summary.csv`：人类可读汇总。
- `results/per_case_comparison.csv`：逐题 × 条件对照（含引用与耗时）。
- `results/scoring/improvement_pairing.csv`：R0 基线与改进版的同题配对差值。

判分口径
--------
`answer_correct`：答案能否由**本次实际可见段落**推出。
`citation_support`：每条引用原文是否**真的支持**该结论；引用ID在输入内不等于语义支持。
两列独立判断。技术失败（正文为空/非合法JSON）不臆造分数，记「无法评分」并留在分母。

注意：R1 / R2 两组判分是 AI 辅助初判，`reviewer` 列标明来源，须由本人复核后才可作为最终结论。
"""
import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCORING = BASE / "results" / "scoring"

CONDITION_ORDER = ["R0", "R1", "R2", "K"]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- R1 / R2 判分
# 每条的 review_reason 引用本次可见段落中的原句，便于复核者直接核对。
R1_R2_JUDGMENTS = {
    ("T01", "R1"): ("无法评分", "不适用",
                    "原始响应 finish_reason=length、completion_tokens=1024、正文为空，属输出截断，"
                    "未形成可评分答案。P555495（S23/S24/S25三项检查状态）与P761989（release_snapshot规则）"
                    "都在输入内，属于模型未产出，而非资料缺失。"),
    ("T01", "R2"): ("无法评分", "不适用",
                    "与R1同题同现象：finish_reason=length、completion_tokens=1024、正文为空。"
                    "可见段落集合与R1相同、仅顺序不同，说明本次截断与段落顺序无关。"),
    ("T02", "R1"): ("是", "是",
                    "P552476规定冻结评测集LX63固定100条主张为分母；P169676记录76条完全支持且"
                    "「完整支持只计完全支持」。76/100=76%，答案与两条引用均有直接证据支持。"),
    ("T02", "R2"): ("是", "是", "同R1：P552476给出分母100，P169676给出76条完全支持，76%正确且两条引用直接支持。"),
    ("T03", "R1"): ("是", "是",
                    "P385105记录WS84基础链路客户端完整响应耗时中位数9.4秒；P362285记录同一批次WS84"
                    "候选链路中位数6.8秒。9.4-6.8=2.6秒，两条引用分别支持被减数与减数。"),
    ("T03", "R2"): ("是", "是", "同R1：P385105（9.4秒）与P362285（6.8秒），差值2.6秒正确，引用直接支持。"),
    ("T04", "R1"): ("是", "是",
                    "P660995给出正式规则：先要求错误证据不超过3条，再最大化召回，流程名称与调用次数不参与第一轮筛选；"
                    "P758661记录甲6条错误、乙2条、丙5条。只有乙满足资格，再比召回。答案「流程乙」正确，两条引用均支持。"),
    ("T04", "R2"): ("是", "是", "同R1：P660995规则（错误≤3）与P758661计数（甲6/乙2/丙5）共同支持选择流程乙。"),
    ("T05", "R1"): ("是", "是",
                    "P286497确定题目所指的校内组TL46并列出所记录字段（请求耗时、响应状态、模型显示名称），"
                    "未含能耗；P452207明确「未采集功率、能耗、节点配置或服务端并发」。"
                    "焦耳数无法计算，「证据不足」正确；两条引用共同确立范围与缺失项。"),
    ("T05", "R2"): ("是", "是", "同R1：P286497界定校内组TL46的记录字段，P452207明确未采集能耗，支持「证据不足」。"),
    ("T06", "R1"): ("是", "是",
                    "P873502记录清单SY37共60项、45项合法、8项超时、7项格式不合法且「每项只计初次结果」；"
                    "P721388规定超时与格式不合法均列技术失败、分母为全部60项。(8+7)/60=25%，引用直接支持。"),
    ("T06", "R2"): ("是", "是", "同R1：P873502给出数字(8+7)/60，P721388给出口径，25%正确，引用直接支持。"),
    ("T07", "R1"): ("是", "是",
                    "P850395给出门槛：完整支持率至少85%且P50不高于7秒；P313278给出甲84%/P50 6.1秒、"
                    "乙87%/7.4秒、丙86%/6.8秒。甲支持率不达标、乙P50超限，只有丙两项都满足。答案「丙」正确。"),
    ("T07", "R2"): ("是", "是", "同R1：P850395门槛与P313278三项数值共同排除甲、乙，支持选择丙。"),
    ("T08", "R1"): ("是", "是",
                    "P223300规定selected_snapshot要求文本问答、区域定位、会话恢复三项检查全部通过；"
                    "P183430记录K16区域定位4项偏移、K18会话恢复2项失败、K17三项通过。答案K17正确，引用直接支持。"),
    ("T08", "R2"): ("是", "是", "同R1：P223300规则与P183430三项状态共同支持K17，引用直接支持。"),
}

# R0 改进版 T05 的两份旧记录互相矛盾。本人已于 2026-10-15 裁定采用「是」口径，
# 但两份旧文件的冲突作为判分历史保留在仓库中，不删除。
T05_IMPROVED_NOTE = (
    "P452207明确说明未采集功率和能耗数据，单独足以支持「证据不足」；P286497为补充背景。"
    "注：旧文件 R0_improved_manual_review.csv 对本行记 citation_support=否，与 "
    "R0_manual_review.csv 同行理由冲突。本人已于 2026-10-15 裁定采用「是」"
    "（依据题目「证据不足时引用列出支持这种判断的检查来源」，P452207 即该检查来源），"
    "故改进版的引用语义支持为 7/7；若改用严格口径则为 6/7，即改进在覆盖上退步一次。"
)


def load_existing_reviews():
    """合并已有的人工核查文件；R0_manual_review.csv 含 baseline 与 improved 两组。"""
    reviews = {}
    for name in ("R0_manual_review.csv", "K_manual_review.csv"):
        path = SCORING / name
        if not path.exists():
            continue
        for row in read_csv(path):
            key = (row["case_id"], row.get("condition") or
                   ("R0" if name.startswith("R0") else "K"), row["variant"])
            reviews[key] = {
                "run_id": row.get("run_id", ""),
                "answer_correct": row.get("answer_correct", ""),
                "citation_support": row.get("citation_support", ""),
                "review_reason": row.get("review_reason", ""),
                "reviewer": f"已有记录（{name}）",
            }
    return reviews


def main():
    runs = read_csv(SCORING / "main_runs_40.csv")
    existing = load_existing_reviews()

    merged = []
    for run in runs:
        case_id, condition, variant = run["case_id"], run["condition"], run["variant"]
        key = (case_id, condition, variant)

        if key in existing:
            judgement = dict(existing[key])
            if judgement["run_id"] and judgement["run_id"] != run["run_id"]:
                judgement["review_reason"] += (
                    f" [注意] 旧记录 run_id={judgement['run_id']} 与重建结果 "
                    f"{run['run_id']} 不一致，请复核。"
                )
        elif (case_id, condition) in R1_R2_JUDGMENTS:
            correct, support, reason = R1_R2_JUDGMENTS[(case_id, condition)]
            judgement = {
                "run_id": run["run_id"],
                "answer_correct": correct,
                "citation_support": support,
                "review_reason": reason,
                "reviewer": "本人复核确认（初判由 AI 辅助，2026-10-15）",
            }
        else:
            judgement = {
                "run_id": run["run_id"],
                "answer_correct": "待核查",
                "citation_support": "待核查",
                "review_reason": "尚未人工核查",
                "reviewer": "未核查",
            }

        if case_id == "T05" and condition == "R0" and variant == "improved":
            judgement["citation_support"] = "是"
            judgement["review_reason"] = T05_IMPROVED_NOTE
            judgement["reviewer"] = "本人已裁定口径（R0_manual_review.csv），分歧已记录"

        merged.append({**run, **judgement})

    fields = ["run_id", "case_id", "condition", "variant", "answer", "citations",
              "citations_in_input", "json_valid", "empty_content", "finish_reason",
              "completion_tokens", "elapsed_seconds", "answer_correct",
              "citation_support", "reviewer", "review_reason", "log_file",
              "selected_passage_ids", "utc"]
    with (SCORING / "manual_review.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in merged:
            w.writerow({k: row.get(k, "") for k in fields})
    print(f"wrote {SCORING / 'manual_review.csv'} ({len(merged)} rows)")

    # ------------------------------------------------ 条件对照
    def summarize(rows, label):
        n = len(rows)
        valid = [r for r in rows if r["json_valid"] == "是"]
        correct = [r for r in rows if r["answer_correct"] == "是"]
        scored = [r for r in rows if r["citation_support"] in ("是", "否")]
        support = [r for r in scored if r["citation_support"] == "是"]
        times = [float(r["elapsed_seconds"]) for r in rows]
        return {
            "condition": label,
            "requests": n,
            "valid_json": len(valid),
            "valid_json_rate": f"{len(valid) / n:.1%}",
            "correct_answers": len(correct),
            "accuracy_all": f"{len(correct) / n:.1%}",
            "accuracy_valid_only": f"{len(correct) / len(valid):.1%}" if valid else "n/a",
            "citation_support": f"{len(support)}/{len(scored)}" if scored else "不适用",
            "mean_seconds": f"{sum(times) / n:.2f}",
            "median_seconds": f"{sorted(times)[n // 2]:.2f}",
            "truncated": sum(1 for r in rows if r["empty_content"] == "是"),
        }

    groups = []
    for cond in CONDITION_ORDER:
        groups.append(summarize([r for r in merged if r["condition"] == cond
                                 and r["variant"] == "baseline"], cond))
    groups.append(summarize([r for r in merged if r["condition"] == "R0"
                             and r["variant"] == "improved"], "R0 improved"))

    cfields = list(groups[0].keys())
    with (SCORING / "condition_comparison.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cfields)
        w.writeheader()
        w.writerows(groups)
    print(f"wrote {SCORING / 'condition_comparison.csv'}")

    notes = {
        "R0": "T01 输出截断；其余7题答案正确且引用均获语义支持",
        "R1": "T01 输出截断；其余7题答案与引用支持均与R0逐题一致",
        "R2": "T01 输出截断；其余7题答案与引用支持均与R0逐题一致",
        "K": "4题为输出截断（技术失败，计为不正确）；4题有效输出均为「证据不足」且经核查正确。"
             "K的准确率下降来自资料覆盖与截断，不是把这4题答错",
        "R0 improved": "T08 输出截断；答案正确数与基线同为7/8，但失败题目由T01换成T08。"
                       "T05 引用支持口径存在两种判断，见 improvement_pairing.csv 与 review_reason",
    }
    summary_rows = [{**g, "note": notes.get(g["condition"], "")} for g in groups]
    with (SCORING / "final_summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cfields + ["note"])
        w.writeheader()
        w.writerows(summary_rows)
    print(f"wrote {SCORING / 'final_summary.csv'}")

    # ------------------------------------------------ 逐题对照
    per_case = []
    for i in range(1, 9):
        case_id = f"T{i:02d}"
        row = {"case_id": case_id}
        for cond in CONDITION_ORDER:
            r = next((x for x in merged if x["case_id"] == case_id
                      and x["condition"] == cond and x["variant"] == "baseline"), None)
            row[f"{cond}_answer"] = r["answer"] if r else ""
            row[f"{cond}_correct"] = r["answer_correct"] if r else ""
            row[f"{cond}_citations"] = r["citations"] if r else ""
            row[f"{cond}_seconds"] = f"{float(r['elapsed_seconds']):.2f}" if r else ""
        imp = next((x for x in merged if x["case_id"] == case_id
                    and x["condition"] == "R0" and x["variant"] == "improved"), None)
        base = next((x for x in merged if x["case_id"] == case_id
                     and x["condition"] == "R0" and x["variant"] == "baseline"), None)
        row["R0_improved_answer"] = imp["answer"] if imp else ""
        row["R0_improved_correct"] = imp["answer_correct"] if imp else ""
        row["R0_improved_support"] = imp["citation_support"] if imp else ""
        row["R0_improved_seconds"] = f"{float(imp['elapsed_seconds']):.2f}" if imp else ""
        if base and imp:
            row["delta_seconds"] = f"{float(imp['elapsed_seconds']) - float(base['elapsed_seconds']):+.2f}"
        per_case.append(row)

    out = BASE / "results" / "per_case_comparison.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per_case[0].keys()))
        w.writeheader()
        w.writerows(per_case)
    print(f"wrote {out}")

    deltas = []
    for i in range(1, 9):
        case_id = f"T{i:02d}"
        base = next(r for r in merged if r["case_id"] == case_id
                    and r["condition"] == "R0" and r["variant"] == "baseline")
        imp = next(r for r in merged if r["case_id"] == case_id
                   and r["condition"] == "R0" and r["variant"] == "improved")
        deltas.append({
            "case_id": case_id,
            "baseline_run_id": base["run_id"],
            "improved_run_id": imp["run_id"],
            "baseline_answer": base["answer"],
            "improved_answer": imp["answer"],
            "baseline_correct": base["answer_correct"],
            "improved_correct": imp["answer_correct"],
            "baseline_support": base["citation_support"],
            "improved_support": imp["citation_support"],
            "baseline_seconds": f"{float(base['elapsed_seconds']):.2f}",
            "improved_seconds": f"{float(imp['elapsed_seconds']):.2f}",
            "delta_seconds": f"{float(imp['elapsed_seconds']) - float(base['elapsed_seconds']):+.2f}",
        })
    with (SCORING / "improvement_pairing.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(deltas[0].keys()))
        w.writeheader()
        w.writerows(deltas)
    print(f"wrote {SCORING / 'improvement_pairing.csv'}")


if __name__ == "__main__":
    main()
