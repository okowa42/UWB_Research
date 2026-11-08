"""E6(高所アンカー1台とタグ合格率)の判定。

依頼: 研究フォルダ Claude用参考資料/ClaudeCode実装依頼_高所アンカーとタグ合格率_261108.md(Cowork, 灯承認)。
判定基準は 2026-11-08 に、本実行とスモーク実行のどちらよりも前に commit して固定した。
結果を見てから基準を変えないこと。

======================================================================
条件(§2 と §5 回答で確定)
======================================================================
z_high = 1,500 / 5,000 / 10,000 / 20,000 / 40,000 mm、L_site = 100,000 mm、N_a=8、k=4、σ_r=100mm、
R_max=150,000mm、タグ格子 21×21×{0, 2,000}mm = 882 点、N_mc=100。共通乱数(全10条件で試行 i の乱数列が同一)。
- K 系列: 既知アンカー known_idx[3](座標 (+50 m, 0)、既定 2,900mm の台。E2_height と同じ台)を z_high に。
          他は既知 1,500×3、未知4台 1,500。K1500 は既知4台が同一平面になる(E2_height の基準と同じ)。
- U 系列: 未知アンカー index 7(座標 (−50 m, 0)。K の台と y 軸対称な辺の中点)を z_high に。
          他は E4/E2c H0 と同じ(既知 1,500×3+2,900、残りの未知3台 1,500)。展開誤差 σ_deploy=300 / σ_v=150。
- 注意(交絡): U 系列は常に既知 2,900mm の台を持つので、K と U の差は「高所アンカーが既知か未知か」だけでなく
  「2,900mm の既知台の有無」も含む。z_high が高いほどこの寄与は相対的に小さくなるはず。

======================================================================
§3 事前予測(依頼書の記述。すべて仮定)
======================================================================
- 高所アンカーから水平に約 50,000mm 離れたタグでは、高さ方向の距離感度 ≈ z_high / √(50,000² + z_high²)。
  σ_r=100mm で、その1台だけで決まる高さ誤差の目安は 10,000mm ≈510mm、20,000mm ≈270mm、40,000mm ≈160mm。
- 区画の隅(高所アンカーから水平に約 130,000mm)では、40,000mm でも感度 ≈0.29、誤差の目安 ≈340mm。
- よって C(200mm) が 95% に届くとしても 40,000mm 付近からで、隅の点が残るため 40,000mm でも届かない可能性がある。
  10,000mm 以下では届かない。
- アンカー側(鉛直 shape)は既存 E2_height の傾向(10,000mm で 564mm、40,000mm で 134mm)を K 系列が再現する。
(Claude Code 注: 高所アンカーは辺の中点にあるので、格子の最遠点までの水平距離は √(100²+50²) ≈ 111,800mm。
 依頼書の「約 130,000mm」「対角との距離 約 147,000mm」は角に置いた場合の値に近い。判定基準には影響しない。
 辺の中点・z_high=40,000mm・タグ z=0 での最遠点との距離は ≈118,700mm で、R_max 内。)

======================================================================
§3 判定基準(依頼書の記述)
======================================================================
主判定: 各系列・各水準の C(200mm)〔定義(b)、推定アンカー、CSV 列 `coverage`〕。試行の復元抽出 2,000 回で
    中央値の 95% 区間(パーセンタイル)を出し、
    - 区間の下限 ≥ 95%        → 「合格」
    - 区間が 95% をまたぐ     → 「境界」
    - 区間の上限 < 95%        → 「不合格」
必要高さ = 「合格」となる最も低い水準。全水準で合格しなければ「40,000mm でも不足」と書く。
副判定: 同じ判定を真アンカー版 C(200mm)(列 `coverage_trueanchor`)でも行う。
K と U の差: 同じ z_high での C(200mm) の中央値の差(K − U)を、対応ありブートストラップ(同じ試行番号の組を
    両系列に適用)で 95% 区間つきで報告する。

======================================================================
S0 事前確認(Claude Code 追加。判定の前提の検査。不一致なら判定前に原因を調べる。基準は変えない)
======================================================================
S0a: U1500 は E2c H0 と同一条件・同一乱数列なので、results/e4_area.csv の L=100,000 行と、共通列(compute_time_s・
     condition_id・height_pattern・ラベル列を除く)が全行一致するはず。
S0b: K1500 は e2_height_gap.csv の 1,500mm 水準(条件番号0、タグ測位 OFF)と同じ配置・測距の乱数列なので、
     アンカー側の列(rmse_anchor_*・rigidity_*・converged・iterations・rms_residual_mm)が全行一致するはず。

======================================================================
§5 確認事項3 の記録方法
======================================================================
剛性: 列 `rigidity_ok`(既存。毎試行)。不合格件数を水準ごとに数える。
一意性: 多スタート検査(experiments.E6_UNIQUENESS: 12 初期値、うち半数は自由アンカーを既知平均面で鏡映した種、
    摂動 500mm)。最良残差から 10mm 以内の相異なる解(回転のみ Procrustes で 10mm 以上離れた解)の数を
    `uniq_n_distinct` とし、2 以上の試行を「離散不定性あり」と数える。10mm は σ_r=100mm・28 辺・rms 残差 ≈70mm で
    残差二乗和の差 Δχ² ≈ 4 に相当する。あわせて `uniq_main_gap_mm`(通常の推定の残差 − 最良残差)> 10mm の
    試行を「通常の推定が別の局所解に落ちた」と数える。
    予測(Claude Code): K1500 は既知4台が同一平面なので、その面についての鏡映解が厳密に同じ距離を与え、ほぼ全試行で
    `uniq_n_distinct` ≥ 2 になる。それ以外の条件では既知が非共面なので、離散不定性は少ない。

======================================================================
Claude Code の追加予測(依頼書の判定は変えない。考察用)
======================================================================
L1 線形化予測(本スクリプトの `--predict`。シミュレーションは回さず、意図配置(誤差なし)の真アンカー幾何で、
   各評価点の測位誤差共分散 σ_r²(HᵀH)⁻¹ から P(3D 誤差 ≤ 200mm) を求め、882 点で平均した値)。
   E4 では真アンカーのタグ誤差が線形理論どおり L に比例した(傾き 0.995)ので、真アンカー版の目安になる。
   ただし非線形(発散・局所解)を含まないので、実際の値はこれより低いと予測する。予測値は下の表(commit 前に計算)。
L2 推定アンカー版は、高所アンカーが既知の K 系列では真アンカー版に近づくが、未知の U 系列では高所アンカー自身の
   推定誤差(特に水平。高い台は水平位置が距離に効きにくい)が残り、K より低くなると予測する。

線形化予測の表(--predict の出力をここに転記):
    系列  z_high[mm]  鉛直σ 中央値/最大[mm]  C(100)  C(200)  C(500)   (線形化・真アンカー・意図配置)
    K        1500       1303 / 4083         4.6%   12.1%   28.4%
    K        5000        986 / 2389         6.7%   17.6%   40.4%
    K       10000        640 / 1280        10.8%   28.1%   59.9%
    K       20000        347 / 644         17.9%   45.2%   82.9%
    K       40000        196 / 331         27.5%   66.2%   97.1%
    U        1500       1150 / 3991         5.1%   13.4%   31.3%
    U        5000        835 / 2317         7.3%   19.1%   43.6%
    U       10000        582 / 1296        11.3%   29.4%   62.4%
    U       20000        339 / 651         18.3%   46.2%   84.2%
    U       40000        193 / 333         27.8%   66.8%   97.3%
   ⇒ 線形化でも 40,000mm で C(200mm) ≈ 66% にとどまり、両系列・全水準で「不合格」と予測する(C(500mm) は 40,000mm で ≈97%)。
     鉛直 σ の中央値は依頼書の手計算(40,000mm で ≈160mm)とほぼ同じ ≈195mm だが、合否は 3D 誤差(水平 + 鉛直)で
     数えるため、鉛直 σ が 200mm 前後では 1 点あたりの P(≤200mm) が 7 割程度にしかならない。
   ⇒ 1,500mm の線形化値(K 12%, U 13%)は、E4 の真アンカー実測(L=100 m で 2.4%)より大きい。低い z_high では
     非線形の影響が大きく、線形化は楽観側に外れると予測する(z_high が高いほど線形化に近づく)。

例:
    python scripts/analyze_e6.py --predict     # 線形化予測のみ(シミュレーション結果を読まない)
    python scripts/analyze_e6.py --figdir <出力先>
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_PROJ = _HERE.parent
_ROOT = _PROJ.parent
for _p in (str(_PROJ), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from selfcal.deployment import intended_layout             # noqa: E402
from selfcal.experiments import HIGH_Z_SWEEP, build_conditions  # noqa: E402
from selfcal.io.config_loader import load_config           # noqa: E402
from selfcal.tag_positioning import build_tag_grid         # noqa: E402

TARGET = 0.95
N_BOOT = 2000
BOOT_SEED = 0
UNIQ_TOL_MM = 10.0
SERIES = ("K", "U")
S0A_SKIP = {"compute_time_s", "condition_id", "height_pattern", "e6_series", "z_high_mm"}
S0B_COLS = ["rmse_anchor_abs_mm", "rmse_anchor_abs_h_mm", "rmse_anchor_abs_v_mm",
            "rmse_anchor_shape_mm", "rmse_anchor_shape_h_mm", "rmse_anchor_shape_v_mm",
            "converged", "rigidity_ok", "iterations", "rigidity_min_singular",
            "rigidity_cond", "rms_residual_mm"]
# E2_height(7月版 results/e2_height.csv)のアンカー鉛直 shape 中央値(依頼書 §3 の参照値)
E2_HEIGHT_REF = {10000.0: 564.0, 40000.0: 134.0}

COL = {"K": "#2a78d6", "U": "#eb6834"}
INK, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"


# ---------------------------------------------------------------- 線形化予測
def _p_within(cov: np.ndarray, eps: float, z: np.ndarray) -> float:
    """3D ガウス N(0, cov) で ||e|| ≤ eps の確率(固定標本 z による MC)。"""
    w, v = np.linalg.eigh(cov)
    e = (z * np.sqrt(np.clip(w, 0, None))) @ v.T
    return float(np.mean(np.einsum("ij,ij->i", e, e) <= eps ** 2))


def linear_prediction(eps_list=(100.0, 200.0, 500.0)) -> list[dict]:
    base = load_config()
    sigma_r = float(base["ranging"]["sigma_r_mm"])
    z = np.random.default_rng(12345).standard_normal((20000, 3))
    out = []
    for cfg, cid in build_conditions("E6", base):
        anchors, _ = intended_layout(cfg)
        grid = build_tag_grid(cfg)
        pv, sz = {e: [] for e in eps_list}, []
        for tag in grid:
            d = anchors - tag
            H = d / np.linalg.norm(d, axis=1, keepdims=True)
            cov = sigma_r ** 2 * np.linalg.inv(H.T @ H)
            sz.append(np.sqrt(cov[2, 2]))
            for e in eps_list:
                pv[e].append(_p_within(cov, e, z))
        lab = cfg["montecarlo"]["record_labels"]
        row = {"series": lab["e6_series"], "z_high_mm": lab["z_high_mm"],
               "sigma_z_median_mm": float(np.median(sz)), "sigma_z_max_mm": float(np.max(sz))}
        for e in eps_list:
            row[f"C{int(e)}_pred"] = float(np.mean(pv[e]))
        out.append(row)
    return out


def format_prediction(rows: list[dict]) -> str:
    lines = ["    系列  z_high[mm]  鉛直σ 中央値/最大[mm]  C(100)  C(200)  C(500)   (線形化・真アンカー・意図配置)"]
    for r in rows:
        lines.append(f"    {r['series']}   {r['z_high_mm']:>9.0f}   {r['sigma_z_median_mm']:>8.0f} / {r['sigma_z_max_mm']:<8.0f}"
                     f"   {r['C100_pred']*100:5.1f}%  {r['C200_pred']*100:5.1f}%  {r['C500_pred']*100:5.1f}%")
    return "\n".join(lines)


# ---------------------------------------------------------------- 判定
def read_rows(path: pathlib.Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def matrix(rows: list[dict], series: str, col: str) -> tuple[list[float], np.ndarray]:
    """(水準, (水準, 試行) 配列)。試行番号で整列し、全水準で番号の集合が同じことを確かめる。"""
    mats, ids0 = [], None
    for z in HIGH_Z_SWEEP:
        sub = sorted([r for r in rows if r["e6_series"] == series and float(r["z_high_mm"]) == z],
                     key=lambda r: int(r["trial_id"]))
        ids = [int(r["trial_id"]) for r in sub]
        ids0 = ids if ids0 is None else ids0
        assert ids == ids0 and ids, "水準・系列間で試行番号の集合が違う"
        mats.append([float(r[col]) for r in sub])
    return list(HIGH_Z_SWEEP), np.asarray(mats)


def ci(a) -> list[float]:
    return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]


def verdict(lo: float, hi: float) -> str:
    if lo >= TARGET:
        return "合格"
    if hi < TARGET:
        return "不合格"
    return "境界"


def judge(rows: list[dict], col: str, B: np.ndarray) -> dict:
    out = {}
    for s in SERIES:
        levels, X = matrix(rows, s, col)
        res = {}
        for i, z in enumerate(levels):
            bm = np.median(X[i][B], axis=1)
            lo, hi = ci(bm)
            res[f"{z:.0f}"] = {"median": float(np.median(X[i])), "ci95": [lo, hi], "verdict": verdict(lo, hi)}
        passed = [z for z in levels if res[f"{z:.0f}"]["verdict"] == "合格"]
        res["required_height_mm"] = min(passed) if passed else None
        res["required_height_text"] = (f"{min(passed):.0f} mm" if passed else "40,000 mm でも不足")
        out[s] = res
    return out


def k_minus_u(rows: list[dict], col: str, B: np.ndarray) -> dict:
    _, K = matrix(rows, "K", col)
    _, U = matrix(rows, "U", col)
    out = {}
    for i, z in enumerate(HIGH_Z_SWEEP):
        d = float(np.median(K[i]) - np.median(U[i]))
        bd = np.median(K[i][B], axis=1) - np.median(U[i][B], axis=1)
        out[f"{z:.0f}"] = {"diff": d, "ci95": ci(bd)}
    return out


def level_stats(rows: list[dict], col: str, B: np.ndarray) -> dict:
    out = {}
    for s in SERIES:
        levels, X = matrix(rows, s, col)
        out[s] = {f"{z:.0f}": {"median": float(np.median(X[i])),
                               "ci95": ci(np.median(X[i][B], axis=1))} for i, z in enumerate(levels)}
    return out


def counts(rows: list[dict]) -> dict:
    out = {}
    for s in SERIES:
        for z in HIGH_Z_SWEEP:
            sub = [r for r in rows if r["e6_series"] == s and float(r["z_high_mm"]) == z]
            f = lambda c: np.array([float(r[c]) for r in sub])
            out[f"{s}{z:.0f}"] = {
                "n": len(sub),
                "rigidity_fail": int(np.sum(f("rigidity_ok") == 0)),
                "not_converged": int(np.sum(f("converged") == 0)),
                "uniq_multi": int(np.sum(f("uniq_n_distinct") >= 2)),
                "main_stuck_local": int(np.sum(f("uniq_main_gap_mm") > UNIQ_TOL_MM)),
                "uniq_no_converged_start": int(np.sum(f("uniq_n_converged") == 0)),
            }
    return out


def s0(rows: list[dict], res: pathlib.Path) -> dict:
    out = {}
    e4 = sorted([r for r in read_rows(res / "e4_area.csv") if float(r["area_mm"]) == 100000.0],
                key=lambda r: int(r["trial_id"]))
    u = sorted([r for r in rows if r["height_pattern"] == "U1500"], key=lambda r: int(r["trial_id"]))
    cols = [c for c in e4[0] if c in u[0] and c not in S0A_SKIP]
    bad = [(int(a["trial_id"]), c) for a, b in zip(u, e4) for c in cols if a[c] != b[c]]
    out["S0a_U1500_vs_e4_L100000"] = {"rows": [len(u), len(e4)], "n_cols": len(cols),
                                       "all_equal": not bad and len(u) == len(e4), "mismatch_first10": bad[:10]}
    g = sorted([r for r in read_rows(res / "e2_height_gap.csv") if float(r["known_z_max_mm"]) == 1500.0],
               key=lambda r: int(r["trial_id"]))
    k = sorted([r for r in rows if r["height_pattern"] == "K1500"], key=lambda r: int(r["trial_id"]))
    bad = [(int(a["trial_id"]), c) for a, b in zip(k, g) for c in S0B_COLS if a[c] != b[c]]
    out["S0b_K1500_vs_e2_height_gap_1500"] = {"rows": [len(k), len(g)], "all_equal": not bad and len(k) == len(g),
                                               "mismatch_first10": bad[:10]}
    return out


# ---------------------------------------------------------------- 図
def _setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker  # noqa: F401
    plt.rcParams["font.family"] = ["Yu Gothic", "Meiryo", "MS Gothic", "sans-serif"]
    return matplotlib, plt


def _style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=INK)
    ax.grid(True, which="major", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _xaxis(ax, matplotlib):
    zs = np.array(HIGH_Z_SWEEP) / 1000
    ax.set_xscale("log")
    ax.set_xticks(zs)
    ax.set_xticklabels([f"{z:g}" for z in zs])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("高所アンカーの高さ z_high [m]", color=INK)


def fig_coverage(summary: dict, path: pathlib.Path) -> None:
    matplotlib, plt = _setup()
    fig, ax = plt.subplots(figsize=(7.2, 5.0), dpi=150)
    fig.patch.set_facecolor(SURF)
    ax.set_facecolor(SURF)
    _style(ax)
    zs = np.array(HIGH_Z_SWEEP)
    names = {"K": "K 既知アンカーを上げる", "U": "U 未知アンカーを上げる"}
    for s in SERIES:
        for key, ls, mk, tag in (("main_est", "-", "o", "推定アンカー"), ("sub_true", (0, (4, 3)), "s", "真アンカー")):
            d = summary[key][s]
            m = np.array([d[f"{z:.0f}"]["median"] for z in zs]) * 100
            lo = np.array([d[f"{z:.0f}"]["ci95"][0] for z in zs]) * 100
            hi = np.array([d[f"{z:.0f}"]["ci95"][1] for z in zs]) * 100
            ax.errorbar(zs / 1000, m, yerr=[m - lo, hi - m], color=COL[s], linestyle=ls, marker=mk,
                        markersize=8, linewidth=2, capsize=3, markeredgecolor=SURF, markeredgewidth=1.5,
                        label=f"{names[s]}({tag})")
    ax.axhline(TARGET * 100, color="#e34948", linewidth=1.2, linestyle=(0, (2, 2)))
    ax.text(zs[0] / 1000, TARGET * 100 + 1.5, "目標 95%", color=INK, fontsize=8)
    _xaxis(ax, matplotlib)
    ax.set_ylim(0, 105)
    ax.set_ylabel("C(200 mm) [%](定義(b)・ひげ: 95% 区間)", color=INK)
    ax.set_title("E6 高所アンカー1台の高さとタグ合格率(各100試行・共通乱数)", color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="center left")
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def fig_errors(summary: dict, path: pathlib.Path) -> None:
    matplotlib, plt = _setup()
    fig, ax = plt.subplots(figsize=(7.2, 5.0), dpi=150)
    fig.patch.set_facecolor(SURF)
    ax.set_facecolor(SURF)
    _style(ax)
    zs = np.array(HIGH_Z_SWEEP)
    for s in SERIES:
        for key, ls, mk, tag in (("anchor_shape_v", "-", "o", "アンカー鉛直 shape"),
                                 ("tag_v", (0, (4, 3)), "s", "タグ鉛直(推定アンカー)")):
            d = summary[key][s]
            m = np.array([d[f"{z:.0f}"]["median"] for z in zs])
            lo = np.array([d[f"{z:.0f}"]["ci95"][0] for z in zs])
            hi = np.array([d[f"{z:.0f}"]["ci95"][1] for z in zs])
            ax.errorbar(zs / 1000, m, yerr=[m - lo, hi - m], color=COL[s], linestyle=ls, marker=mk,
                        markersize=8, linewidth=2, capsize=3, markeredgecolor=SURF, markeredgewidth=1.5,
                        label=f"{s}: {tag}")
    ax.axhline(200, color=MUTED, linewidth=1, linestyle=(0, (2, 2)))
    ax.text(zs[0] / 1000, 215, "200 mm", color=MUTED, fontsize=8)
    _xaxis(ax, matplotlib)
    ax.set_yscale("log")
    ax.set_ylabel("鉛直 RMSE 中央値 [mm](ひげ: 95% 区間)", color=INK)
    ax.set_title("E6 高所アンカーの高さと鉛直誤差(K: 既知を上げる / U: 未知を上げる)", color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="E6 判定")
    ap.add_argument("--predict", action="store_true", help="線形化予測だけを出す(結果 CSV を読まない)")
    ap.add_argument("--results", default=str(_PROJ / "results"))
    ap.add_argument("--figdir", default=None)
    args = ap.parse_args(argv)
    if args.predict:
        print(format_prediction(linear_prediction()))
        return 0

    res = pathlib.Path(args.results)
    figdir = pathlib.Path(args.figdir) if args.figdir else res
    rows = read_rows(res / "e6_high_anchor.csv")
    n = len([r for r in rows if r["height_pattern"] == "K1500"])
    B = np.random.default_rng(BOOT_SEED).integers(0, n, size=(N_BOOT, n))
    summary = {
        "S0": s0(rows, res),
        "main_est": judge(rows, "coverage", B),
        "sub_true": judge(rows, "coverage_trueanchor", B),
        "K_minus_U_est": k_minus_u(rows, "coverage", B),
        "K_minus_U_true": k_minus_u(rows, "coverage_trueanchor", B),
        "C100_est": level_stats(rows, "coverage_100mm", B),
        "C500_est": level_stats(rows, "coverage_500mm", B),
        "C100_true": level_stats(rows, "coverage_trueanchor_100mm", B),
        "C500_true": level_stats(rows, "coverage_trueanchor_500mm", B),
        "anchor_shape_v": level_stats(rows, "rmse_anchor_shape_v_mm", B),
        "anchor_shape_h": level_stats(rows, "rmse_anchor_shape_h_mm", B),
        "tag_v": level_stats(rows, "rmse_tag_v_mm", B),
        "tag_h": level_stats(rows, "rmse_tag_h_mm", B),
        "tag_true_3d": level_stats(rows, "rmse_tag_trueanchor_mm", B),
        "vdop_true": level_stats(rows, "vdop_true", B),
        "vdop_est": level_stats(rows, "vdop_est", B),
        "counts": counts(rows),
        "e2_height_ref_anchor_shape_v": {f"{k:.0f}": v for k, v in E2_HEIGHT_REF.items()},
        "linear_prediction": linear_prediction(),
    }
    with open(res / "e6_summary.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    figdir.mkdir(parents=True, exist_ok=True)
    fig_coverage(summary, figdir / "e6_coverage.png")
    fig_errors(summary, figdir / "e6_vertical.png")
    print(json.dumps(summary["S0"], ensure_ascii=False))
    for key in ("main_est", "sub_true"):
        for s in SERIES:
            d = summary[key][s]
            print(key, s, d["required_height_text"],
                  " ".join(f"{z}:{v['median']*100:.1f}%[{v['ci95'][0]*100:.1f},{v['ci95'][1]*100:.1f}]{v['verdict']}"
                           for z, v in d.items() if isinstance(v, dict)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
