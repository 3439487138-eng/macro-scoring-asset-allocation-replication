# 本次回测报告

本报告由当前运行的真实市场数据重新计算；它是原策略思想的 practical adaptation，不是原始专有宏观数据库的严格复现。

## 绩效

| 指标 | 值 |
|---|---:|
| data_cutoff_date | 2026-08-31 |
| backtest_start | 2018-01-31 |
| backtest_end | 2026-08-31 |
| observations | 104 |
| cumulative_return | 0.11925149312866035 |
| annualized_return | 0.013084105853264916 |
| annualized_volatility | 0.03818443363233444 |
| sharpe_ratio | 0.34265549095863357 |
| max_drawdown | -0.07603989029158165 |
| monthly_win_rate | 0.5673076923076923 |
| rebalance_count | 104 |
| annualized_turnover | 2.99 |
| total_transaction_cost | 0.02591333333333333 |
| benchmark_cumulative_return | 0.9799513332411838 |
| benchmark_annualized_return | 0.08200524790699637 |
| excess_cumulative_return | -0.8606998401125234 |
| excess_annualized_return | -0.06892114205373145 |

## 复现限制

- CREDIT 依据原注释‘短融’使用 VCSH；没有与 SHORT_BOND 或现金合并。
- CBON、VCSH 等调整价是可交易代理，不等于原研究的唯一正确资产定义。
- 宏观输入改用带时间戳的市场隐含代理，因此不存在统计数据修订值，但不能代表原始统计宏观因子。
- Yahoo 原始数据只在运行时获取且不随仓库再分发；上游可用性与条款可能变化。
- 测试通过只说明工程约束成立，不等于原策略收益得到严格复现。
