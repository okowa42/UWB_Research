"""推定器インターフェース(抽象)。TBD-1(PF 等の後付け)対応。

新しい推定器は同じ ``Estimator`` プロトコルを実装するだけで pipeline.py を変更せず
差し替えられる。単位はすべて mm。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence

import numpy as np


@dataclass(frozen=True)
class CalibrationResult:
    anchor_positions_mm: np.ndarray   # (N,3) 推定アンカー座標
    residuals_mm: np.ndarray          # 測距残差
    iterations: int
    converged: bool
    rigidity_ok: bool                 # 剛性チェック結果(§4.4)
    info: dict = field(default_factory=dict)  # 推定器固有の付随情報


class Estimator(Protocol):
    def calibrate(
        self,
        dist_matrix_mm: np.ndarray,      # (N,N) 欠測は NaN
        intended_xyz_mm: np.ndarray,     # 初期値 = 意図配置
        known_idx: Sequence[int],        # 固定する既知アンカー index(G1)。空なら G2
        gauge: str,                      # 'known'(G1) | 'convention'(G2 規約固定)
        dof: int,                        # 3=3D校正 / 2=z固定2D校正(E3)
        rng: np.random.Generator,
    ) -> CalibrationResult: ...
