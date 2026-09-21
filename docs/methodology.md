# Methodology mapping

| Strategy component | Extracted implementation | Status / strict check |
|---|---|---|
| Monthly asset returns | Month-end level, `pct_change(fill_method=None)` | Oil frequency is unavailable; bond yield semantics invalid |
| Domestic economy | PMI levels plus 12-month loan/property changes, seasonal adjustment, trailing smoothing, expanding PCA, direction of change | Annual loan data causes strict failure; no implicit fill |
| Domestic currency | 1Y yield, reserve ratio and market operations; smoothed 12-month directions and six-month signal average | Duplicate macro keys and missing months fail |
| Domestic credit | Rolling 12-month loan sum, 12-month change, expanding PCA direction | PCA sign changes fail rather than being silently corrected |
| Domestic expectation | EWM trade expectation; level/delta regime mapping | Extracted from `single_assets.ipynb` unchanged |
| Domestic FX | Three-month percent change, internally shifted one month, then signed | Extracted unchanged; double-lag review remains unresolved |
| Domestic inflation | Seasonal/PCA factor change compared with lagged 36-month standard deviation | Missing source observations fail |
| Global economy | US/China PMI, Korea exports, copper/gold, trailing smoothing, expanding PCA direction | No full-sample result fallback |
| Global currency | Smoothed 1Y yield direction and Fed holdings rule | Persistent derived signal is an explicit state machine, not raw-data filling |
| Global inflation | Expanding HP endpoint and EWM z-score regimes | Endpoint sensitivity documented |
| Dollar cycle | Expanding HP endpoint and EWM z-score regimes | Endpoint sensitivity documented |
| Financial risk | OFR FSI EWM z-score regimes | Release dates validated |
| Autoregression | Walk-forward AutoReg(12), 36-month initial window, forecast sign | Model failure is fatal, not silently skipped |
| Asset positions | Original per-asset factor directions normalized by absolute weights | Missing active factors fail |
| Execution | Asset position shifted exactly one monthly period | Dedicated regression test |
| Portfolio | Original fixed capital weights | `CREDIT`/`SHORT_BOND` mismatch is fatal |
| Costs | Zero, matching the notebook's omission | Explicit assumption; no hidden cost model |
| Benchmark | None specified | Reported as `unavailable` |

No strategy logic or result from `../32_宏观打分资产配置` is imported. The reference directory was used only to understand organizational conventions.

