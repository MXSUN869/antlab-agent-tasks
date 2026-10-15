import json
import glob
import student

# 读取题目数据
with open("../data/cases.json", "r", encoding="utf-8") as f:
    cases = {
        case["id"]: case
        for case in json.load(f)
    }

# 查找运行日志
logs = glob.glob("../runs/**/*.json", recursive=True)

print("读取到的题目数量：", len(cases))
print("找到的日志文件数量：", len(logs))

seen = set()

for path in logs:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        continue

    case_id = data.get("case_id")
    condition = data.get("condition")

    # 只检查开发集 D01-D04 的 R0 条件
    if case_id not in ("D01", "D02", "D03", "D04"):
        continue

    if condition != "R0" or case_id in seen:
        continue

    # 尝试读取日志中的段落 ID
    passage_ids = (
        data.get("selected_passage_ids")
        or data.get("passage_ids")
        or []
    )

    if not passage_ids:
        continue

    # 根据段落 ID 找回原始段落
    passage_map = {
        passage["id"]: passage
        for passage in cases[case_id]["passages"]
    }

    if any(pid not in passage_map for pid in passage_ids):
        print("\n", case_id, "：日志段落 ID 无法全部匹配")
        continue

    original_passages = [
        passage_map[pid]
        for pid in passage_ids
    ]

    improved_passages = student.improve(
        cases[case_id]["question"],
        original_passages
    )

    print("\n题目：", case_id)
    print("R0 原顺序：", passage_ids)
    print(
        "改进顺序：",
        [p["id"] for p in improved_passages]
    )

    seen.add(case_id)

if not seen:
    print("\n暂未找到符合条件的 R0 日志。")
    print("可能需要根据实际日志结构调整字段名。")