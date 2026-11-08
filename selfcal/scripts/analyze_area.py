"""E4(配置範囲の縮小)と E5(許容誤差の感度)の判定。

依頼: 研究フォルダ Claude用参考資料/ClaudeCode実装依頼_配置範囲と許容誤差_261108.md(Cowork, 灯承認)。
判定基準は 2026-11-08 に実験の本実行より前に commit して固定した。結果を見てから基準を変えないこと。

======================================================================
§3 事前予測(依頼書の記述。数値はすべて仮定)
======================================================================
理論(仮定): ∂d_ij/∂z_i = (z_i − z_j)/d_ij。鉛直誤差 ≈ σ_r × d / Δz に比例する。
水平を相似縮小し Δz を固定すると、鉛直誤差は L_site に比例する。

    L_site [mm]   アンカー鉛直 shape 中央値の予測   タグ鉛直の予測
    100,000       ≈1,100(基準)                   基準値
     50,000       ≈550                             基準の 1/2
     25,000       ≈280                             基準の 1/4
     12,500       ≈140                             基準の 1/8

- 水平誤差は σ_r 程度で L にほぼ依存しない。
- 12,500 mm では近似が崩れる、または σ_r 由来の下限に近づき比例から外れる可能性がある(予測の範囲外)。

======================================================================
§3 判定基準(依頼書の記述)
======================================================================
指標: rmse_anchor_shape_v_mm(アンカー鉛直 shape RMSE)。results/e4_area.csv。
主判定: 100,000 / 50,000 / 25,000 mm の3水準で log(鉛直 shape 中央値) を log(L_site) に
    最小二乗回帰した傾き。試行の再標本化(ブートストラップ、対応を保ったまま 2,000 回)で
    95% 区間(パーセンタイル)を出す。
    - 区間が 1 を含む     → 「鉛直誤差は配置範囲に比例する(高さ不足の比 Δz/d で説明できる)」
    - 区間が 1 を含まない → 「比だけでは説明できない」(傾きの値と区間を報告)
副判定: 各水準の比 median(L)/median(100,000) を対応ありブートストラップの 95% 区間つきで出し、
    予測 0.5 / 0.25 / 0.125 が区間に入るかを示す。
12,500 mm は主判定に含めない(外れたら「比例が成り立つ範囲の下端」の情報として扱う)。
1点の値で改善率を言い切らない。中央値と 95% 区間で報告する。

「対応を保つ」の実装: 試行番号 i の乱数列は全水準で同一(experiments.E4_RNG_CONDITION_ID)。
ブートストラップでは試行番号の集合を復元抽出し、同じ番号の組を全水準に適用する。

======================================================================
S0 事前確認(Claude Code 追加。判定の前提が崩れていないかの検査)
======================================================================
E4 の L=100,000mm は E2c H0 と同じ乱数列・同じ条件なので、results/e2c_extrap.csv の H0
(2026-09-15, 同じ Windows venv)と、共通列が compute_time_s を除いて全行一致するはず。
一致しなければ判定の前に原因を調べる(判定基準は変えない)。

======================================================================
E5 の定義(§5 確認事項1への回答として固定)
======================================================================
タグ誤差は 3D 誤差ノルム ||推定 − 真||(仕様書 §3「ε_thr: タグ 3D 誤差」)。評価点 M=882。
- 定義(b)(コードの既存実装・過去の数値すべて): 試行ごとに「誤差 ≤ ε の評価点の割合」を出し、
  試行の中央値を取る。E2c・中間発表の C(200mm)=4% はこちら。
- 定義(a)(仕様書 §4.6 表の書き方): 評価点ごとに試行の中央値誤差を出し、それが ≤ ε の点の割合。
E5 では両方を並べる。どちらを正とするかは灯/Cowork の判断事項(仕様書と実装の食い違い)。
加えて真アンカー版(同一ノイズ)の C(ε) も出し、自己校正の寄与とタグ側幾何の寄与を分ける。
95% 区間は試行の復元抽出 2,000 回(定義(a)は抽出した試行で点ごとの中央値を取り直す)。
E5 の対象: E4 の4水準(タグ z の2系列とも)と E2c H0〜H3(results/e5_e2c_rerun.csv)。
目標線は 95%(仕様書 §4.6, TBD-2 暫定)。

======================================================================
Claude Code の対立予測(依頼書の判定は変えない。考察用に事前に書き残す)
======================================================================
P1 傾きは 1 より小さい(0.5〜0.9 程度)と予測する。根拠: 未知4台と既知3台はいずれも意図高さ
   1,500mm で、実際の高さの差は σ_v=150mm の散らばりだけ。高さの差がほぼ 0 の組では
   ∂d/∂z ≈ 0 で一次の情報が無く、距離の二次の変化 δd ≈ Δz²/(2d) から高さが決まる。この領域では
   鉛直誤差 ∝ √(σ_r·d)(傾き 0.5)。既知 2,900mm との組だけが一次の情報(傾き 1)を持つので、
   全体はその間に来る。⇒ 主判定で「区間が 1 を含まない」が出ても、それは「配置範囲が要因でない」
   ことを意味しない。傾きの区間が 0 を含まず正なら「配置範囲は要因だが、比 Δz/d の一次則だけでは
   説明できない」と読む、という解釈を提案する(これは主判定の置き換えではない)。
P2 C(200mm)(定義(b))は全水準で 95% に届かないと予測する。真アンカー版でも届かない。
   根拠: E2c H0 の真アンカー版タグ VDOP 中央値は 11.6 で、タグ側の幾何だけで鉛直が σ_r の
   10 倍になる。VDOP も d/Δz に比例するなら 12,500mm で 1.5 前後まで下がるが、σ_r=100mm・
   1回測距では 3D 誤差の 95% 点が 200mm を超える。⇒ C(ε) は自己校正の良し悪しを分離できる
   指標ではなく、E4 で配置範囲を縮めても破綻判定は変わらない可能性が高い。
P3 定義(a) は 0% か 100% に寄る(点ごとの中央値誤差が ε より大きい点は丸ごと落ち、小さい点は丸ごと
   数えられる)。誤差の大半が ε を超える条件では (a) < (b)、大半が ε を下回る条件では (a) > (b)。
   どちらを採るかで「破綻」の判定が変わりうる。
   【修正の開示】当初は「(a) は (b) より大きい」と書いていたが、下記スモーク実行の図で (a) < (b) を
   見て誤りに気づき、commit 前に上記へ書き直した。

開示: 判定基準の commit 前に、動作確認として E4 を 3 試行だけ実行し値を見た
(L=100,000→12,500mm で鉛直 shape は試行ごとに 1,738→526 / 1,611→552 / 355→132mm)。
P1 の √ 則の議論はそれより前に立てていたが、予測の数値幅(0.5〜0.9)はスモーク値を見た後に書いた。
さらに本スクリプトの動作確認として 3 試行のデータで通し実行し、そのとき主判定の傾き(3試行で 0.50)
と E5 の図も見えてしまった。したがって P1〜P3 は「スモークを見た後の予測」として扱うこと。
依頼書の予測・判定基準(上の §3)はスモーク値と無関係に依頼書から転記したもの。

例:
    python scripts/analyze_area.py --figdir <出力先>
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent          # <repo>/selfcal/scripts
_PROJ = _HERE.parent                                      # <repo>/selfcal
_ROOT = _PROJ.parent
for _p in (str(_PROJ), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from selfcal.experiments import AREA_SWEEP                 # noqa: E402

METRIC = "rmse_anchor_shape_v_mm"
TAG_METRIC = "rmse_tag_v_mm"
MAIN_LEVELS = [100000.0, 50000.0, 25000.0]
BASE_L = 100000.0
PRED_RATIO = {50000.0: 0.5, 25000.0: 0.25, 12500.0: 0.125}
EPSILONS = [100.0, 200.0, 500.0]
TARGET = 0.95
N_BOOT = 2000
BOOT_SEED = 0
S0_SKIP = {"compute_time_s", "condition_id", "height_pattern", "unknown_z_std_mm"}

assert sorted(MAIN_LEVELS + [12500.0]) == sorted(AREA_SWEEP)

# 図の色(dataviz 参照パレット): L は順序のある4水準なので blue の ordinal ramp。
L_COLORS = {100000.0: "#0d366b", 50000.0: "#1c5cab", 25000.0: "#3987e5", 12500.0: "#86b6ef"}
SERIES = {"anchor": "#2a78d6", "tag": "#eb6834", "tag1000": "#1baf7a"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e1e0d9"


def read_rows(path: pathlib.Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def by_level(rows: list[dict], key: str, metric: str) -> tuple[list, np.ndarray]:
    """(水準リスト, (水準, 試行) 配列)。試行番号で整列し、全水準で番号の集合が同じことを確かめる。"""
    levels = sorted({float(r[key]) if key == "area_mm" else r[key] for r in rows},
                    key=lambda v: -v if isinstance(v, float) else v)
    mats, ids0 = [], None
    for lv in levels:
        sub = [r for r in rows if (float(r[key]) if key == "area_mm" else r[key]) == lv]
        sub.sort(key=lambda r: int(r["trial_id"]))
        ids = [int(r["trial_id"]) for r in sub]
        if ids0 is None:
            ids0 = ids
        assert ids == ids0, "水準間で試行番号の集合が違う(対応が取れない)"
        mats.append([float(r[metric]) for r in sub])
    return levels, np.asarray(mats)


def boot_idx(n: int) -> np.ndarray:
    return np.random.default_rng(BOOT_SEED).integers(0, n, size=(N_BOOT, n))


def ci(a: np.ndarray) -> list[float]:
    return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]


def slope_of(levels: list[float], med: np.ndarray) -> float:
    return float(np.polyfit(np.log(levels), np.log(med), 1)[0])


def scaling_analysis(rows: list[dict], metric: str) -> dict:
    levels, X = by_level(rows, "area_mm", metric)
    n = X.shape[1]
    B = boot_idx(n)
    med = np.median(X, axis=1)
    bmed = np.median(X[:, B], axis=2)               # (水準, N_BOOT)
    li = [levels.index(L) for L in MAIN_LEVELS]
    s = slope_of(MAIN_LEVELS, med[li])
    bs = np.array([slope_of(MAIN_LEVELS, bmed[li, b]) for b in range(N_BOOT)])
    s_ci = ci(bs)
    i0 = levels.index(BASE_L)
    out = {
        "metric": metric, "n_trials": n,
        "levels": {f"{L:.0f}": {"median": float(med[i]), "median_ci95": ci(bmed[i])}
                   for i, L in enumerate(levels)},
        "slope_main": s, "slope_main_ci95": s_ci,
        "slope_ci_contains_1": bool(s_ci[0] <= 1.0 <= s_ci[1]),
        "slope_ci_contains_0": bool(s_ci[0] <= 0.0 <= s_ci[1]),
        "ratios": {},
    }
    for L, pred in PRED_RATIO.items():
        i = levels.index(L)
        r_ci = ci(bmed[i] / bmed[i0])
        out["ratios"][f"{L:.0f}"] = {
            "ratio": float(med[i] / med[i0]), "ci95": r_ci, "pred": pred,
            "pred_in_ci": bool(r_ci[0] <= pred <= r_ci[1]),
        }
    # 参考: 12,500 を含む4水準の傾き(主判定ではない)
    out["slope_all4_ref"] = slope_of(levels, med)
    return out


def coverage_table(rows: list[dict], npz_path: pathlib.Path, dataset: str, label_key: str) -> list[dict]:
    z = np.load(npz_path)
    err, err_t = z["tag_err_mm"], z["tag_err_true_mm"]
    cids, tids = z["condition_id"], z["trial_id"]
    # npz と CSV の行対応を確かめ、定義(b)の再計算が CSV の coverage 列と一致することも確かめる。
    assert [int(r["condition_id"]) for r in rows] == cids.tolist()
    assert [int(r["trial_id"]) for r in rows] == tids.tolist()
    for col, eps in (("coverage_100mm", 100.0), ("coverage", 200.0), ("coverage_500mm", 500.0)):
        csv_v = np.array([float(r[col]) for r in rows])
        assert np.allclose(csv_v, np.mean(err <= eps, axis=1)), col
    out = []
    for cid in sorted(set(cids.tolist())):
        m = cids == cid
        label = rows[int(np.where(m)[0][0])][label_key]
        n = int(m.sum())
        B = boot_idx(n)
        for anchors, E in (("est", err[m]), ("true", err_t[m])):
            for eps in EPSILONS:
                per_trial = np.mean(E <= eps, axis=1)                 # 定義(b)の試行ごとの値
                b_val = float(np.median(per_trial))
                b_boot = np.median(per_trial[B], axis=1)
                a_val = float(np.mean(np.median(E, axis=0) <= eps))  # 定義(a)
                a_boot = np.array([np.mean(np.median(E[B[k]], axis=0) <= eps) for k in range(N_BOOT)])
                out.append({
                    "dataset": dataset, "condition": label, "anchors": anchors, "eps_mm": eps,
                    "C_b_median_trial": b_val, "C_b_ci_lo": ci(b_boot)[0], "C_b_ci_hi": ci(b_boot)[1],
                    "C_a_pointmedian": a_val, "C_a_ci_lo": ci(a_boot)[0], "C_a_ci_hi": ci(a_boot)[1],
                    "meets_95_b": b_val >= TARGET, "meets_95_a": a_val >= TARGET, "n_trials": n,
                })
    return out


def s0_check(e4_rows: list[dict], ref_rows: list[dict]) -> dict:
    a = sorted([r for r in e4_rows if float(r["area_mm"]) == BASE_L], key=lambda r: int(r["trial_id"]))
    b = sorted([r for r in ref_rows if r["height_pattern"] == "H0"], key=lambda r: int(r["trial_id"]))
    cols = [c for c in b[0] if c in a[0] and c not in S0_SKIP]
    bad = [(int(x["trial_id"]), c) for x, y in zip(a, b) for c in cols if x[c] != y[c]]
    return {"n_compared_rows": min(len(a), len(b)), "n_cols": len(cols),
            "all_equal": not bad and len(a) == len(b), "mismatches_first10": bad[:10]}


def _style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=INK)
    ax.grid(True, which="major", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fig_scaling(res_anchor: dict, res_tag: dict, res_tag1000: dict | None, path: pathlib.Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker  # noqa: F401
    plt.rcParams["font.family"] = ["Yu Gothic", "Meiryo", "MS Gothic", "sans-serif"]
    fig, ax = plt.subplots(figsize=(7.2, 5.0), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    _style(ax)
    series = [("アンカー鉛直 shape", res_anchor, SERIES["anchor"], "o"),
              ("タグ鉛直(タグ z={0,2000})", res_tag, SERIES["tag"], "s")]
    if res_tag1000 is not None:
        series.append(("タグ鉛直(タグ z={0,1000})", res_tag1000, SERIES["tag1000"], "^"))
    Ls = np.array(sorted(AREA_SWEEP))
    for name, res, col, mk in series:
        meds = np.array([res["levels"][f"{L:.0f}"]["median"] for L in Ls])
        lo = np.array([res["levels"][f"{L:.0f}"]["median_ci95"][0] for L in Ls])
        hi = np.array([res["levels"][f"{L:.0f}"]["median_ci95"][1] for L in Ls])
        ax.errorbar(Ls / 1000, meds, yerr=[meds - lo, hi - meds], color=col, marker=mk,
                    markersize=8, linewidth=2, capsize=3, markeredgecolor="#fcfcfb",
                    markeredgewidth=1.5,
                    label=f"{name}  傾き {res['slope_main']:.2f} "
                          f"[{res['slope_main_ci95'][0]:.2f}, {res['slope_main_ci95'][1]:.2f}]")
        base = res["levels"][f"{BASE_L:.0f}"]["median"]
        ax.plot(Ls / 1000, base * Ls / BASE_L, color=col, linestyle=(0, (4, 3)), linewidth=1.2, alpha=0.8)
    ax.plot([], [], color=MUTED, linestyle=(0, (4, 3)), linewidth=1.2, label="予測: 傾き 1(L に比例, 100 m 基準)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(Ls / 1000)
    ax.set_xticklabels([f"{L/1000:g}" for L in Ls])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("配置範囲 L_site [m]", color=INK)
    ax.set_ylabel("鉛直 RMSE 中央値 [mm](ひげ: 95% 区間)", color=INK)
    ax.set_title("E4 配置範囲の縮小と鉛直誤差(各水準100試行・共通乱数)", color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.text(0.01, 0.005, "傾きは 100/50/25 m の3水準の回帰(主判定)。12.5 m は主判定外。",
             color=MUTED, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def fig_coverage(cov_rows: list[dict], dataset: str, path: pathlib.Path, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["Yu Gothic", "Meiryo", "MS Gothic", "sans-serif"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), dpi=150, sharey=True)
    fig.patch.set_facecolor("#fcfcfb")
    rows = [r for r in cov_rows if r["dataset"] == dataset and r["anchors"] == "est"]
    conds = list(dict.fromkeys(r["condition"] for r in rows))
    w = 0.8 / len(conds)
    for ax, (defn, key, lo_k, hi_k) in zip(axes, [
            ("定義(b) 試行ごとの割合の中央値(既存実装)", "C_b_median_trial", "C_b_ci_lo", "C_b_ci_hi"),
            ("定義(a) 点ごとの中央値誤差 ≤ ε の割合(仕様書)", "C_a_pointmedian", "C_a_ci_lo", "C_a_ci_hi")]):
        ax.set_facecolor("#fcfcfb")
        _style(ax)
        ax.grid(False, axis="x")
        for j, c in enumerate(conds):
            vals = [next(r for r in rows if r["condition"] == c and r["eps_mm"] == e) for e in EPSILONS]
            x = np.arange(len(EPSILONS)) + (j - (len(conds) - 1) / 2) * w
            v = np.array([r[key] for r in vals]) * 100
            lo = np.array([r[lo_k] for r in vals]) * 100
            hi = np.array([r[hi_k] for r in vals]) * 100
            col = L_COLORS.get(float(c), None) if dataset.startswith("E4") else \
                ["#0d366b", "#1c5cab", "#3987e5", "#86b6ef"][j % 4]
            lab = f"L = {float(c)/1000:g} m" if dataset.startswith("E4") else str(c)
            ax.bar(x, v, width=w * 0.92, color=col, label=lab, edgecolor="#fcfcfb", linewidth=1)
            ax.errorbar(x, v, yerr=[v - lo, hi - v], fmt="none", ecolor=MUTED, elinewidth=1, capsize=2)
        ax.axhline(TARGET * 100, color="#e34948", linewidth=1.2, linestyle=(0, (4, 3)))
        ax.text(len(EPSILONS) - 0.5, TARGET * 100 + 1.5, "目標 95%", color=INK, fontsize=8, ha="right")
        ax.set_xticks(np.arange(len(EPSILONS)))
        ax.set_xticklabels([f"ε = {e:g} mm" for e in EPSILONS])
        ax.set_ylim(0, 105)
        ax.set_title(defn, color=INK, fontsize=9.5, loc="left")
    axes[0].set_ylabel("カバレッジ率 C(ε) [%](ひげ: 95% 区間)", color=INK)
    axes[0].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0.0, 0.88))
    fig.suptitle(title, color=INK, fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="E4/E5 判定")
    ap.add_argument("--results", default=str(_PROJ / "results"))
    ap.add_argument("--figdir", default=None, help="図の出力先(既定: results/)")
    args = ap.parse_args(argv)
    res = pathlib.Path(args.results)
    figdir = pathlib.Path(args.figdir) if args.figdir else res

    e4 = read_rows(res / "e4_area.csv")
    e4z = read_rows(res / "e4_area_tagz1000.csv")
    e5 = read_rows(res / "e5_e2c_rerun.csv")
    summary = {
        "S0_vs_e2c_extrap_H0": s0_check(e4, read_rows(res / "e2c_extrap.csv")),
        "E4_anchor_shape_v": scaling_analysis(e4, METRIC),
        "E4_anchor_shape_h": scaling_analysis(e4, "rmse_anchor_shape_h_mm"),
        "E4_tag_v_z2000": scaling_analysis(e4, TAG_METRIC),
        "E4_tag_v_z1000": scaling_analysis(e4z, TAG_METRIC),
        "E4_vdop_true_z2000": scaling_analysis(e4, "vdop_true"),
        "E4_anchor_shape_v_z1000_identical": by_level(e4, "area_mm", METRIC)[1].tolist()
            == by_level(e4z, "area_mm", METRIC)[1].tolist(),
    }
    for k in ("E4", "E4_tagz1000"):
        rows = e4 if k == "E4" else e4z
        summary[f"{k}_converged_rate"] = {
            f"{L:.0f}": float(np.mean([float(r["converged"]) for r in rows if float(r["area_mm"]) == L]))
            for L in AREA_SWEEP}
    cov = (coverage_table(e4, res / "e4_area.csv.point_err.npz", "E4_tagz2000", "area_mm")
           + coverage_table(e4z, res / "e4_area_tagz1000.csv.point_err.npz", "E4_tagz1000", "area_mm")
           + coverage_table(e5, res / "e5_e2c_rerun.csv.point_err.npz", "E2c_rerun", "height_pattern"))

    with open(res / "e4_area_summary.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(res / "e5_coverage.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cov[0]))
        w.writeheader()
        w.writerows(cov)

    figdir.mkdir(parents=True, exist_ok=True)
    fig_scaling(summary["E4_anchor_shape_v"], summary["E4_tag_v_z2000"], summary["E4_tag_v_z1000"],
                figdir / "e4_area_scaling.png")
    fig_coverage(cov, "E4_tagz2000", figdir / "e5_coverage_e4.png",
                 "E5 許容誤差 ε ごとのカバレッジ率(E4, タグ z={0,2000}, 推定アンカー)")
    fig_coverage(cov, "E2c_rerun", figdir / "e5_coverage_e2c.png",
                 "E5 許容誤差 ε ごとのカバレッジ率(E2c H0〜H3 取り直し, 推定アンカー)")

    a = summary["E4_anchor_shape_v"]
    print(json.dumps(summary["S0_vs_e2c_extrap_H0"], ensure_ascii=False))
    print(f"主判定 傾き {a['slope_main']:.3f} 95%CI {a['slope_main_ci95']} 1を含む={a['slope_ci_contains_1']}")
    for L, r in a["ratios"].items():
        print(f"  比 {L}: {r['ratio']:.3f} CI {r['ci95']} 予測 {r['pred']} 区間内={r['pred_in_ci']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
