# 方法映射

生产实现与公式详见 [backtest_methodology.md](backtest_methodology.md)。本项目保留原 notebook 的资产方向权重、10/40/5/30/5/10 组合权重、AR(12) 扩展窗结构和统一一期滞后；统计宏观数据因来源、许可、发布日期和 vintage 均不能可靠确认，改为明确标记的市场隐含 `practical_adaptation`，没有复制老师参考项目的策略逻辑或结果。

关键适配包括：`CREDIT` 依据“短融”注释映射 VCSH，`CH_BOND` 使用 CBON 调整价，原油使用 USO，FX 内部滞后为 0 且组合层滞后为 1，benchmark 是同资产固定权重组合。所有偏离严格原模型之处都在 README 和本次报告中披露。
