"""Self-contained current-run report and figures."""
from __future__ import annotations
import base64, json
from pathlib import Path
from typing import Any
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from jinja2 import BaseLoader, Environment, select_autoescape

HTML = """<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><title>{{ title }}</title><style>body{font-family:Arial,sans-serif;max-width:1100px;margin:2rem auto;color:#17202a}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd1d1;padding:.45rem}th{background:#eef2f3}img{max-width:100%}.note{border-left:4px solid #d68910;padding:.7rem;background:#fef9e7}code{background:#eee}</style></head><body><h1>{{ title }}</h1><p class=\"note\">{{ summary }}</p><p>状态：{{ run.status }}；模式：{{ run.mode }}；样本：{{ run.sample }}</p><h2>绩效</h2><table><tr><th>指标</th><th>值</th></tr>{% for k,v in metrics.items() %}<tr><td>{{ k }}</td><td>{{ v }}</td></tr>{% endfor %}</table><h2>资产映射</h2><table><tr><th>策略资产</th><th>代码</th><th>说明</th></tr>{% for a in assets %}<tr><td>{{ a.asset }}</td><td>{{ a.symbol }}</td><td>{{ a.role }}</td></tr>{% endfor %}</table><h2>图表</h2>{% for fig in figures %}<img src=\"data:image/png;base64,{{ fig }}\">{% endfor %}<h2>方法与限制</h2><ul>{% for x in limitations %}<li>{{ x }}</li>{% endfor %}</ul><h2>可复现性</h2><p>命令：<code>{{ run.command }}</code><br>配置：<code>{{ run.config }}</code><br>提交：<code>{{ run.commit_sha }}</code><br>生成时间：{{ run.generated_at }}</p><p>研究用途，不构成投资建议。</p></body></html>"""

def save_figures(nav: pd.DataFrame, allocations: pd.DataFrame, directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory/"nav_curve.png", directory/"drawdown_curve.png", directory/"allocation_weights.png"]
    fig, ax = plt.subplots(figsize=(10,5)); nav[["strategy_nav","benchmark_nav"]].plot(ax=ax); ax.set_title("NAV: strategy and benchmark"); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(paths[0],dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10,4)); nav[["strategy_drawdown","benchmark_drawdown"]].plot(ax=ax); ax.set_title("Drawdown"); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(paths[1],dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(11,5)); allocations.plot(ax=ax); ax.set_title("Executed allocation weights"); ax.axhline(0,color="black",linewidth=.6); fig.tight_layout(); fig.savefig(paths[2],dpi=150); plt.close(fig)
    return paths

def build_payload(metrics: dict[str,Any], run: dict[str,Any], assets: list[dict[str,str]], inputs: list[dict[str,Any]]) -> dict[str,Any]:
    return {"paper":{"title":"资产配置宏观打分策略（公开数据实务适配）","source":"existing project engineering extraction"},
            "run":run,"summary":"本报告由当前运行的真实市场数据重新计算；它是原策略思想的 practical adaptation，不是原始专有宏观数据库的严格复现。",
            "metrics":metrics,"assets":assets,"inputs":inputs,"limitations":[
                "CREDIT 依据原注释‘短融’使用 VCSH；没有与 SHORT_BOND 或现金合并。",
                "CBON、VCSH 等调整价是可交易代理，不等于原研究的唯一正确资产定义。",
                "宏观输入改用带时间戳的市场隐含代理，因此不存在统计数据修订值，但不能代表原始统计宏观因子。",
                "Yahoo 原始数据只在运行时获取且不随仓库再分发；上游可用性与条款可能变化。",
                "测试通过只说明工程约束成立，不等于原策略收益得到严格复现。"]}

def write_report(payload: dict[str,Any], figures: list[Path], json_path: Path, html_path: Path) -> None:
    json_path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    encoded=[base64.b64encode(p.read_bytes()).decode("ascii") for p in figures]
    env=Environment(loader=BaseLoader(),autoescape=select_autoescape(["html"]))
    html_path.write_text(env.from_string(HTML).render(title=payload["paper"]["title"],figures=encoded,**payload),encoding="utf-8")

def write_markdown(payload: dict[str,Any], path: Path) -> None:
    lines=["# 本次回测报告","",payload["summary"],"","## 绩效","","| 指标 | 值 |","|---|---:|"]
    lines += [f"| {k} | {v} |" for k,v in payload["metrics"].items()]
    lines += ["","## 复现限制",""]+[f"- {x}" for x in payload["limitations"]]
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")
