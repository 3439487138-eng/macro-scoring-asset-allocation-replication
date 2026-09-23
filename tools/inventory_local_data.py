#!/usr/bin/env python3
"""Create a non-sensitive inventory of local candidate data; never loads pickle."""
from __future__ import annotations
import argparse, csv
from datetime import datetime
from pathlib import Path
import pandas as pd

SUFFIXES={".csv",".xlsx",".xls",".parquet",".feather",".pkl",".pickle",".db",".sqlite",".sqlite3"}
SKIP={".venv","site-packages",".git","__pycache__",".pytest_cache","data/cache","data/processed"}

def alias(path: Path, roots: list[tuple[str,Path]]) -> tuple[str,str]:
    for label,root in roots:
        try: return f"{{{label}}}/{path.relative_to(root).as_posix()}",label
        except ValueError: pass
    return path.name,"OTHER"

def inspect(path: Path) -> tuple[str,str,str,str]:
    if path.suffix.lower() in {".pkl",".pickle",".db",".sqlite",".sqlite3"}: return "not_loaded","unknown","unknown","unsafe_or_database_not_opened"
    try:
        if path.suffix.lower()==".csv": frame=pd.read_csv(path,nrows=20000)
        else: frame=pd.read_excel(path,nrows=20000)
        fields="|".join(map(str,frame.columns))[:1000]
        date_col=next((c for c in frame if any(x in str(c).lower() for x in ("date","time","日期"))),None)
        if date_col is None: return fields,str(len(frame)),"unknown","unknown"
        dates=pd.to_datetime(frame[date_col],errors="coerce").dropna().sort_values()
        if dates.empty: return fields,str(len(frame)),"unknown","unknown"
        delta=dates.drop_duplicates().diff().dt.days.median()
        freq="daily" if delta<=7 else "monthly" if delta<=40 else "quarterly" if delta<=100 else "annual_or_sparse"
        return fields,str(len(frame)),freq,f"{dates.min().date()}..{dates.max().date()}"
    except Exception as exc: return "unreadable","unknown","unknown",type(exc).__name__

def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--quant-root",type=Path,required=True); parser.add_argument("--downloads",type=Path,required=True); parser.add_argument("--output",type=Path,default=Path("docs/local_data_inventory.csv")); args=parser.parse_args()
    project=Path(__file__).resolve().parents[1]; reference=project.parent/"32_宏观打分资产配置"
    roots=[("PROJECT",project),("REFERENCE",reference),("QUANT_ROOT",args.quant_root),("DOWNLOADS",args.downloads)]
    seen=set(); records=[]
    for scan_root in (args.quant_root,args.downloads):
        for path in scan_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUFFIXES: continue
            parts={p.lower() for p in path.parts}
            if any(token.lower() in parts or token.lower() in path.as_posix().lower() for token in SKIP): continue
            resolved=path.resolve()
            if resolved in seen: continue
            seen.add(resolved); shown,source=alias(resolved,roots); fields,rows,freq,coverage=inspect(resolved)
            origin={"PROJECT":"current_project_local_unconfirmed","REFERENCE":"teacher_reference_do_not_copy","DOWNLOADS":"downloads_unrelated_or_unconfirmed"}.get(source,"quant_archive_unconfirmed")
            records.append({"path":shown,"source":origin,"fields":fields,"records":rows,"frequency":freq,"coverage":coverage,"updated_at":datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),"formal_backtest":"no" if source!="PROJECT" else "review_required","public_commit":"no_unless_separately_licensed","bytes":path.stat().st_size})
    records.sort(key=lambda x:x["path"])
    output=project/args.output; output.parent.mkdir(exist_ok=True)
    with output.open("w",encoding="utf-8-sig",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=records[0].keys()); writer.writeheader(); writer.writerows(records)
    print(f"Inventoried {len(records)} unique local candidates without deserializing pickle.")
if __name__=="__main__": main()
