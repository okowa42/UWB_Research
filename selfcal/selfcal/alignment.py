"""Procrustes 整列(並進・回転・鏡映)(§4.6 G2)。

G2(規約固定)では推定配置の絶対座標系は真値とずれる。形状誤差を測るため、推定配置を
真配置へ剛体(+鏡映)整列してから RMSE を評価する。回転行列は
``scipy.linalg.orthogonal_procrustes`` を使用(独自実装しない)。スケールは固定
(UWB 距離は絶対尺度を持つため 1)。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import orthogonal_procrustes


@dataclass(frozen=True)
class Alignment:
    aligned_mm: np.ndarray   # (N,3) 真配置へ整列後の推定配置
    R: np.ndarray            # 回転(+鏡映可)行列
    t: np.ndarray            # 並進ベクトル
    rmse_shape_mm: float     # 整列後 RMSE(形状誤差)


def procrustes_align(
    estimated_mm: np.ndarray, truth_mm: np.ndarray, allow_reflection: bool = True
) -> Alignment:
    """estimated を truth へ整列(並進+回転, 既定で鏡映許容)。

    allow_reflection=False の場合は真の回転(det=+1)に制限する。
    """
    est = np.asarray(estimated_mm, dtype=float)
    tru = np.asarray(truth_mm, dtype=float)

    mu_e = est.mean(axis=0)
    mu_t = tru.mean(axis=0)
    ec = est - mu_e
    tc = tru - mu_t

    R, _ = orthogonal_procrustes(ec, tc)  # ec @ R ~ tc
    if not allow_reflection and np.linalg.det(R) < 0:
        # 鏡映を禁止: 最小特異方向を反転して det=+1 の回転に射影
        U, _, Vt = np.linalg.svd(ec.T @ tc)
        D = np.eye(R.shape[0])
        D[-1, -1] = -1.0
        R = U @ D @ Vt

    aligned = ec @ R + mu_t
    t = mu_t - mu_e @ R
    rmse = float(np.sqrt(np.mean(np.sum((aligned - tru) ** 2, axis=1))))
    return Alignment(aligned_mm=aligned, R=R, t=t, rmse_shape_mm=rmse)
