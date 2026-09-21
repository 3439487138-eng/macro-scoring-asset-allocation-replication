# 资产配置宏观打分策略

这是对既有研究 notebook 的工程化整理，不是对参考目录策略的复制，也不是投资建议。项目保留原宏观因子公式、方向权重、组合权重和统一一期滞后逻辑，同时把所有尚未解决的数据与口径问题变成明确、非零退出的安全失败。

## 当前状态

状态：**工程结构和严格校验已建立，真实策略收益尚未复现。**

当前真实运行会失败，这是预期行为，原因包括：

- 组合权重包含 `CREDIT`，收益资产只有 `SHORT_BOND`，两者未经确认不能等同；
- `CH_BOND` 输入被识别为收益率水平，不能冒充债券总收益；
- 原油和贷款只有年度级有效观测，不足以支持月度策略；
- 国内宏观数据存在重复 `release_date/indicator` 键；
- 国内汇率因子的内部滞后与组合统一滞后是否重复尚未确认；
- 四个核心输入的来源和公开许可尚未确认。

严格失败不会读取旧 CSV、PNG、Excel 或 notebook 输出，不会生成报告，也不会用缺失收益、随机数据或替代下载伪造成功。

## 策略调用链

```text
run_replication.py
  -> YAML configuration and strict validation
  -> real local source loading and release-date alignment
  -> domestic macro factors
  -> global macro factors
  -> walk-forward AR factor
  -> asset-specific factor aggregation and positions
  -> exactly one-period-lag backtest
  -> metrics and NAV
  -> current-run JSON and self-contained HTML report
```

生产入口不依赖 notebook 执行顺序、Jupyter 内核状态、当前工作目录或历史结果文件。

## 数据

用户需要自行放置以下四个真实文件，默认位置是项目根目录，也可通过 `.env` 中的 `MACRO_STRATEGY_DATA_DIR` 指向其他目录：

- `China Rolled Return.csv`
- `China Rolled Return2.csv`
- `china-data.csv`
- `data_indicator_review.csv`

当前本地原件没有删除，但被 `.gitignore` 排除。其哈希、字段、行数和覆盖期见 `docs/data_manifest.json`；所有许可状态均为 `unconfirmed_do_not_upload`。项目不提供自动下载、测试数据回退或虚构凭证。

## 安装

需要 Python 3.12。

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pip check
```

复制环境文件仅用于可选数据目录覆盖：

```powershell
Copy-Item .env.example .env
```

离线快照模式没有必需 API Secret。未来只有在项目所有者批准真实数据提供商后，才能增加同名的本地环境变量和 GitHub Actions Secret。

## 命令

```powershell
# 只校验工程结构；当前应通过
.venv\Scripts\python.exe run_replication.py validate-config --structure-only

# 严格配置校验；当前因已知策略歧义应以退出码 2 失败
.venv\Scripts\python.exe run_replication.py validate-config

# 审计本地真实输入；当前因重复键和频率不足应以退出码 2 失败
.venv\Scripts\python.exe run_replication.py audit-inputs

# 真实策略；只有所有严格阻断项解决后才会生成 outputs
.venv\Scripts\python.exe run_replication.py run

# 测试和上传候选扫描
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe tools/check_upload_candidates.py
```

测试中的微型人工数据只验证公式和失败路径，全部位于 `tests/fixtures`，不会进入生产入口、`outputs` 或收益报告。测试通过不等于真实策略已复现。

## 输出

只有真实数据校验、因子计算和回测全部成功后才会原子发布：

- `outputs/report.json`
- `outputs/report.html`
- `outputs/metrics.csv`
- `outputs/nav.csv`
- `outputs/positions.csv`
- `outputs/factor_signals.csv`
- `outputs/run_manifest.json`
- `outputs/equity_curve.png`

HTML 报告自包含图片，并区分本次运行、不可用指标和剩余保真差距。历史结果只登记为 `legacy_unverified`，生产代码禁止读取。

## GitHub Actions

工作流只有 `workflow_dispatch`。默认仅安装依赖、编译、结构校验、敏感信息扫描和 pytest。只有手动选择 `run_replication=true` 才会尝试真实策略；成功后才验证、上传并显式暂存批准的输出文件。工作流不使用 `git add --all`、定时任务、GitHub Pages、邮件或虚构 Secret。

## 许可证

许可证待项目所有者确认。当前没有擅自附加开源许可证；在许可明确前，不应公开发布许可不明的原始数据或历史二进制文件。

## 研究来源与限制

清理后的 notebook 仅用于追溯公式，不是生产入口。完整方法映射见 `docs/methodology.md`，复现与技能来源见 `docs/reproducibility.md`，明确上传白名单见 `docs/upload_candidates.txt`。

