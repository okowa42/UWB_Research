"""E2 の long-format CSV から感度曲線 / 破綻領域ヒートマップを描く(§7)。

スイープ軸を自動判定する:
  - 1軸のみ変動 → 感度曲線(中央値 + IQR 帯)
  - 2軸変動      → ヒートマップ(セル=中央値指標)

破綻は2種類を区別して重畳表示する(追補①):
  - 剛性破綻(×, 赤): rigidity_ok=False が過半 → 校正不能
  - 精度破綻(△, 橙): 中央値 coverage C(200mm) < 95% → 測位精度が要求水準に届かない
凡例に両定義を明記する。coverage 列が無い CSV(タグ測位 OFF)では剛性破綻のみ表示。

依存は matplotlib のみ(集計は標準ライブラリ)。ヘッドレス(Agg)で PNG を書き出す。

例:
    python scripts/make_figures.py --csv results/e2_sigma_r.csv        --out results/e2_sigma_r.png
    python scripts/make_figures.py --csv results/e2_grid.csv           --out results/e2_grid.png --metric coverage
    python scripts/make_figures.py --csv results/e2_grid_rigidity.csv  --out results/e2_grid_rigidity.png
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
    "known_z_max_mm": "elevated known-anchor z [mm]",
}

# 精度破綻のしきい値: 中央値 coverage C(200mm) がこの値を下回るセルを破綻とみなす。
COVERAGE_TARGET = 0.95


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


def _has_coverage(rows: list[dict]) -> bool:
    """coverage 列が有効値を持つか(タグ測位 ON の CSV か)。"""
    return any(
        r.get("coverage", "").strip() not in ("", "nan", "NaN")
        for r in rows
    )


def _median_coverage(rows: list[dict]) -> float:
    vals = [
        _to_float(r["coverage"]) for r in rows
        if r.get("coverage", "").strip() not in ("", "nan", "NaN")
    ]
    return statistics.median(vals) if vals else float("nan")


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

    has_cov = _has_coverage(rows)

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    im = ax.imshow(grid, origin="lower", aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(xs)), [f"{x:g}" for x in xs])
    ax.set_yticks(range(len(ys)), [f"{y:g}" for y in ys])
    ax.set_xlabel(AXIS_LABELS.get(ax_x, ax_x))
    ax.set_ylabel(AXIS_LABELS.get(ax_y, ax_y))
    ax.set_title(f"Breakdown map: median {metric}")

    # 2種の破綻を区別して重畳(追補①):
    #   剛性破綻(×赤): rigidity_ok=False が過半 → 校正不能
    #   精度破綻(△橙): 中央値 coverage < COVERAGE_TARGET → 精度が要求水準未満
    n_rig = n_prec = 0
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            crows = cell[(x, y)]
            if _rigidity_fail_frac(crows) > 0.5:
                ax.text(ix, iy, "×", ha="center", va="center",
                        color="red", fontsize=15, fontweight="bold")
                n_rig += 1
            elif has_cov and _median_coverage(crows) < COVERAGE_TARGET:
                ax.text(ix, iy, "△", ha="center", va="center",
                        color="orange", fontsize=14, fontweight="bold")
                n_prec += 1

    # 凡例(破綻定義を明記)。マーカーは proxy で示す。
    handles = [
        plt.Line2D([], [], marker="x", color="red", linestyle="None",
                   markersize=10, markeredgewidth=2.5,
                   label="rigidity breakdown (rigidity_ok=False)"),
    ]
    if has_cov:
        handles.append(
            plt.Line2D([], [], marker="^", color="orange", linestyle="None",
                       markersize=10,
                       label=f"precision breakdown (C(200mm) < {COVERAGE_TARGET:.0%})")
        )
    ax.legend(handles=handles, loc="upper center",
              bbox_to_anchor=(0.5, -0.13), ncol=1, fontsize=8, frameon=False)

    fig.colorbar(im, ax=ax, label=f"median {metric}")
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"  breakdown cells: rigidity={n_rig}, precision={n_prec}"
          f"{'' if has_cov else ' (coverage 列なし=剛性のみ判定)'}")


def plot_categorical_box(rows: list[dict], group: str, metric: str,
                         out: pathlib.Path) -> None:
    """カテゴリ列(例: height_pattern)で metric を箱ひげ表示(E2c)。

    群ごとの中央値 C(200mm) を各箱の下に注記する(タグ測位 ON の CSV のみ)。
    群の並びは初出順(H0,H1,... の宣言順)を保つ。
    """
    order: list[str] = []
    by_g: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        g = r[group]
        if g not in by_g:
            order.append(g)
        by_g[g].append(r)

    data = [[_to_float(r[metric]) for r in by_g[g]] for g in order]
    meds = [statistics.median(d) for d in data]
    has_cov = _has_coverage(rows)

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.boxplot(data, tick_labels=order, showmeans=True)
    ax.set_xlabel(group)
    ax.set_ylabel(metric)
    ax.set_title(f"{metric} by {group}")
    ax.grid(True, axis="y", alpha=0.3)

    # 各群の中央値と(あれば)C(200mm) を注記。
    ymax = max((max(d) for d in data if d), default=1.0)
    for i, g in enumerate(order, start=1):
        note = f"med={meds[i - 1]:.0f}"
        if has_cov:
            note += f"\nC200={_median_coverage(by_g[g]):.0%}"
        ax.annotate(note, (i, ymax), ha="center", va="bottom", fontsize=8,
                    color="#1f4e9c")
    ax.set_ylim(top=ymax * 1.18)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"  categorical box: {group} 群={len(order)}, metric={metric}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="E2 感度曲線 / 破綻領域ヒートマップ描画")
    ap.add_argument("--csv", required=True, help="入力 long-format CSV")
    ap.add_argument("--out", required=True, help="出力 PNG パス")
    ap.add_argument("--metric", default="rmse_anchor_shape_mm", help="集計対象の列")
    ap.add_argument("--group", default=None,
                    help="カテゴリ列で箱ひげ表示(例: height_pattern, E2c 用)")
    args = ap.parse_args(argv)

    rows = _read_rows(pathlib.Path(args.csv))
    if not rows:
        raise SystemExit(f"空の CSV: {args.csv}")
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # カテゴリ群指定(E2c)は数値スイープ軸判定より優先する。
    if args.group is not None:
        if args.group not in rows[0]:
            raise SystemExit(f"群列が CSV に無い: {args.group}")
        plot_categorical_box(rows, args.group, args.metric, out)
        print(f"箱ひげを書き出し: {out} (群={args.group}, metric={args.metric})")
        return 0

    axes = _varying_axes(rows)

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
