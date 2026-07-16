"""B: アンカー間 TWR 測距(§4.3)。

真配置(true_xyz)の全ペアについて距離を測る:
    d_ij = ||p_i - p_j||,  観測 = d_ij + b_r + N(0, σ_r²)
- d_ij > R_max のペアは欠測(NaN)。
- 対称行列(i<j を1回測って両側にミラー)。対角は NaN(自己測距なし)。
- m 回平均オプション: 実効 σ_r = σ_r / √m。
- NLOS は p_nlos 枠のみ(公称0)。正バイアス mu_nlos を上乗せ。
- **グローバル np.random は使わず注入 Generator のみ**(V-6)。

σ_r は距離非依存(TBD-6: R_max<=150m の限り影響なし)。
"""
from __future__ import annotations

import numpy as np


def true_distance_matrix(true_xyz_mm: np.ndarray) -> np.ndarray:
    """(N,N) の真ユークリッド距離行列。対角0。"""
    diff = true_xyz_mm[:, None, :] - true_xyz_mm[None, :, :]
    return np.linalg.norm(diff, axis=2)


def measure_ranges(
    true_xyz_mm: np.ndarray,
    cfg: dict,
    rng: np.random.Generator,
) -> np.ndarray:
    """アンカー間測距行列 (N,N) を返す。欠測=NaN, 対角=NaN, 対称。"""
    rng_cfg = cfg["ranging"]
    tbd = cfg["tbd"]
    r_max = float(rng_cfg["r_max_mm"])
    sigma_r = float(rng_cfg["sigma_r_mm"])
    m = int(rng_cfg["averaging_m"])
    b_r = float(tbd["b_r_mm"])
    p_nlos = float(tbd["p_nlos"])
    mu_nlos = float(tbd["mu_nlos_mm"])

    eff_sigma = sigma_r / np.sqrt(m) if m > 1 else sigma_r

    d_true = true_distance_matrix(true_xyz_mm)
    n = d_true.shape[0]
    out = np.full((n, n), np.nan)

    iu = np.triu_indices(n, k=1)  # 上三角(i<j)の全ペア
    for i, j in zip(*iu):
        d = d_true[i, j]
        if d > r_max:
            continue  # 欠測のまま NaN
        obs = d + b_r + rng.normal(0.0, eff_sigma)
        if p_nlos > 0.0 and rng.random() < p_nlos:
            obs += rng.exponential(mu_nlos)  # NLOS 正バイアス枠(公称未使用)
        out[i, j] = obs
        out[j, i] = obs  # 対称ミラー
    return out
