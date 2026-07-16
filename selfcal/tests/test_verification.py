"""受け入れ基準 V-1〜V-8 の自動化 = E0。

Phase A: V-1,2,3,6,7,8(決定的テスト)。Phase B: V-4(統計的単調性)・V-5(整列不変式)。
乱数はすべて rng.trial_generator 経由(V-6)。
"""
from __future__ import annotations

import importlib.util
import pathlib
import statistics

import numpy as np

from selfcal import deployment, ranging
from selfcal.calibration import LMEstimator
from selfcal.geometry_bridge import dop_components
from selfcal.io.config_loader import load_config
from selfcal.io.exporters import write_long_csv
from selfcal.montecarlo import run_condition
from selfcal.rigidity import check_rigidity
from selfcal.rng import trial_generator

_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _run_calibration(cfg, seed, gauge=None, dof=None):
    gauge = gauge or cfg["calibration"]["gauge"]
    dof = dof or cfg["calibration"]["dof"]
    rng = trial_generator(seed, 0, 0)
    dep = deployment.build_deployment(cfg, rng)
    dist = ranging.measure_ranges(dep.true_xyz_mm, cfg, rng)
    known = cfg["known"]["known_idx"] if gauge == "known" else []
    res = LMEstimator().calibrate(dist, dep.intended_xyz_mm, known, gauge, dof, rng)
    return dep, dist, res


# --- V-1: 無雑音・展開誤差0・完全グラフ → 誤差 < 1e-6 mm ---
def test_v1_noiseless_identity():
    cfg = load_config(overrides={
        "deployment": {"sigma_deploy_mm": 0.0, "sigma_v_mm": 0.0},
        "ranging": {"sigma_r_mm": 0.0},
    })
    dep, _, res = _run_calibration(cfg, seed=1)
    err = np.linalg.norm(res.anchor_positions_mm - dep.true_xyz_mm, axis=1).max()
    assert err < 1e-6
    assert res.rigidity_ok


# --- V-2: 無雑音・展開誤差大・G1(k=4) → 機械精度で真値復元 ---
def test_v2_noiseless_recovery_from_large_deploy_error():
    cfg = load_config(overrides={
        "deployment": {"sigma_deploy_mm": 1000.0, "sigma_v_mm": 1000.0},
        "ranging": {"sigma_r_mm": 0.0},
    })
    dep, _, res = _run_calibration(cfg, seed=2, gauge="known")
    drift = np.linalg.norm(dep.intended_xyz_mm - dep.true_xyz_mm, axis=1).max()
    assert drift > 500.0  # 実際に大きくズレた初期値から出発している
    err = np.linalg.norm(res.anchor_positions_mm - dep.true_xyz_mm, axis=1).max()
    assert err < 1e-3
    assert res.converged and res.rigidity_ok


# --- V-3: 剛性不足(エッジ欠落) → 「校正不能」検出 ---
def test_v3_insufficient_rigidity_detected():
    # 非共面4点(四面体)。完全グラフK4は剛(rank=3N-6=6)。1エッジ欠落で非剛。
    xyz = np.array([
        [0.0, 0.0, 0.0],
        [1000.0, 0.0, 0.0],
        [0.0, 1000.0, 0.0],
        [200.0, 300.0, 1200.0],
    ])
    n = 4
    full = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(i + 1, n):
            full[i, j] = full[j, i] = np.linalg.norm(xyz[i] - xyz[j])
    ok_full = check_rigidity(xyz, full, "convention", dim=3)
    assert ok_full.rigidity_ok and ok_full.rank == ok_full.required_rank

    # 最長エッジ(2,3)を欠測にすると rank 不足 → 非剛
    dropped = full.copy()
    dropped[2, 3] = dropped[3, 2] = np.nan
    res = check_rigidity(xyz, dropped, "convention", dim=3)
    assert not res.rigidity_ok
    assert res.rank < res.required_rank


# --- V-6: 同一seed再実行 → CSV完全一致 ---
def test_v6_reproducible_csv(tmp_path):
    cfg = load_config(overrides={
        "montecarlo": {"n_mc": 3},
        # タググリッドを最小化して高速化(再現性の検証が目的)
        "tag_positioning": {"grid_span_mm": 10000.0, "grid_step_mm": 5000.0},
    })
    rows1 = run_condition(cfg, condition_id=0)
    rows2 = run_condition(cfg, condition_id=0)
    # compute_time_s は壁時計で本質的に非決定的 → 科学的出力の再現性検証から除外する。
    for rows in (rows1, rows2):
        for r in rows:
            r.pop("compute_time_s", None)
    p1 = write_long_csv(rows1, tmp_path / "a.csv")
    p2 = write_long_csv(rows2, tmp_path / "b.csv")
    assert p1.read_bytes() == p2.read_bytes()


# --- V-7: 真値配置PDOP = pdop/ 出力と一致(回帰) ---
def test_v7_pdop_matches_pdop_package():
    # pdop の geometry を独立ロードし、bridge 経由の値と一致することを確認
    geom_path = _ROOT / "pdop" / "simulation" / "geometry.py"
    spec = importlib.util.spec_from_file_location("pdop_geom_ref", geom_path)
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)

    anchors = np.array([
        [0.0, 0.0, 0.0], [1000.0, 0.0, 500.0],
        [0.0, 1000.0, 0.0], [1000.0, 1000.0, 800.0],
    ])
    tag = np.array([400.0, 600.0, 100.0])
    ref_pdop = ref.dilution_of_precision(anchors, tag)
    bridge_pdop, _, _ = dop_components(anchors, tag)
    assert np.isclose(bridge_pdop, ref_pdop, rtol=0, atol=1e-12)


# --- V-8: 共面配置を3D/2D両モードへ入力 ---
def test_v8_coplanar_3d_flagged_unsolvable():
    cfg = load_config(overrides={
        "known": {"known_z_mm": [1500.0, 1500.0, 1500.0, 1500.0]},
        "deployment": {"sigma_v_mm": 0.0},
        "ranging": {"sigma_r_mm": 0.0},
    })
    dep, dist, _ = _run_calibration(cfg, seed=8, gauge="known", dof=3)
    rig = check_rigidity(dep.true_xyz_mm, dist, "known",
                         cfg["known"]["known_idx"], dim=3)
    assert not rig.rigidity_ok           # 3D では校正不能を検出
    assert rig.rank < rig.required_rank


def test_v8_coplanar_2d_recovers_truth():
    cfg = load_config(overrides={
        "known": {"known_z_mm": [1500.0, 1500.0, 1500.0, 1500.0]},
        "deployment": {"sigma_v_mm": 0.0},
        "ranging": {"sigma_r_mm": 0.0},
    })
    dep, _, res = _run_calibration(cfg, seed=8, gauge="known", dof=2)
    xy_err = np.linalg.norm(
        res.anchor_positions_mm[:, :2] - dep.true_xyz_mm[:, :2], axis=1
    ).max()
    assert xy_err < 1e-3                 # 2D(z既知)なら σ_r=0 で真値復元
    assert res.rigidity_ok


# --- V-4: σ_r 増加で RMSE(N_mc=100 中央値)が単調増加 ---
def test_v4_rmse_monotonic_in_sigma_r():
    # 中央値の統計的単調性。タグ測位は本テストに無関係なので無効化して高速化。
    sigma_r_values = [30.0, 110.0, 190.0, 280.0]
    medians = []
    for sr in sigma_r_values:
        cfg = load_config(overrides={
            "montecarlo": {"n_mc": 100},
            "tag_positioning": {"enabled": False},
            "ranging": {"sigma_r_mm": sr},
        })
        rows = run_condition(cfg, condition_id=0)
        medians.append(statistics.median(r["rmse_anchor_shape_mm"] for r in rows))
    # σ_r=30→280 の広い範囲で隣接条件が明瞭に増加することを要求。
    assert all(medians[i] < medians[i + 1] for i in range(len(medians) - 1)), medians


# --- V-5: G2 Procrustes 整列後 RMSE_shape ≤ 整列前絶対 RMSE(全試行) ---
def test_v5_procrustes_shape_le_absolute():
    # G2(規約固定)は規約点の誤差で絶対座標系が大きく歪むが、形状誤差は Procrustes
    # 整列で吸収される。整列後 shape ≤ 整列前 abs が全試行で成立することを保証。
    cfg = load_config(overrides={
        "montecarlo": {"n_mc": 50},
        "tag_positioning": {"enabled": False},
        "calibration": {"gauge": "convention"},
    })
    rows = run_condition(cfg, condition_id=0)
    assert rows
    for r in rows:
        assert r["rmse_anchor_shape_mm"] <= r["rmse_anchor_abs_mm"] + 1e-9
