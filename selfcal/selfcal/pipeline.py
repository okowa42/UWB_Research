"""A→E を1試行実行する統括(run_single_trial)。

各試行は (root_seed, condition_id, trial_id) から決定的な Generator を1本得て、
配置・測距・タグ測位の全乱数をそこから引く(V-6 再現性)。
"""
from __future__ import annotations

import time

from . import deployment, ranging, tag_positioning
from .calibration import LMEstimator
from .metrics import trial_metrics
from .rng import trial_generator


def _make_estimator(cfg: dict) -> LMEstimator:
    cal = cfg["calibration"]
    return LMEstimator(
        method=cal["lm_method"],
        max_nfev=int(cal["max_nfev"]),
        ftol=float(cal["ftol"]),
        xtol=float(cal["xtol"]),
    )


def run_single_trial(
    cfg: dict, condition_id: int, trial_id: int
) -> dict:
    """1試行を実行し、指標 dict(long-format CSV の1行素材)を返す。"""
    root_seed = int(cfg["montecarlo"]["seed"])
    rng = trial_generator(root_seed, condition_id, trial_id)

    t0 = time.perf_counter()

    # A: 配置 + 展開誤差
    dep = deployment.build_deployment(cfg, rng)

    # B: アンカー間測距
    dist = ranging.measure_ranges(dep.true_xyz_mm, cfg, rng)

    # C: 自己校正
    cal = cfg["calibration"]
    estimator = _make_estimator(cfg)
    calib = estimator.calibrate(
        dist,
        dep.intended_xyz_mm,
        cfg["known"]["known_idx"] if cal["gauge"] == "known" else [],
        cal["gauge"],
        int(cal["dof"]),
        rng,
    )

    # D: タグ測位(推定/真アンカー, 同一ノイズ)
    tag_res = None
    if cfg["tag_positioning"]["enabled"]:
        tag_res = tag_positioning.position_tags(
            dep.true_xyz_mm, calib.anchor_positions_mm, cfg, rng
        )

    # E: 集計
    row = trial_metrics(
        dep.true_xyz_mm, calib.anchor_positions_mm, calib, tag_res, cfg
    )
    row["condition_id"] = condition_id
    row["trial_id"] = trial_id
    row["compute_time_s"] = time.perf_counter() - t0
    row["n_anchors"] = cfg["deployment"]["n_anchors"]
    row["sigma_r_mm"] = cfg["ranging"]["sigma_r_mm"]
    row["sigma_deploy_mm"] = cfg["deployment"]["sigma_deploy_mm"]
    row["sigma_v_mm"] = cfg["deployment"]["sigma_v_mm"]
    row["r_max_mm"] = cfg["ranging"]["r_max_mm"]
    # 高さ多様性スイープの軸(条件内で一定なスカラー): 既知アンカー最大高さ。
    row["known_z_max_mm"] = float(max(cfg["known"]["known_z_mm"]))
    row["gauge"] = cfg["calibration"]["gauge"]
    row["dof"] = cfg["calibration"]["dof"]
    # E2c: 未知アンカー高さ分散パターンのラベルと、この試行で実現した未知アンカー高さの
    # 標準偏差(H3/H4 は試行毎に変動するため実測値を記録する)。
    row["height_pattern"] = cfg["deployment"].get("height_pattern") or ""
    known_idx = set(int(i) for i in cfg["known"]["known_idx"])
    unknown = [i for i in range(dep.intended_xyz_mm.shape[0]) if i not in known_idx]
    row["unknown_z_std_mm"] = (
        float(dep.intended_xyz_mm[unknown, 2].std()) if unknown else 0.0
    )
    return row
