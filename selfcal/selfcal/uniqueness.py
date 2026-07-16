"""多スタート大域一意性検査(Phase C, §4.4 注意1)。

剛性ランク(rigidity.check_rigidity)は連続変形に対する**局所**一意性の必要条件だが、
鏡映・反転などの**離散**不定性(大域一意性)は捕捉できない。本モジュールは自己校正を
複数の初期配置から回し、収束かつ低残差(データに等しく適合)な解を形状でクラスタリング
して、相異なる解が2つ以上あれば「離散不定性あり(大域一意でない)」と判定する。

代表例: 既知アンカーが共面だと、その平面を鏡とする自由アンカーの鏡映が距離を保つため
2解が生じる(V-8 の共面3D校正不能を離散不定性側から裏付ける)。既知が非共面なら鏡映は
既知点で破れ1解に収束する。

形状距離は**回転のみ**の Procrustes RMSE(allow_reflection=False)で測る。並進・回転は
ゲージ自由度として商化し、鏡映は「真の剛体運動でない=別配置」として区別する。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from .alignment import procrustes_align
from .calibration import LMEstimator


@dataclass(frozen=True)
class UniquenessResult:
    n_starts: int                    # 試した初期配置数
    n_converged: int                 # LM 収束数
    n_admissible: int                # 収束かつ低残差(=データに適合)な解の数
    n_distinct: int                  # 相異なる形状クラスタ数
    uniqueness_ok: bool              # n_distinct <= 1(大域一意)
    best_residual_mm: float          # 最良の rms 残差
    max_cluster_shape_dist_mm: float # クラスタ代表間の最大 回転のみ Procrustes RMSE
    cluster_residuals_mm: list[float] = field(default_factory=list)


def _reflect_free_z(xyz: np.ndarray, free_mask: np.ndarray, z0: float) -> np.ndarray:
    """自由アンカーの z を平面 z=z0 について鏡映した配置(鏡映基底を種にする)。"""
    out = np.array(xyz, dtype=float, copy=True)
    out[free_mask, 2] = 2.0 * z0 - out[free_mask, 2]
    return out


def multistart_uniqueness(
    dist_matrix_mm: np.ndarray,
    intended_xyz_mm: np.ndarray,
    known_idx: Sequence[int],
    gauge: str,
    dof: int,
    rng: np.random.Generator,
    estimator: LMEstimator | None = None,
    n_starts: int = 12,
    perturb_mm: float = 500.0,
    resid_tol_mm: float = 1.0,
    cluster_tol_mm: float = 10.0,
    reflect_fraction: float = 0.5,
) -> UniquenessResult:
    """複数初期値から自己校正し、相異なる低残差解の数で大域一意性を判定する。

    - 初期配置は意図配置に Gaussian(perturb_mm) を付加。うち reflect_fraction は
      既知平面 z0 について自由アンカー z を鏡映してから付加し、鏡映基底を明示的に探索する。
    - 「適合」= converged かつ rms 残差 <= best_residual + resid_tol_mm。noisy 運用では
      resid_tol_mm を測距ノイズ規模に合わせて広げること(既定は低ノイズ診断向け)。
    - クラスタリングは回転のみ Procrustes RMSE < cluster_tol_mm を同一解とみなす貪欲法。
      cluster_tol_mm は同一基底の解のばらつきより大きく、鏡映等の離散分離より小さく取る。
    """
    estimator = estimator or LMEstimator()
    intended = np.asarray(intended_xyz_mm, dtype=float)
    n = intended.shape[0]

    known = np.asarray([] if known_idx is None else known_idx, dtype=int)
    free_mask = np.ones(n, dtype=bool)
    if known.size:
        free_mask[known] = False
    # 鏡映の種にする基準平面(既知点があればその平均 z, なければ全体平均 z)。
    z0 = float(intended[known, 2].mean()) if known.size else float(intended[:, 2].mean())

    solutions: list[np.ndarray] = []
    residuals: list[float] = []
    n_converged = 0
    n_reflect = int(round(n_starts * reflect_fraction))

    for s in range(n_starts):
        init = np.array(intended, copy=True)
        if s < n_reflect:
            init = _reflect_free_z(init, free_mask, z0)
        # 自由アンカーのみ摂動(既知は最終的に固定されるが初期値も動かさない)
        noise = rng.normal(0.0, perturb_mm, size=(n, 3))
        noise[~free_mask] = 0.0
        init = init + noise

        res = estimator.calibrate(
            dist_matrix_mm, init, known if gauge == "known" else [], gauge, dof, rng,
        )
        if not res.converged:
            continue
        n_converged += 1
        solutions.append(np.asarray(res.anchor_positions_mm, dtype=float))
        residuals.append(float(res.info.get("rms_residual_mm", np.nan)))

    if not solutions:
        return UniquenessResult(
            n_starts=n_starts, n_converged=0, n_admissible=0, n_distinct=0,
            uniqueness_ok=False, best_residual_mm=float("nan"),
            max_cluster_shape_dist_mm=float("nan"),
        )

    best = float(np.nanmin(residuals))
    admissible = [
        (sol, r) for sol, r in zip(solutions, residuals)
        if np.isfinite(r) and r <= best + resid_tol_mm
    ]

    # 貪欲クラスタリング(回転のみ Procrustes RMSE で同一性を判定)
    reps: list[np.ndarray] = []
    rep_res: list[float] = []
    max_dist = 0.0
    for sol, r in admissible:
        matched = False
        for i, rep in enumerate(reps):
            d = procrustes_align(sol, rep, allow_reflection=False).rmse_shape_mm
            max_dist = max(max_dist, d)
            if d < cluster_tol_mm:
                matched = True
                rep_res[i] = min(rep_res[i], r)
                break
        if not matched:
            reps.append(sol)
            rep_res.append(r)

    n_distinct = len(reps)
    return UniquenessResult(
        n_starts=n_starts,
        n_converged=n_converged,
        n_admissible=len(admissible),
        n_distinct=n_distinct,
        uniqueness_ok=(n_distinct <= 1),
        best_residual_mm=best,
        max_cluster_shape_dist_mm=float(max_dist),
        cluster_residuals_mm=sorted(rep_res),
    )
