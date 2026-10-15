"""自建边界检查：范围正确但该快照下没有任何资料。

用例
----
查询 `metadata beta`、doc_ids=beta、snapshot=v999。v999 在 data.json 中不存在，
但 beta 文档本身存在（其资料都在 v1）。这属于"文档合法、快照不存在"的边界，
与 `R07`（doc_ids=missing，文档本身不存在）不同。

预期依据（spec.md 第 1、3 条）
-----------------------------
- 范围由 doc_ids 与 snapshot 共同确定，未知组合返回 invalid_scope；
- 不允许回退到另一快照的资料，因此不得把 v1 的 b05 当成本次有效证据；
- 引用有效性要求每个引用都在本次实际检索证据中，越界须标为无效。

预期：evidence 为空、locator_status 为 invalid、且**总体状态应能被区分**，
不能与"正常完成"混为一谈。本脚本因此同时打印 status，供人工判断区分度是否足够。

用法
----
    python 进阶/runs/test_boundary.py
    python 进阶/runs/test_boundary.py challenge
"""
import importlib
import json
import sys
from pathlib import Path

ADVANCED = Path(__file__).resolve().parents[1]   # 进阶/
sys.path.insert(0, str(ADVANCED))

REQUEST = {"query": "metadata beta", "doc_ids": ["beta"], "snapshot": "v999", "k": 2}
DRAFT = {"answer": "文档编号为beta。", "citations": ["b05"]}


def run(engine_label):
    module_name = {"challenge": "challenge_b.challenge",
                   "my_engine": "challenge_b.my_engine"}[engine_label]
    Engine = getattr(importlib.import_module(module_name), "Engine")
    data = json.loads((ADVANCED / "challenge_b" / "data.json").read_text(encoding="utf-8"))

    result = Engine().evaluate(REQUEST, data["corpus"], DRAFT)
    evidence = [b["id"] for b in result["evidence"]]
    print(f"=== 引擎：{engine_label} ===")
    print(f"  evidence       = {evidence}")
    print(f"  locator_status = {result['locator_status']}")
    print(f"  support_status = {result['support_status']}")
    print(f"  status         = {result['status']}")
    leaked = "b05" in evidence
    print(f"  -> 是否回退到另一快照的证据：{'是（违反 spec 第1条）' if leaked else '否'}")
    print()
    return {
        "evidence": evidence,
        "locator_status": result["locator_status"],
        "support_status": result["support_status"],
        "status": result["status"],
        "leaked_other_snapshot": leaked,
    }


if __name__ == "__main__":
    targets = sys.argv[1:] or ["challenge", "my_engine"]
    outcomes = {t: run(t) for t in targets}
    if any(o["leaked_other_snapshot"] for o in outcomes.values()):
        raise SystemExit("存在跨快照回退，范围约束未生效")
