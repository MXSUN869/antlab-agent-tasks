"""提交前清理：从归档的运行日志中移除 API Endpoint。

为什么要做
----------
`进阶/05_提交与报告格式.md` 与 `基础/03_提交要求.md` 都要求提交前
「检查并移除 API 密钥、Endpoint、私人账号信息和本地配置」。
而 `runner.py` 会把整个 config 原样写进每条运行记录，因此 140+ 份
`基础/runs/*.json` 里都带着真实 Endpoint。

这个脚本只替换 `config.endpoint` 一个字段的值，**不动**任何结果字段：

不改动的内容
------------
- `response`（模型原始响应）      —— 判分与复核的依据
- `usage` / `elapsed_seconds` / `http_status` / `status`
- `messages` / `selected_passage_ids` / `original_passage_ids`
- `data_sha256` / `student_sha256` / `dataset_version`
- `config` 里的 `provider` / `model` / `parameters` / `timeout_seconds`

因此 40 次主结果的任何数字都不发生变化。原始 Endpoint 保留在本机的
`基础/config.local.json`（已被 .gitignore 排除），不在仓库中。

用法
----
    python tools/redact_endpoint.py            # 预演，只报告将改动多少文件
    python tools/redact_endpoint.py --apply    # 实际写入
"""
import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLACEHOLDER = "<REMOVED_PER_SUBMISSION_REQUIREMENTS: see config.example.json>"
TARGETS = [REPO / "基础" / "runs", REPO / "进阶" / "runs"]


def redact_file(path):
    """返回改写后的数据；无需改动时返回 None。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    def walk(node):
        changed = False
        if isinstance(node, dict):
            endpoint = node.get("endpoint")
            if isinstance(endpoint, str) and endpoint.startswith("http") and endpoint != PLACEHOLDER:
                node["endpoint"] = PLACEHOLDER
                changed = True
            for value in node.values():
                changed = walk(value) or changed
        elif isinstance(node, list):
            for item in node:
                changed = walk(item) or changed
        return changed

    if not walk(data):
        return None
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="实际写入；缺省只预演")
    args = parser.parse_args()

    scanned = changed = 0
    for target in TARGETS:
        if not target.is_dir():
            continue
        for path in sorted(target.glob("*.json")):
            scanned += 1
            data = redact_file(path)
            if data is None:
                continue
            changed += 1
            if args.apply:
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    mode = "已写入" if args.apply else "预演（未写入，加 --apply 生效）"
    print(f"{mode}：扫描 {scanned} 个 JSON，{'改动' if args.apply else '将改动'} {changed} 个")
    if not args.apply:
        print("预演模式下不修改任何文件。")


if __name__ == "__main__":
    main()
