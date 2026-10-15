import argparse
import importlib
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
RUNS = ROOT.parent / "runs"
DATA = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
ENGINE = None


def read_run_file(filename):
    # Only allow these two fixed, local result files.
    if filename not in ("baseline.json", "repaired.json"):
        raise ValueError("unsupported_file")

    path = RUNS / filename
    if not path.is_file():
        raise FileNotFoundError(filename)

    value = json.loads(path.read_text(encoding="utf-8-sig"))

    # The runner normally saves a list of {case_id, input, output} records.
    # Also tolerate a wrapper object containing a "results" list.
    if isinstance(value, dict) and isinstance(value.get("results"), list):
        value = value["results"]

    if not isinstance(value, list):
        raise ValueError(filename + " must contain a JSON list")

    return value


def evidence_ids(output):
    evidence = output.get("evidence", [])
    if not isinstance(evidence, list):
        return []
    return [
        str(item.get("id", ""))
        for item in evidence
        if isinstance(item, dict) and item.get("id") is not None
    ]


def comparison_data():
    baseline = read_run_file("baseline.json")
    repaired = read_run_file("repaired.json")

    def index_records(records):
        indexed = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            case_id = record.get("case_id")
            output = record.get("output")
            if case_id is not None and isinstance(output, dict):
                indexed[str(case_id)] = record
        return indexed

    before = index_records(baseline)
    after = index_records(repaired)
    case_ids = list(dict.fromkeys(
        [str(r["case_id"]) for r in baseline
         if isinstance(r, dict) and "case_id" in r]
        + [str(r["case_id"]) for r in repaired
           if isinstance(r, dict) and "case_id" in r]
    ))

    rows = []
    for case_id in case_ids:
        old_record = before.get(case_id)
        new_record = after.get(case_id)
        old = old_record.get("output", {}) if old_record else {}
        new = new_record.get("output", {}) if new_record else {}

        rows.append({
            "case_id": case_id,
            "baseline": {
                "present": old_record is not None,
                "evidence_ids": evidence_ids(old),
                "answer": old.get("answer"),
                "locator_status": old.get("locator_status"),
                "support_status": old.get("support_status"),
                "status": old.get("status"),
                "cache_hit": old.get("cache_hit"),
                "run_kind": old.get("run_kind"),
                "request_id": old.get("request_id"),
            },
            "repaired": {
                "present": new_record is not None,
                "evidence_ids": evidence_ids(new),
                "answer": new.get("answer"),
                "locator_status": new.get("locator_status"),
                "support_status": new.get("support_status"),
                "status": new.get("status"),
                "cache_hit": new.get("cache_hit"),
                "run_kind": new.get("run_kind"),
                "request_id": new.get("request_id"),
            },
        })

    return {
        "source_files": ["runs/baseline.json", "runs/repaired.json"],
        "case_count": len(rows),
        "rows": rows,
    }


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, value, mime="application/json; charset=utf-8"):
        raw = value if isinstance(value, bytes) else json.dumps(
            value, ensure_ascii=False
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/":
            self.reply(
                200,
                (ROOT / "index.html").read_bytes(),
                "text/html; charset=utf-8",
            )
        elif self.path == "/api/cases":
            self.reply(200, DATA)
        elif self.path == "/api/comparison":
            try:
                self.reply(200, comparison_data())
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self.reply(500, {
                    "error": "comparison_unavailable",
                    "detail": str(exc),
                })
        else:
            self.reply(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/api/run":
            return self.reply(404, {"error": "not_found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 32768:
                raise ValueError("invalid_size")
            body = json.loads(self.rfile.read(length))
            case = next(c for c in DATA["cases"] if c["id"] == body["case_id"])
            if body.get("reset"):
                ENGINE.cache.clear()
            self.reply(
                200,
                ENGINE.evaluate(case["request"], DATA["corpus"], case["draft"]),
            )
        except (ValueError, KeyError, StopIteration, TypeError) as exc:
            self.reply(400, {"error": str(exc) or "invalid_case"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--engine", default="challenge:Engine")
    args = parser.parse_args()

    module, name = args.engine.split(":")
    ENGINE = getattr(importlib.import_module(module), name)()

    print(
        "Offline replay: http://127.0.0.1:" + str(args.port),
        flush=True,
    )
    HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
