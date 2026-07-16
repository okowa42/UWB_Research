"""実験ID指定でバッチ実行し long-format CSV を出力する(§7)。

例:
    python scripts/run_experiment.py --exp E1 --out results/e1.csv
    python scripts/run_experiment.py --exp E1 --n-mc 20   # 上書き

依存 import のためリポジトリルートと selfcal プロジェクトディレクトリを sys.path へ
追加してから selfcal を読む。
"""
from __future__ import annotations

import argparse
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent          # <repo>/selfcal/scripts
_PROJ = _HERE.parent                                      # <repo>/selfcal
_ROOT = _PROJ.parent                                      # <repo>
for _p in (str(_PROJ), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from selfcal.experiments import build_conditions          # noqa: E402
from selfcal.io.config_loader import load_config           # noqa: E402
from selfcal.io.exporters import write_long_csv            # noqa: E402
from selfcal.montecarlo import run_condition               # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="selfcal 実験バッチ実行")
    ap.add_argument("--exp", default="E1", help="実験ID(例: E1)")
    ap.add_argument("--config", default=None, help="config yaml パス")
    ap.add_argument("--out", default=None, help="出力 CSV パス")
    ap.add_argument("--n-mc", type=int, default=None, help="試行数の上書き")
    args = ap.parse_args(argv)

    overrides = {}
    if args.n_mc is not None:
        overrides = {"montecarlo": {"n_mc": args.n_mc}}
    base_cfg = load_config(args.config, overrides=overrides or None)

    conditions = build_conditions(args.exp, base_cfg)
    all_rows: list[dict] = []
    for cfg, cid in conditions:
        rows = run_condition(cfg, condition_id=cid)
        all_rows.extend(rows)
        print(f"[{args.exp}] condition {cid}: {len(rows)} trials")

    out = args.out or f"results/{args.exp.lower()}.csv"
    path = write_long_csv(all_rows, out)
    print(f"wrote {len(all_rows)} rows -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
