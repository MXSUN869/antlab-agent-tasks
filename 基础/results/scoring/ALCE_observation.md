# 公开系统观察：ALCE

## 观察对象
ALCE：Automatic LLMs' Citation Evaluation。
论文：Gao, Tianyu; Yen, Howard; Yu, Jiatong; Chen, Danqi. "Enabling Large Language Models to Generate Text with Citations." EMNLP 2023.
论文页面：https://aclanthology.org/2023.emnlp-main.398/
代码仓库：https://github.com/princeton-nlp/ALCE

## 本次完成方式
阅读论文摘要和公开代码仓库说明，观察评估维度与引用核查思路。没有安装 ALCE、下载其数据集或运行其模型；本记录不声称完成代码复现。

## 主要观察
1. ALCE 将生成质量分成流畅度、正确性和引用质量等维度，而不是只用一个总分代表所有质量。
2. 公开实现提供答案正确性相关评估，以及引用支持相关评估。
3. 引用质量不仅是引用格式是否存在，还要检查引用的文档是否支持对应的陈述。
4. 自动评估能扩大核查规模，但仍需留意自动评估器本身的局限；人工核查可以补充具体案例解释。

## 与本项目的联系
- 本项目的 answer_correct 对应答案是否正确。
- 本项目的 citation_support 对应引用文本是否支持答案。
- citation_ids_in_input 只检查引用 ID 是否出现在输入中，不能替代语义支持核查。
- 本项目保留原始响应和失败记录，方便复查单个案例；这与可复核评估的目标一致。

## 不可直接类比的地方
ALCE 使用其论文定义的数据集、任务与自动评估方法；本项目使用中文模拟文档、8 道正式题和人工语义核查。两者数据、任务和指标实现不同，不能直接比较分数，也没有复现 ALCE 的实验结果。

## 参考位置
- 论文摘要：ALCE 的评估目标与流畅度、正确性、引用质量三个维度。
- 公开仓库 README 的 Evaluation 部分：eval.py 的评估入口。
- 公开仓库 eval.py 的 compute_autoais 函数：检查句子与引用文档之间的支持关系。

## 状态
已完成公开资料阅读与设计观察；未安装、未运行、未复现 ALCE。
