"""D: 推定アンカーでタグ測位(§4.5)。

タググリッド各点で、可視アンカー(真距離 <= R_max)への測距ノイズを1回実現し、
- 推定アンカー座標 + そのノイズ距離 -> タグ推定位置
- **同一ノイズ実現**で真アンカー座標版も計算
の両方を trilateration(pdop 流用)で解く。両者の差から、測距ノイズ由来と
アンカー推定誤差由来の寄与を分離(ΔRMSE, metrics 側で算出)できる。

可視アンカー < 4 は「測位不能」(NaN)。乱数は注入 Generator のみ(V-6)。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry_bridge import trilateration


@dataclass(frozen=True)
class TagResult:
    grid_mm: np.ndarray        # (M,3) タグ真位置
    est_pos_mm: np.ndarray     # (M,3) 推定アンカー版の測位結果(不能は NaN)
    truth_pos_mm: np.ndarray   # (M,3) 真アンカー版(同一ノイズ)。ノイズ寄与の基準
    visible_count: np.ndarray  # (M,) 可視アンカー数


def build_tag_grid(cfg: dict) -> np.ndarray:
    """タググリッド (M,3) を生成。span 四方 × step 間隔 × grid_z 各層。"""
    tp = cfg["tag_positioning"]
    span = float(tp["grid_span_mm"])
    step = float(tp["grid_step_mm"])
    zs = [float(z) for z in tp["grid_z_mm"]]
    axis = np.arange(-span / 2.0, span / 2.0 + step / 2.0, step)
    pts = []
    for z in zs:
        for y in axis:
            for x in axis:
                pts.append([x, y, z])
    return np.asarray(pts, dtype=float)


def position_tags(
    true_xyz_mm: np.ndarray,
    est_xyz_mm: np.ndarray,
    cfg: dict,
    rng: np.random.Generator,
) -> TagResult:
    """タググリッド全点を測位する。"""
    r_max = float(cfg["ranging"]["r_max_mm"])
    sigma_r = float(cfg["ranging"]["sigma_r_mm"])
    m = int(cfg["ranging"]["averaging_m"])
    eff_sigma = sigma_r / np.sqrt(m) if m > 1 else sigma_r

    grid = build_tag_grid(cfg)
    n_tag = grid.shape[0]
    est_pos = np.full((n_tag, 3), np.nan)
    truth_pos = np.full((n_tag, 3), np.nan)
    vis_count = np.zeros(n_tag, dtype=int)

    for k in range(n_tag):
        tag = grid[k]
        d_true = np.linalg.norm(true_xyz_mm - tag, axis=1)
        visible = d_true <= r_max
        vis_count[k] = int(visible.sum())
        if vis_count[k] < 4:
            continue  # 測位不能
        # 可視アンカーへの測距ノイズを1回実現(真アンカー基準の物理距離)
        noisy = d_true[visible] + rng.normal(0.0, eff_sigma, vis_count[k])
        truth_pos[k] = trilateration(true_xyz_mm[visible], noisy)
        est_pos[k] = trilateration(est_xyz_mm[visible], noisy)

    return TagResult(
        grid_mm=grid,
        est_pos_mm=est_pos,
        truth_pos_mm=truth_pos,
        visible_count=vis_count,
    )
