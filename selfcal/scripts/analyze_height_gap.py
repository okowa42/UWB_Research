"""追補⑤の判定: 仰角スイープ空白区間の低下開始水準と、H5 による総量則の外挿検証。

判定基準は 2026-09-15 に実験の実行前に固定した(Cowork 回答 260915 §3 で合意)。
結果を見てから基準を変えないこと(旧「約1.8 m」は根拠なく図に書いた値が本文に流れたもの)。

基準1 低下開始水準:
    e2_height_gap.csv の 5,000〜10,000mm の6水準を、それぞれ 1,500mm 水準と
    Mann-Whitney U 検定(両側)で比較し、6本に Holm 補正をかける。補正後 p<0.05 かつ
    中央値が 1,500mm 水準より小さい水準のうち、z が最も低いものを「低下開始水準」とする。
    水準の間のどこで下がり始めるかは特定しない(測定点の列として報告する)。
基準2 総量則の外挿検証:
    e2c_extrap.csv の H5(8台全体 std 1.780m)と、e2_height_gap.csv の 7,000mm 水準
    (std 1.819m, 最も近い測定点)の中央値差(H5 − 7000mm)のブートストラップ 95%CI を求める。
    CI が 0 を含めば「単一台昇降の曲線と区別できない」、含まなければ「曲線から外れる」。
    区別できないことは等しいことを意味しないため、CI の幅を併記する。

指標はすべて rmse_anchor_shape_v_mm(アンカー鉛直 shape RMSE)。std は各試行の意図配置を
seed から再構成した8台全体の高さ標準偏差(母標準偏差)の、条件内中央値。

例:
    python scripts/analyze_height_gap.py
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

import numpy as np
from scipy.stats import mannwhitneyu

_HERE = pathlib.Path(__file__).resolve().parent          # <repo>/selfcal/scripts
_PROJ = _HERE.parent                                      # <repo>/selfcal
_ROOT = _PROJ.parent                                      # <repo>
for _p in (str(_PROJ), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from selfcal.deployment import intended_layout             # noqa: E402
from selfcal.experiments import HEIGHT_GAP_SWEEP, build_conditions  # noqa: E402
from selfcal.io.config_loader import load_config           # noqa: E402
from selfcal.rng import trial_generator                    # noqa: E402

METRIC = "rmse_anchor_shape_v_mm"
ALPHA = 0.05
BASELINE_Z_MM = 1500.0
TESTED_Z_MM = [5000.0, 6000.0, 7000.0, 8000.0, 9000.0, 10000.0]
EXTRAP_LABEL = "H5"
EXTRAP_REF_Z_MM = 7000.0
N_BOOT = 10000
BOOT_SEED = 0

assert sorted(TESTED_Z_MM + [BASELINE_Z_MM]) == sorted(HEIGHT_GAP_SWEEP)


def base_config(csv_path: pathlib.Path) -> dict:
    """CSV に添えた meta.json の config を返す(無ければ config 既定)。"""
    meta = pathlib.Path(f"{csv_path}.meta.json")
    if meta.exists():
        cfg = json.loads(meta.read_text(encoding="utf-8")).get("config")
        if cfg:
            return cfg
    return load_config(None)


def read_by_condition(csv_path: pathlib.Path) -> dict[int, list[dict]]:
    by: dict[int, list[dict]] = {}
    with open(csv_path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            by.setdefault(int(r["condition_id"]), []).append(r)
    return by


def median_height_std_mm(cfg: dict, seed: int, cid: int, rows: list[dict]) -> float:
    stds = [
        intended_layout(cfg, trial_generator(seed, cid, int(r["trial_id"])))[0][:, 2].std()
        for r in rows
    ]
    return float(np.median(stds))


def holm(pvals: list[float]) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(np.argsort(p)):
        running = max(running, min(1.0, (p.size - rank) * p[i]))
        adj[i] = running
    return adj


def boot_medians(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    return np.median(x[rng.integers(0, x.size, (N_BOOT, x.size))], axis=1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="追補⑤ 判定(基準は docstring で事前固定)")
    ap.add_argument("--gap-csv", default=str(_PROJ / "results" / "e2_height_gap.csv"))
    ap.add_argument("--extrap-csv", default=str(_PROJ / "results" / "e2c_extrap.csv"))
    args = ap.parse_args(argv)
    rng = np.random.default_rng(BOOT_SEED)

    # --- 基準1: 単一台昇降の低下開始水準 ---
    gap_csv = pathlib.Path(args.gap_csv)
    gap_base = base_config(gap_csv)
    gap_seed = int(gap_base["montecarlo"]["seed"])
    gap_cfgs = {cid: cfg for cfg, cid in build_conditions("E2_height_gap", gap_base)}
    levels = {}
    for cid, rows in read_by_condition(gap_csv).items():
        z = float(rows[0]["known_z_max_mm"])
        levels[z] = (
            np.array([float(r[METRIC]) for r in rows]),
            median_height_std_mm(gap_cfgs[cid], gap_seed, cid, rows),
        )
    base_vals = levels[BASELINE_Z_MM][0]
    raw_p = [mannwhitneyu(levels[z][0], base_vals, alternative="two-sided").pvalue
             for z in TESTED_Z_MM]
    adj_p = dict(zip(TESTED_Z_MM, holm(raw_p)))
    raw_p = dict(zip(TESTED_Z_MM, raw_p))

    print(f"[基準1] {gap_csv.name}: 各水準 vs {BASELINE_Z_MM:.0f}mm "
          f"(Mann-Whitney 両側, Holm {len(TESTED_Z_MM)}本, alpha={ALPHA})")
    print(f"{'z_mm':>7} {'std_m':>6} {'n':>4} {'median':>7} {'95%CI(median)':>15} "
          f"{'p_raw':>9} {'p_holm':>9}  判定")
    onset = None
    for z in sorted(levels):
        vals, std = levels[z]
        lo, hi = np.percentile(boot_medians(vals, rng), [2.5, 97.5])
        if z == BASELINE_Z_MM:
            verdict, ps = "基準", f"{'-':>9} {'-':>9}"
        else:
            lower = adj_p[z] < ALPHA and np.median(vals) < np.median(base_vals)
            verdict = "低下" if lower else "差なし"
            ps = f"{raw_p[z]:9.3g} {adj_p[z]:9.3g}"
            if lower and onset is None:
                onset = z
        print(f"{z:7.0f} {std / 1000:6.3f} {vals.size:4d} {np.median(vals):7.0f} "
              f"[{lo:6.0f},{hi:6.0f}] {ps}  {verdict}")
    if onset is None:
        print("低下開始水準: 該当なし")
    else:
        print(f"低下開始水準: z={onset:.0f}mm (8台全体 std {levels[onset][1] / 1000:.3f} m)")

    # --- 基準2: H5 が単一台昇降の曲線に乗るか ---
    ext_csv = pathlib.Path(args.extrap_csv)
    if not ext_csv.exists():
        print(f"\n[基準2] {ext_csv.name} が無いため省略")
        return 0
    ext_base = base_config(ext_csv)
    ext_seed = int(ext_base["montecarlo"]["seed"])
    ext_cfgs = {cid: cfg for cfg, cid in build_conditions("E2c_extrap", ext_base)}
    ext = {}
    for cid, rows in read_by_condition(ext_csv).items():
        ext[rows[0]["height_pattern"]] = (
            np.array([float(r[METRIC]) for r in rows]),
            median_height_std_mm(ext_cfgs[cid], ext_seed, cid, rows),
        )
    h5, h5_std = ext[EXTRAP_LABEL]
    ref, ref_std = levels[EXTRAP_REF_Z_MM]
    diff = boot_medians(h5, rng) - boot_medians(ref, rng)
    lo, hi = np.percentile(diff, [2.5, 97.5])
    same = lo <= 0.0 <= hi
    print(f"\n[基準2] {ext_csv.name} {EXTRAP_LABEL} vs {gap_csv.name} z={EXTRAP_REF_Z_MM:.0f}mm")
    for label, (vals, std) in sorted(ext.items()):
        print(f"  {label}: std {std / 1000:.3f} m  n={vals.size}  median={np.median(vals):.0f}")
    print(f"  z={EXTRAP_REF_Z_MM:.0f}mm: std {ref_std / 1000:.3f} m  n={ref.size}  "
          f"median={np.median(ref):.0f}")
    print(f"  中央値差(H5 - z{EXTRAP_REF_Z_MM:.0f}) = {np.median(h5) - np.median(ref):.0f} mm, "
          f"95%CI [{lo:.0f}, {hi:.0f}] (幅 {hi - lo:.0f} mm), "
          f"Mann-Whitney p={mannwhitneyu(h5, ref, alternative='two-sided').pvalue:.3g}")
    print(f"  判定: {'単一台昇降の曲線と区別できない' if same else '曲線から外れる'}")
    if "H0" in ext:
        p0 = mannwhitneyu(h5, ext["H0"][0], alternative="two-sided").pvalue
        print(f"  参考: H5 vs 同一実行の H0  Mann-Whitney p={p0:.3g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
