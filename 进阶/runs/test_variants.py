"""语义等价变体检查：查询大小写、doc_ids 顺序。

预期依据（spec.md 第 2、5 条）
-----------------------------
- 排序只按 query 空格分词与 tags 的交集数量，大小写不应改变分词结果；
- 范围由 doc_ids 与 snapshot 共同确定，doc_ids 是集合语义，顺序不应改变结果；
- 缓存可以复用等价输入的结果，但不允许改变资料/配置/响应后的请求命中旧结果。

因此三个变体应当给出**相同的证据集合与相同的定位状态**。这是"等价输入得到等价输出"的
正对照，用来确认修复没有把缓存削弱到"任何请求都不复用"，也没有把等价变体误判为新请求。

用法
----
    python 进阶/runs/test_variants.py            # 两个引擎都跑
    python 进阶/runs/test_variants.py challenge  # 只跑原始样机
    python 进阶/runs/test_variants.py my_engine  # 只跑修复版
"""
import importlib
import json
import sys
from pathlib import Path

ADVANCED = Path(__file__).resolve().parents[1]   # 进阶/
sys.path.insert(0, str(ADVANCED))                # 使 challenge_b 可作为包导入

BASE_REQUEST = {
    "query": "metadata beta",
    "doc_ids": ["alpha", "beta"],
    "snapshot": "v1",
    "k": 2,
}
DRAFT = {"answer": "文档编号为beta。", "citations": ["b05"]}

VARIANTS = [
    ("V1_原始请求", {}),
    ("V2_查询改大写", {"query": "METADATA BETA"}),
    ("V3_反转doc_ids", {"doc_ids": ["beta", "alpha"]}),
]


def run(engine_label):
    module_name = {"challenge": "challenge_b.challenge",
                   "my_engine": "challenge_b.my_engine"}[engine_label]
    Engine = getattr(importlib.import_module(module_name), "Engine")
    data = json.loads((ADVANCED / "challenge_b" / "data.json").read_text(encoding="utf-8"))
    corpus = data["corpus"]

    engine = Engine()
    print(f"=== 引擎：{engine_label}（{module_name}.Engine）===")
    rows = []
    for name, override in VARIANTS:
        request = {**BASE_REQUEST, **override}
        result = engine.evaluate(request, corpus, DRAFT)
        evidence = [b["id"] for b in result["evidence"]]
        rows.append((name, evidence, result["locator_status"], result["cache_hit"], result["status"]))
        print(f"  {name:14} evidence={evidence} locator={result['locator_status']} "
              f"cache_hit={result['cache_hit']} status={result['status']}")

    # 判定：三者证据集合与定位状态一致即为通过；cache_hit 允许不同。
    signatures = {(tuple(r[1]), r[2]) for r in rows}
    ok = len(signatures) == 1
    print(f"  -> 三个变体的（证据集合, 定位状态）{'一致，等价性成立' if ok else '不一致，等价性被破坏'}")
    print()
    return ok


if __name__ == "__main__":
    targets = sys.argv[1:] or ["challenge", "my_engine"]
    results = {t: run(t) for t in targets}
    if not all(results.values()):
        raise SystemExit("存在不等价的变体，请检查")
