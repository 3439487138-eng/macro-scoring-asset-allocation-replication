# 可复现说明

- 正式命令：`python run_replication.py --config config/base.yml`。
- 生产入口只读取当前运行下载并校验的真实 Yahoo 调整价，不读取 legacy 文件或测试 fixture。
- `input_manifest.json` 保存每个输入的请求、覆盖期、行数和 SHA-256；原始缓存被 `.gitignore` 排除。
- 数据截止日固定为 2026-08-31，保证本地和 GitHub Actions 使用相同完整月份。
- `tools/validate_backtest.py` 独立复算时点、发布可用日、权重、持仓收益、成本、净值、回撤、有限值、benchmark 对齐和末期日期。
- GitHub Actions 只手动触发；完整运行成功后上传 Artifact 并显式提交批准的派生输出。

当前结果是公开数据实务适配，不是原专有数据库的严格收益复现。上游网络或 schema 变化会让运行明确失败，不会调用缓存旧结果或人工数据回退。
