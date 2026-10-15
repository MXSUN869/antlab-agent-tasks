# 公开行为契约（实现可能不满足）

1. 查询范围由doc_ids与snapshot共同确定，未知组合返回invalid_scope。允许查询多个文档，只选它们该版本的材料。不能回退另一快照。
2. 排序按query空格分词与tags的交集数量降序，分数相同按id字典序；只保留正分证据，k为范围内最多返回数。tags是本题简化排序输入，不等同真实中文语义检索。scope内有匹配时不能因为scope外条目而丢失名额。
3. 引用有效性要求非空且每个引用都在本次实际检索证据中；缺失或越界须分别标识，不能把错误来源显示为当前版本。
4. 固定draft是可信度未知的合成响应，不能编辑它冒充修复。支持判断必须独立验证该answer的语义；只有ID有效不足以supported。未实现语义检查可not_checked，且页面要如实呈现。所有supported/contradicted/insufficient都需要相应依据与来源。
5. 缓存可复用等价输入结果，但不能污染改变资料/配置/响应后的请求。响应要有本次唯一request_id和实际来源；cache_hit只说明是否复用缓存。可以选择保留或关闭缓存，但须验证所选实现的行为。
6. 耗时是真实本地函数时间，只能报告offline_replay。源码中没有真实网络模型请求或服务器计算阶段。

server.py提供最小UI与API，初始只显示JSON。提升到题目要求的差异/来源/状态展示由候选人完成。浏览器数据通过textContent显示，不作为HTML执行。这个样机有意不包含生产账号/多用户/并发安全实现；相关推断不能当已测结论。

Engine接口：evaluate(request, corpus, draft)->dict；cache为实例状态。CLI按cases顺序执行，reset_before=true创建新实例。修复应保留接口或在README给出适配方式。可指定`--engine my_engine:Engine`，把模块放在challenge_b里。
