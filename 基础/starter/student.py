"""待候选人实现。避免读取dev_answers或题号/condition来构造答案。"""
import re


def prepare_messages(question, passages):
    """
    返回模型消息。
    只使用问题和给定资料。
    """

    evidence = "\n\n".join(
        f"[{p['id']}] {p['text']}"
        for p in passages
    )

    system_prompt = """你是一个严格基于证据回答问题的问答助手。

规则：

1. 只能使用用户提供的资料回答。
2. 不允许使用外部知识补充。
3. 如果资料不足以确定答案，answer 必须写“证据不足”。
4. citations 只能填写真正支持答案的资料ID。
5. 不要输出推理过程。
6. 只输出合法JSON。

格式必须严格为：

{"answer":"简短答案","citations":["P123456"]}
"""

    user_prompt = f"""问题：

{question}

资料：

{evidence}

请直接输出JSON答案。"""


    return [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]



def improve(question, passages):
    """
    改进方法：
    基于证据字段一致性的排序。

    优先级：
    1. 项目/版本/时间/批次/指标关键词匹配
    2. 普通文本关键词匹配

    不修改资料内容，只调整顺序。
    """

    def tokenize(text):
        tokens = re.findall(
            r"[A-Za-z]+|\d+(?:\.\d+)?|[\u4e00-\u9fff]+",
            text.lower()
        )

        result = []

        for token in tokens:
            if re.fullmatch(r"[\u4e00-\u9fff]+", token):
                result.extend(
                    token[i:i+2]
                    for i in range(len(token)-1)
                )
            else:
                result.append(token)

        return result


    question_tokens = set(tokenize(question))


    # 这些词决定文档是否属于同一个实验条件
    important_patterns = [
        r"[a-z]+\d+",
        r"\d{4}-\d{2}",
        r"版本",
        r"批次",
        r"实验",
        r"链路",
        r"耗时",
        r"中位数",
        r"平均",
        r"能耗",
        r"请求"
    ]


    def field_score(text):

        score = 0

        text_lower = text.lower()

        # 普通关键词
        passage_tokens = set(tokenize(text))
        score += len(
            question_tokens & passage_tokens
        )


        # 关键字段额外加权
        for pattern in important_patterns:

            q_match = re.findall(
                pattern,
                question.lower()
            )

            p_match = re.findall(
                pattern,
                text_lower
            )

            if q_match and p_match:
                overlap = set(q_match) & set(p_match)

                score += len(overlap) * 3


        return score


    return sorted(
        passages,
        key=lambda p: field_score(p["text"]),
        reverse=True
    )