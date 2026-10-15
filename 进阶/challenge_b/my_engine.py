import copy
import hashlib
import json
import time
import uuid


class Engine:
    def __init__(self):
        self.cache = {}

    @staticmethod
    def _canonical(value):
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def evaluate(self, request, corpus, draft):
        started = time.perf_counter()

        # 缓存身份必须同时满足 spec.md 第 5 条的两半：
        #   (a) 不允许改变资料/配置/响应后的请求命中旧结果 —— 因此 corpus 与 draft
        #       整体进入键，snapshot 也进入键；
        #   (b) 允许复用等价输入的结果 —— 因此按 spec.md 第 2、3 条的语义把请求规范化：
        #       排序只按空格分词与 tags 的交集，故 query 的大小写与首尾空白不影响结果；
        #       doc_ids 是集合语义，故其顺序与重复项不影响结果。
        # 这样「大小写不同」和「doc_ids 顺序不同」仍可复用缓存，而跨 snapshot 的请求不会。
        extra_fields = {
            key: value
            for key, value in request.items()
            if key not in ("query", "doc_ids", "snapshot", "k")
        }
        cache_input = {
            "query": str(request.get("query", "")).strip().lower(),
            "doc_ids": sorted({str(d) for d in (request.get("doc_ids") or [])}),
            "snapshot": request.get("snapshot"),
            "k": request.get("k"),
            "extra_fields": extra_fields,
            "corpus": corpus,
            "draft": draft,
        }
        serialized = self._canonical(cache_input)
        key = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        hit = key in self.cache

        if hit:
            result = copy.deepcopy(self.cache[key])
        else:
            requested_docs = set(request.get("doc_ids", []))
            snapshot = request.get("snapshot")
            query = request.get("query", "").strip().lower()
            terms = set(query.split())
            k = request.get("k", 0)

            # First establish the requested document/snapshot scope.
            scoped = [
                b for b in corpus
                if b.get("doc_id") in requested_docs
                and b.get("snapshot") == snapshot
            ]

            if not scoped:
                evidence = []
                status = "invalid_scope"
            else:
                # Rank only within scope, then remove zero-score items,
                # then apply k. Out-of-scope items cannot consume slots.
                ranked = sorted(
                    scoped,
                    key=lambda b: (
                        -len(terms & set(b.get("tags", []))),
                        b.get("id", ""),
                    ),
                )
                positive = [
                    b for b in ranked
                    if len(terms & set(b.get("tags", []))) > 0
                ]
                evidence = positive[:max(0, k)]
                status = "ok"

            citations = draft.get("citations", [])
            evidence_ids = {b.get("id") for b in evidence}

            if not citations:
                locator_status = "missing"
            elif all(c in evidence_ids for c in citations):
                locator_status = "valid"
            else:
                locator_status = "invalid"

            result = {
                "answer": draft.get("answer", ""),
                "citations": copy.deepcopy(citations),
                "evidence": copy.deepcopy(evidence),
                "locator_status": locator_status,
                # ID validity is not semantic verification.
                "support_status": "not_checked",
                "judgment_source": "not_checked",
                "status": status,
            }

            self.cache[key] = copy.deepcopy(result)

        # Per-call metadata must describe this request, even on cache hits.
        result.update(
            request_id=str(uuid.uuid4()),
            request=copy.deepcopy(request),
            cache_hit=hit,
            elapsed_ms=(time.perf_counter() - started) * 1000,
            run_kind="offline_replay",
        )
        return result
