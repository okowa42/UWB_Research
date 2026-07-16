"""LM 最小二乗による自己校正(第一実装, §4.4)。

測距残差 r_ij = ||p_i − p_j|| − obs_ij を scipy.optimize.least_squares(method='trf')
で最小化する。trf は共面近傍のランク落ち耐性から第一候補(v1.1 確定, lm は比較用)。

ゲージ不定性の処理を座標単位の free/fixed マスクで一般化する:
- G1 (gauge='known'): known_idx のアンカーを意図配置(=真値)に固定。残りを最適化。
- G2 (gauge='convention'): 規約固定 — アンカー0を原点・1をx軸上(y=z=0)・2をxy平面内
    (z=0)に拘束して 6 自由度を消す(2D では 3 自由度)。**Moore-Penrose 擬似逆に
    よる自由網調整は不採用**(v1.1)。初期配置を規約フレームへ剛体整列してから固定。
- dof=2 (z固定2D校正, E3/V-8): 全アンカーの z を意図値に固定し x,y のみ推定。距離は
    固定 z を含む 3D で評価する。

剛性チェック(rigidity.check_rigidity)を推定配置で実行し rigidity_ok を返す。
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy.optimize import least_squares

from ..rigidity import check_rigidity
from .base import CalibrationResult


def _align_to_convention(xyz_mm: np.ndarray, dim: int) -> np.ndarray:
    """規約フレームへ剛体整列(anchor0=原点, anchor1 を +x 軸, anchor2 を xy 平面)。

    z(dim=2 のとき)は変更しない。配置の形状は保存する。
    """
    out = np.array(xyz_mm, dtype=float, copy=True)
    p = out[:, :dim] - out[0, :dim]  # anchor0 を原点へ
    n = out.shape[0]
    if n < 2:
        out[:, :dim] = p
        return out

    e1 = p[1] / np.linalg.norm(p[1])
    if dim == 2:
        e2 = np.array([-e1[1], e1[0]])
        basis = np.column_stack([e1, e2])
    else:  # dim == 3
        if n >= 3:
            v2 = p[2] - np.dot(p[2], e1) * e1
            nrm = np.linalg.norm(v2)
            if nrm > 0:
                e2 = v2 / nrm
            else:  # anchor2 が anchor0-1 と共線: 任意直交ベクトル
                tmp = np.array([1.0, 0.0, 0.0])
                if abs(np.dot(tmp, e1)) > 0.9:
                    tmp = np.array([0.0, 1.0, 0.0])
                e2 = tmp - np.dot(tmp, e1) * e1
                e2 /= np.linalg.norm(e2)
        else:
            tmp = np.array([1.0, 0.0, 0.0])
            if abs(np.dot(tmp, e1)) > 0.9:
                tmp = np.array([0.0, 1.0, 0.0])
            e2 = tmp - np.dot(tmp, e1) * e1
            e2 /= np.linalg.norm(e2)
        e3 = np.cross(e1, e2)
        basis = np.column_stack([e1, e2, e3])

    out[:, :dim] = p @ basis
    return out


def _build_masks(
    intended_xyz_mm: np.ndarray,
    known_idx: Sequence[int],
    gauge: str,
    dim: int,
) -> tuple[np.ndarray, np.ndarray]:
    """(base_full (N,3), free_mask (N,3)) を返す。

    base_full は固定座標の値を保持し、free_mask=True の座標のみ最適化する。
    dof=2 のとき z 列は常に fixed(意図値)。
    """
    n = intended_xyz_mm.shape[0]
    free = np.ones((n, 3), dtype=bool)
    if dim == 2:
        free[:, 2] = False  # z は意図値に固定

    if gauge == "known":
        base = np.array(intended_xyz_mm, dtype=float, copy=True)
        known = np.asarray(known_idx, dtype=int)
        if known.size == 0:
            raise ValueError("gauge='known' には known_idx が必要")
        free[known, :] = False  # 既知アンカーを丸ごと固定
    elif gauge == "convention":
        base = _align_to_convention(intended_xyz_mm, dim)
        free[0, :dim] = False               # anchor0: 原点
        if n > 1:
            free[1, 1:dim] = False           # anchor1: y(,z) = 0
        if n > 2 and dim == 3:
            free[2, 2] = False               # anchor2: z = 0
    else:
        raise ValueError(f"未知の gauge: {gauge!r}")

    return base, free


class LMEstimator:
    """least_squares(trf) ベースの自己校正推定器。"""

    def __init__(self, method: str = "trf", max_nfev: int = 2000,
                 ftol: float = 1e-12, xtol: float = 1e-12):
        self.method = method
        self.max_nfev = max_nfev
        self.ftol = ftol
        self.xtol = xtol

    def calibrate(
        self,
        dist_matrix_mm: np.ndarray,
        intended_xyz_mm: np.ndarray,
        known_idx: Sequence[int],
        gauge: str,
        dof: int,
        rng: np.random.Generator,
    ) -> CalibrationResult:
        dim = int(dof)
        intended_xyz_mm = np.asarray(intended_xyz_mm, dtype=float)
        n = intended_xyz_mm.shape[0]

        # 観測エッジ(欠測でない上三角ペア)
        edges = [
            (i, j)
            for i in range(n)
            for j in range(i + 1, n)
            if np.isfinite(dist_matrix_mm[i, j])
        ]
        obs = np.array([dist_matrix_mm[i, j] for (i, j) in edges])
        idx_i = np.array([i for (i, j) in edges], dtype=int)
        idx_j = np.array([j for (i, j) in edges], dtype=int)

        base, free = _build_masks(intended_xyz_mm, known_idx, gauge, dim)
        p0 = base[free]

        def unpack(params: np.ndarray) -> np.ndarray:
            full = base.copy()
            full[free] = params
            return full

        def residual(params: np.ndarray) -> np.ndarray:
            full = unpack(params)
            d = np.linalg.norm(full[idx_i] - full[idx_j], axis=1)  # 3D 距離
            return d - obs

        if p0.size == 0:
            # 自由パラメータなし(全固定): 初期配置がそのまま解
            est = base
            res_vec = residual(np.array([]))
            nfev, converged = 0, True
        else:
            sol = least_squares(
                residual, p0, method=self.method,
                max_nfev=self.max_nfev, ftol=self.ftol, xtol=self.xtol,
            )
            est = unpack(sol.x)
            res_vec = sol.fun
            nfev = int(sol.nfev)
            converged = bool(sol.success)

        rig = check_rigidity(
            est, dist_matrix_mm, gauge=gauge,
            known_idx=known_idx, dim=dim,
        )

        return CalibrationResult(
            anchor_positions_mm=est,
            residuals_mm=res_vec,
            iterations=nfev,
            converged=converged,
            rigidity_ok=rig.rigidity_ok,
            info={
                "gauge": gauge,
                "dof": dim,
                "n_edges": len(edges),
                "rigidity_rank": rig.rank,
                "rigidity_required_rank": rig.required_rank,
                "rigidity_min_singular": rig.min_singular,
                "rigidity_cond": rig.cond,
                "rms_residual_mm": float(np.sqrt(np.mean(res_vec ** 2)))
                if res_vec.size else 0.0,
            },
        )
