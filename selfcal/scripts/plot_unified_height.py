"""統合図: 全アンカー高さの std を共通軸に、単一台昇降と複数台分散の鉛直 shape RMSE 中央値を重ねる。

2026-09-12 に一時スクリプトで作った e2c_unified_height.png を再現できるようリポジトリへ移した。
移す際に次を訂正した(2026-09-15):
- 実現可能域の網掛けは根拠のない 0〜1,800mm だった。400〜2,900mm 定義(2026-09-15 確定)での
  std 上限を config から計算して描く(既知4台固定、未知台を端点に置いた最大値)。
- 追補⑤(e2_height_gap.csv)と H5(e2c_extrap.csv)は別系列で描く。実行ごとに個別試行値が
  変わるため、7月版の曲線と混ぜて1本の線にはしない。
std=0 の条件(1.5m 水準)は対数軸に載らないため描かれない。数値は標準出力の表で確認する。

例:
    python scripts/plot_unified_height.py --out results/e2c_unified_height.png
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import pathlib
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

_HERE = pathlib.Path(__file__).resolve().parent          # <repo>/selfcal/scripts
_PROJ = _HERE.parent                                      # <repo>/selfcal
_ROOT = _PROJ.parent                                      # <repo>
for _p in (str(_PROJ), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from selfcal.deployment import intended_layout             # noqa: E402
from selfcal.experiments import build_conditions           # noqa: E402
from selfcal.io.config_loader import load_config           # noqa: E402
from selfcal.rng import trial_generator                    # noqa: E402

METRIC = "rmse_anchor_shape_v_mm"
FEASIBLE_Z_MM = (400.0, 2900.0)   # 実現可能域: 着陸機構体 400〜2,900mm(2026-09-15 確定)
BLUE, ORANGE = "#1f4e9c", "#c1440e"

# (CSV, 実験ID, 凡例, 色, 塗り, 線種, 描くラベル(None=全条件), 注記するラベル)
SERIES = [
    ("e2_height.csv", "E2_height_diversity", "single anchor raised (2026-07 run)",
     BLUE, True, "-", None, {"5.0m", "10.0m", "40.0m"}),
    ("e2_height_gap.csv", "E2_height_gap", "single anchor raised, gap-fill run (2026-09-15)",
     BLUE, False, "--", None, {"6.0m", "7.0m", "8.0m", "9.0m"}),
    ("e2c_patterns.csv", "E2c", "multi-anchor height spread H0-H4 (E2c)",
     ORANGE, True, "none", None, {"H0", "H1", "H2", "H3", "H4"}),
    ("e2c_extrap.csv", "E2c_extrap", "H5: multi-anchor, outside feasible (reference)",
     ORANGE, False, "none", {"H5"}, {"H5"}),
]


def base_config(csv_path: pathlib.Path) -> dict:
    """CSV に添えた meta.json の config を返す(無ければ config 既定)。"""
    meta = pathlib.Path(f"{csv_path}.meta.json")
    if meta.exists():
        cfg = json.loads(meta.read_text(encoding="utf-8")).get("config")
        if cfg:
            return cfg
    return load_config(None)


def condition_points(csv_path: pathlib.Path, exp_id: str) -> list[tuple[str, float, float]]:
    """条件ごとに (ラベル, 全アンカー z std の試行中央値, 指標の中央値) を返す。"""
    base = base_config(csv_path)
    seed = int(base["montecarlo"]["seed"])
    cfgs = {cid: cfg for cfg, cid in build_conditions(exp_id, base)}
    by: dict[int, list[dict]] = {}
    with open(csv_path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            by.setdefault(int(r["condition_id"]), []).append(r)
    pts = []
    for cid, rows in sorted(by.items()):
        cfg = cfgs[cid]
        stds = [
            intended_layout(cfg, trial_generator(seed, cid, int(r["trial_id"])))[0][:, 2].std()
            for r in rows
        ]
        label = (cfg["deployment"].get("height_pattern")
                 or f"{max(cfg['known']['known_z_mm']) / 1000:.1f}m")
        pts.append((label, float(np.median(stds)), float(np.median([float(r[METRIC]) for r in rows]))))
    return pts


def feasible_std_max_mm(cfg: dict) -> float:
    """既知アンカー固定のまま、未知アンカーを実現可能域内に置いたときの全アンカー z std の最大値。"""
    known_z = [float(z) for z in cfg["known"]["known_z_mm"]]
    n_unknown = int(cfg["deployment"]["n_anchors"]) - len(cfg["known"]["known_idx"])
    # std は z の凸関数なので、箱型領域での最大は端点の組合せで達する。
    return max(
        float(np.std(known_z + list(c)))
        for c in itertools.product(FEASIBLE_Z_MM, repeat=n_unknown)
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="高さ std 共通軸の統合図")
    ap.add_argument("--results", default=str(_PROJ / "results"), help="CSV のあるディレクトリ")
    ap.add_argument("--out", default=str(_PROJ / "results" / "e2c_unified_height.png"))
    args = ap.parse_args(argv)
    results = pathlib.Path(args.results)

    std_max = feasible_std_max_mm(load_config(None))
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    ax.axvspan(0, std_max, color="gray", alpha=0.12)
    ax.annotate(f"feasible range\n(heights 400-2,900 mm:\n std <= {std_max / 1000:.2f} m)",
                (120, 200), fontsize=8.5, color="dimgray")

    print(f"feasible std max = {std_max:.0f} mm")
    print(f"{'csv':>18} {'label':>6} {'all_z_std_mm':>13} {'median_mm':>10}")
    for name, exp_id, legend, color, filled, ls, keep, notes in SERIES:
        path = results / name
        if not path.exists():
            print(f"{name:>18} (無し・省略)")
            continue
        pts = [p for p in condition_points(path, exp_id) if keep is None or p[0] in keep]
        for label, s, v in pts:
            print(f"{name:>18} {label:>6} {s:13.0f} {v:10.0f}")
        ax.plot([p[1] for p in pts], [p[2] for p in pts], marker="s" if color == ORANGE else "o",
                linestyle=ls, color=color, markerfacecolor=color if filled else "white",
                label=legend, markersize=7, alpha=0.85)
        for label, s, v in pts:
            if label in notes:
                ax.annotate(label, (s, v), textcoords="offset points", xytext=(5, 6),
                            fontsize=8, color=color)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("std of intended anchor heights over all anchors [mm]")
    ax.set_ylabel("median anchor shape RMSE, vertical [mm]")
    ax.set_title("Vertical self-calibration vs. height spread (100 m x 100 m layout)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(args.out, dpi=130)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
