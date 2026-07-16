"""E2 の long-format CSV から感度曲線 / 破綻領域ヒートマップを描く(§7)。

スイープ軸を自動判定する:
  - 1軸のみ変動 → 感度曲線(中央値 + IQR 帯)
  - 2軸変動      → ヒートマップ(セル=中央値指標。剛性破綻セルは×で明示)

依存は matplotlib のみ(集計は標準ライブラリ)。ヘッドレス(Agg)で PNG を書き出す。

例:
    python scripts/make_figures.py --csv results/e2_sigma_r.csv --out results/e2_sigma_r.png
    python scripts/make_figures.py --csv results/e2_grid.csv    --out results/e2_grid.png
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # ヘッドレス描画
import matplotlib.pyplot as plt  # noqa: E402

# スイープ軸候補(ラベルは軸名として使う)。
AXIS_LABELS = {
    "sigma_r_mm": "σ_r [mm]",
    "sigma_v_mm": "σ_v [mm]",
    "sigma_deploy_mm": "σ_deploy [mm]",
    "n_anchors": "N_a",
    "r_max_mm": "R_max [mm]",
}


def _read_rows(path: pathlib.Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _to_float(x: str) -> float:
    return float(x)


def _varying_axes(rows: list[dict]) -> list[str]:
    """候補列のうち 2 水準以上を持つものをスイープ軸とみなす。"""
    axes = []
    for col in AXIS_LABELS:
        if col not in rows[0]:
            continue
        vals = {r[col] for r in rows}
        if len(vals) >= 2:
            axes.append(col)
    return axes


def _median(rows: list[dict], metric: str) -> float:
    return statistics.median(_to_float(r[metric]) for r in rows)


def _quartiles(vals: list[float]) -> tuple[float, float]:
    vals = sorted(vals)
    if len(vals) < 2:
        return vals[0], vals[0]
    q = statistics.quantiles(vals, n=4)
    return q[0], q[2]  # Q1, Q3


def _rigidity_fail_frac(rows: list[dict]) -> float:
    def failed(r: dict) -> bool:
        return str(r.get("rigidity_ok", "1")).strip() in ("0", "0.0", "False", "false")
    return sum(failed(r) for r in rows) / len(rows)


def plot_curve(rows: list[dict], axis: str, metric: str, out: pathlib.Path) -> None:
    by_x: dict[float, list[dict]] = defaultdict(list)
    for r in rows:
        by_x[_to_float(r[axis])].append(r)
    xs = sorted(by_x)
    med = [_median(by_x[x], metric) for x in xs]
    q1, q3 = zip(*(_quartiles([_to_float(r[metric]) for r in by_x[x]]) for x in xs))

    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    ax.fill_between(xs, q1, q3, alpha=0.2, color="#3b7dd8", label="IQR (Q1-Q3)")
    ax.plot(xs, med, "-o", color="#1f4e9c", label="median")
    ax.set_xlabel(AXIS_LABELS.get(axis, axis))
    ax.set_ylabel(f"{metric}")
    ax.set_title(f"Sensitivity: {metric} vs {AXIS_LABELS.get(axis, axis)}")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)


def plot_heatmap(rows: list[dict], ax_x: str, ax_y: str, metric: str,
                 out: pathlib.Path) -> None:
    cell: dict[tuple[float, float], list[dict]] = defaultdict(list)
    for r in rows:
        cell[(_to_float(r[ax_x]), _to_float(r[ax_y]))].append(r)
    xs = sorted({k[0] for k in cell})
    ys = sorted({k[1] for k in cell})
    grid = [[_median(cell[(x, y)], metric) for x in xs] for y in ys]

    fig, ax = plt.subplots(figsize=(6.5, 5.0))
    im = ax.imshow(grid, origin="lower", aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(xs)), [f"{x:g}" for x in xs])
    ax.set_yticks(range(len(ys)), [f"{y:g}" for y in ys])
    ax.set_xlabel(AXIS_LABELS.get(ax_x, ax_x))
    ax.set_ylabel(AXIS_LABELS.get(ax_y, ax_y))
    ax.set_title(f"Breakdown map: median {metric}  (x=rigidity fail)")
    # 剛性破綻セル(rigidity_ok=False が過半)を × で明示。
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            if _rigidity_fail_frac(cell[(x, y)]) > 0.5:
                ax.text(ix, iy, "×", ha="center", va="center",
                        color="red", fontsize=14, fontweight="bold")
    fig.colorbar(im, ax=ax, label=f"median {metric} [mm]")
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="E2 感度曲線 / 破綻領域ヒートマップ描画")
    ap.add_argument("--csv", required=True, help="入力 long-format CSV")
    ap.add_argument("--out", required=True, help="出力 PNG パス")
    ap.add_argument("--metric", default="rmse_anchor_shape_mm", help="集計対象の列")
    args = ap.parse_args(argv)

    rows = _read_rows(pathlib.Path(args.csv))
    if not rows:
        raise SystemExit(f"空の CSV: {args.csv}")
    axes = _varying_axes(rows)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if len(axes) == 0:
        raise SystemExit("スイープ軸が検出できない(全条件が同一)。E2 の CSV を渡すこと。")
    elif len(axes) == 1:
        plot_curve(rows, axes[0], args.metric, out)
        print(f"感度曲線を書き出し: {out} (軸={axes[0]})")
    else:
        # 2軸を超える場合は先頭2軸でヒートマップ(残りは無視)。
        plot_heatmap(rows, axes[0], axes[1], args.metric, out)
        print(f"ヒートマップを書き出し: {out} (軸={axes[0]}×{axes[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
