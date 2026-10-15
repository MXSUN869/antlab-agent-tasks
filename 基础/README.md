# 基础题入口

先读`01_考核题目.md`，再读`02_阅读材料.md`和`data/使用与标注说明.md`。开发题D01–D04有公开答案；正式题T01–T08只有输入。

北京时间2026年10月16日23:59（UTC+8）截止。在该时间前把基础与一套进阶作品推送至GitHub，并在Q群公布的收集表登记仓库链接与最终commit SHA。简历与联系方式填表，不放公开仓库。

`starter`是Python 3.10+标准库前后端骨架。默认模型适配层使用HTTPS＋Bearer的Chat Completions格式；本地服务或其他协议可以替换`provider.py`，保留记录契约。先复制`config.example.json`为本地配置，密钥放环境变量，不提交密钥或私人Endpoint。

先实现`student.py`，运行`python starter/runner.py --case D01 --condition E --dry-run --config config.local.json`核查输入，再启动`python starter/server.py --config config.local.json`预览页面。真实调用需显式使用`--paid`或服务端`--allow-paid`，会使用自己的模型额度。

正式基线可运行`python starter/runner.py --split evaluation --condition all --limit 32 --paid --config config.local.json`；冻结改进后用`--condition R0 --variant improved --limit 8`运行配对任务。命令执行前检查模型费用、输入、配置和调用上限。结果默认保存在`runs/`，`export_runs.py`可导出索引。

完整题目、目录和声明以进阶/05_提交与报告格式.md为准。
