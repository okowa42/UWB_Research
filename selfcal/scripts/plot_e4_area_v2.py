"""E4 両対数図の v2: 真アンカー版のタグ誤差(rmse_tag_trueanchor_mm)の系列を加える。

依頼 261108(高所アンカー)§4b。元の e4_area_scaling.png は推定アンカー版のタグ系列しかなく、
「タグ側は真アンカーでも範囲に比例」(Cowork 回答 261108 §2)と述べるには逆の印象を与えるため。
タグ高さは正式な {0, 2,000}mm(e4_area.csv)のみを描く。傾きは 100/50/25 m の3水準の回帰
(真アンカー版の傾きは結果を見た後の事後分析で、事前 commit した判定基準には含まれない)。

例:
    python scripts/plot_e4_area_v2.py --out <出力先>/e4_area_scaling_v2.png
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

from analyze_area import (BASE_L, INK, MUTED, SERIES, _style, read_rows,  # noqa: E402
                          scaling_analysis)
from selfcal.experiments import AREA_SWEEP                  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(_HERE.parent / "results" / "e4_area.csv"))
    ap.add_argument("--out", default=str(_HERE.parent / "results" / "e4_area_scaling_v2.png"))
    args = ap.parse_args(argv)
    rows = read_rows(pathlib.Path(args.csv))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker
    plt.rcParams["font.family"] = ["Yu Gothic", "Meiryo", "MS Gothic", "sans-serif"]

    series = [
        ("アンカー鉛直 shape", "rmse_anchor_shape_v_mm", SERIES["anchor"], "o", "-"),
        ("タグ鉛直(推定アンカー)", "rmse_tag_v_mm", SERIES["tag"], "s", "-"),
        ("タグ誤差 3D(真アンカー)", "rmse_tag_trueanchor_mm", SERIES["tag1000"], "^", "-"),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 5.0), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    _style(ax)
    Ls = np.array(sorted(AREA_SWEEP))
    for name, col, color, mk, ls in series:
        res = scaling_analysis(rows, col)
        meds = np.array([res["levels"][f"{L:.0f}"]["median"] for L in Ls])
        lo = np.array([res["levels"][f"{L:.0f}"]["median_ci95"][0] for L in Ls])
        hi = np.array([res["levels"][f"{L:.0f}"]["median_ci95"][1] for L in Ls])
        ax.errorbar(Ls / 1000, meds, yerr=[meds - lo, hi - meds], color=color, marker=mk, linestyle=ls,
                    markersize=8, linewidth=2, capsize=3, markeredgecolor="#fcfcfb", markeredgewidth=1.5,
                    label=f"{name}  傾き {res['slope_main']:.2f} "
                          f"[{res['slope_main_ci95'][0]:.2f}, {res['slope_main_ci95'][1]:.2f}]")
        base = res["levels"][f"{BASE_L:.0f}"]["median"]
        ax.plot(Ls / 1000, base * Ls / BASE_L, color=color, linestyle=(0, (4, 3)), linewidth=1.2, alpha=0.8)
    ax.plot([], [], color=MUTED, linestyle=(0, (4, 3)), linewidth=1.2, label="傾き 1(L に比例, 100 m 基準)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(Ls / 1000)
    ax.set_xticklabels([f"{L/1000:g}" for L in Ls])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("配置範囲 L_site [m]", color=INK)
    ax.set_ylabel("RMSE 中央値 [mm](ひげ: 95% 区間)", color=INK)
    ax.set_title("E4 配置範囲の縮小と誤差(各水準100試行・共通乱数, タグ z={0,2000})",
                 color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.text(0.01, 0.005, "傾きは 100/50/25 m の3水準の回帰。主判定はアンカー鉛直 shape のみ"
             "(タグ系列の傾きは事後分析)。", color=MUTED, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(args.out, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
