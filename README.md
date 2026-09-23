# 资产配置宏观打分策略

这是从既有研究 notebook 提取出的、可独立运行的工程化项目。生产入口会在每次运行时下载真实市场数据、重算信号和回测并生成报告；不会读取历史 CSV、PNG、Excel 或 notebook 输出冒充本次结果。

> 当前状态：**公开数据 practical adaptation 已可复现运行**。由于原始专有宏观数据库、点时版本和资产定义没有完整授权说明，本项目不声称严格复现原模型的唯一收益路径，也不构成投资建议。

## 策略与调用链

```text
run_replication.py
  → 配置及资产键校验
  → Yahoo 调整价真实数据下载、SHA-256 manifest
  → 月末对齐及因果滚动去极值/标准化
  → 国内、全球、风险、美元与 AR 信号
  → 原方向权重汇总为资产仓位
  → 原组合权重 × 仓位
  → 信号后一期执行、显式 BIL 现金、10bp 换手成本
  → 同资产固定权重 benchmark
  → 指标、图表、JSON/HTML/Markdown 报告
```

原组合基准权重保持为：A 股 10%、中国债券 40%、美股 5%、黄金 30%、原油 5%、信用债 10%。资产信号方向权重保持在 `config/base.yml`。FX 单项不再内部滞后，所有资产仅在组合层统一滞后一期，避免双重滞后。

## 真实数据与资产定义

运行时从 Yahoo Finance chart endpoint 获取调整价，不提交上游原始快照；`outputs/input_manifest.json` 记录请求 URL、获取时间、行数、覆盖期、缓存路径和 SHA-256。

| 策略资产 | 代理 | 解释 |
|---|---|---|
| CH_EQUITY | ASHR | 沪深 300 A 股 ETF，作为原 CSI800 的实务代理 |
| CH_BOND | CBON | 中国债券 ETF 调整价；未把债券收益率水平当收益 |
| US_EQUITY | SPY | 标普 500 ETF |
| GOLD | GLD | 黄金 ETF |
| OIL | USO | 原油期货基金，提供真实月度可交易代理 |
| CREDIT | VCSH | 短久期投资级信用债 ETF，依据原 notebook “短融”注释 |
| CASH | BIL | 未配置风险预算的显式现金代理 |

`CREDIT` 与 `SHORT_BOND` 没有被强行等同：原材料的组合键是 `CREDIT`，而 `SHORT_BOND` 对应代码注释为“短融”，因此统一命名为信用债仓位。VCSH 是 practical adaptation，并非原模型唯一正确映射。benchmark 是相同六类风险资产的固定基准权重月度组合，用来隔离宏观择时影响。

宏观统计数据缺少可靠历史发布日期和未修订 vintages，因此生产版使用带交易时间戳的市场隐含代理（ASHR、CNY=X、VCSH/CBON、SPY、USO/GLD、HG=F/GC=F、TLT/BIL、DX-Y.NYB、^VIX）。它们只在月末收盘后形成信号并在下一交易月执行，不声称等同原始统计因子。完整公式见 `docs/backtest_methodology.md`。

## 安装与运行

需要 Python 3.12。

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe run_replication.py --config config/base.yml
.venv\Scripts\python.exe tools/validate_backtest.py
```

当前配置固定数据截止日为 2026-08-31，以确保本地与 Actions 得到相同月份范围。上游请求失败、数据陈旧、键不一致、重复日期、缺失收益或非有限结果都会返回非零退出码，且不会采用随机/演示/合成回退。

## 当前真实回测

当前提交内结果来自本次真实下载与重算，区间 2018-01-31 至 2026-08-31，共 104 个月。主要指标以 `outputs/performance_metrics.csv` 和自包含的 `outputs/report.html` 为准。测试 fixture 只存在于 `tests/fixtures`；测试通过不代表原模型严格复现成功。

生成文件包括绩效、月收益、净值、权重、宏观得分、调仓记录、输入 manifest、三张图和三种报告格式，均在 `outputs/`。

## GitHub Actions

工作流 `Macro allocation replication` 仅支持 `workflow_dispatch`。选择 `run_replication=true` 后会安装固定依赖、运行结构及敏感信息检查和 pytest、删除批准的旧输出、下载真实数据、执行正式入口、复算 12 项回测不变量、验证报告、上传完整 Artifact，并只显式提交批准的输出；不使用 `continue-on-error`、schedule、Pages、邮件、虚构 Secret 或 `git add --all`。

## 复现限制与许可

- Yahoo 调整价是总收益近似，可交易代理的管理费、跟踪误差与上市前历史都会影响结果。
- 市场隐含代理避免统计数据修订的前视问题，但改变了原统计宏观指标的经济含义，属于明确适配。
- ASHR 不是 CSI800，CBON/VCSH 也未被证明是原研究使用的指数。
- 上游数据使用与再分发受其条款约束；仓库不提交原始运行时缓存。
- 原始四个本地数据文件来源与公开许可仍未确认，保留在本地并由 `.gitignore` 排除。
- 项目许可证待所有者确认；未擅自添加开源许可证。

本机搜索、历史文件登记和上传白名单分别见 `docs/local_data_inventory.csv`、`docs/legacy_manifest.json` 和 `docs/upload_candidates.txt`。
