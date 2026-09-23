# 本地原始数据边界

原项目的 `China Rolled Return.csv`、`China Rolled Return2.csv`、`china-data.csv` 和 `data_indicator_review.csv` 来源、历史发布日期、修订状态与公开许可尚未确认，继续在本机保留并由 `.gitignore` 排除。生产入口不会读取它们。

当前 practical adaptation 在运行时从配置声明的 Yahoo chart endpoint 下载调整价；缓存位于 `data/processed/` 且不提交。仓库不包含随机、mock、demo 或 synthetic 生产回退。
