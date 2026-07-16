"""E: 1試行の集計指標(§4.6)。

- RMSE_anchor_abs / _shape(Procrustes 整列後)と **水平/鉛直分解**(v1.1 追加)。
- RMSE_tag / ΔRMSE_tag(推定アンカー版 − 真アンカー版, 同一ノイズ)と H/V 分解。
- PDOP_true / PDOP_est(タググリッド中央値)と PDOP 過信度。
- カバレッジ率 C(ε_thr)、収束フラグ。
共面近傍では鉛直のみ極端に劣化するため H/V 分解が必須。
"""
from __future__ import annotations

import numpy as np

from .alignment import procrustes_align
from .geometry_bridge import dop_components


def rmse_components(est_mm: np.ndarray, truth_mm: np.ndarray) -> tuple[float, float, float]:
    """(full, horizontal(xy), vertical(z)) RMSE を返す。"""
    d = np.asarray(est_mm, dtype=float) - np.asarray(truth_mm, dtype=float)
    full = float(np.sqrt(np.mean(np.sum(d ** 2, axis=1))))
    h = float(np.sqrt(np.mean(d[:, 0] ** 2 + d[:, 1] ** 2)))
    v = float(np.sqrt(np.mean(d[:, 2] ** 2)))
    return full, h, v


def _median_pdop(anchor_xyz: np.ndarray, tags: np.ndarray, visible_mask: np.ndarray,
                 r_max: float) -> tuple[float, float, float]:
    """測位可能タグでの PDOP/HDOP/VDOP 中央値(真距離ベースの幾何)。"""
    pdops, hdops, vdops = [], [], []
    for k in np.where(visible_mask)[0]:
        tag = tags[k]
        d = np.linalg.norm(anchor_xyz - tag, axis=1)
        vis = d <= r_max
        if vis.sum() < 4:
            continue
        p, h, v = dop_components(anchor_xyz[vis], tag)
        if np.isfinite(p):
            pdops.append(p)
            hdops.append(h)
            if v is not None and np.isfinite(v):
                vdops.append(v)
    med = lambda a: float(np.median(a)) if a else float("nan")
    return med(pdops), med(hdops), med(vdops)


def trial_metrics(
    true_xyz_mm: np.ndarray,
    est_xyz_mm: np.ndarray,
    calib_result,
    tag_result,
    cfg: dict,
) -> dict:
    """1試行の全指標を平坦 dict で返す(long-format CSV の1行素材)。"""
    out: dict[str, float] = {}
    r_max = float(cfg["ranging"]["r_max_mm"])
    sigma_r = float(cfg["ranging"]["sigma_r_mm"])
    eps = float(cfg["metrics"]["epsilon_thr_mm"])

    # --- アンカー誤差(絶対) ---
    a_abs, a_abs_h, a_abs_v = rmse_components(est_xyz_mm, true_xyz_mm)
    out["rmse_anchor_abs_mm"] = a_abs
    out["rmse_anchor_abs_h_mm"] = a_abs_h
    out["rmse_anchor_abs_v_mm"] = a_abs_v

    # --- アンカー誤差(Procrustes 整列後 = 形状) ---
    align = procrustes_align(est_xyz_mm, true_xyz_mm, allow_reflection=True)
    s_full, s_h, s_v = rmse_components(align.aligned_mm, true_xyz_mm)
    out["rmse_anchor_shape_mm"] = s_full
    out["rmse_anchor_shape_h_mm"] = s_h
    out["rmse_anchor_shape_v_mm"] = s_v

    # --- 収束・剛性 ---
    out["converged"] = float(bool(calib_result.converged))
    out["rigidity_ok"] = float(bool(calib_result.rigidity_ok))
    out["iterations"] = float(calib_result.iterations)
    out["rigidity_min_singular"] = float(calib_result.info.get("rigidity_min_singular", float("nan")))
    out["rigidity_cond"] = float(calib_result.info.get("rigidity_cond", float("nan")))
    out["rms_residual_mm"] = float(calib_result.info.get("rms_residual_mm", float("nan")))

    # --- タグ測位 ---
    if tag_result is not None:
        grid = tag_result.grid_mm
        est_pos = tag_result.est_pos_mm
        tru_pos = tag_result.truth_pos_mm
        positionable = np.isfinite(est_pos).all(axis=1)
        n_pos = int(positionable.sum())
        out["tag_positionable"] = float(n_pos)
        out["tag_total"] = float(grid.shape[0])
        if n_pos > 0:
            g = grid[positionable]
            e = est_pos[positionable]
            t = tru_pos[positionable]
            t_full, t_h, t_v = rmse_components(e, g)
            out["rmse_tag_mm"] = t_full
            out["rmse_tag_h_mm"] = t_h
            out["rmse_tag_v_mm"] = t_v
            # ΔRMSE_tag: 推定アンカー版 − 真アンカー版(同一ノイズ)
            tt_full, _, _ = rmse_components(t, g)
            out["rmse_tag_trueanchor_mm"] = tt_full
            out["delta_rmse_tag_mm"] = t_full - tt_full
            # カバレッジ率 C(ε_thr)
            err = np.linalg.norm(e - g, axis=1)
            out["coverage"] = float(np.mean(err <= eps))
            # PDOP true/est(中央値)と過信度
            p_true, h_true, v_true = _median_pdop(true_xyz_mm, grid, positionable, r_max)
            p_est, h_est, v_est = _median_pdop(est_xyz_mm, grid, positionable, r_max)
            out["pdop_true"] = p_true
            out["pdop_est"] = p_est
            out["vdop_true"] = v_true
            out["vdop_est"] = v_est
            # 過信度: 実測 RMSE / (PDOP_est · σ_r)。>1 で PDOP は楽観的。
            pred = p_est * sigma_r
            out["pdop_overconfidence"] = float(t_full / pred) if pred > 0 else float("nan")
        else:
            for key in ["rmse_tag_mm", "rmse_tag_h_mm", "rmse_tag_v_mm",
                        "rmse_tag_trueanchor_mm", "delta_rmse_tag_mm", "coverage",
                        "pdop_true", "pdop_est", "vdop_true", "vdop_est",
                        "pdop_overconfidence"]:
                out[key] = float("nan")
    return out
