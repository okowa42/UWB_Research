"""剛性行列の構成とモード別ランク検査(§4.4)。

距離拘束ネットワークの無限小剛性を判定する。各観測エッジ (i,j) は剛性行列に1行を
与え、頂点 i のブロックに (p_i - p_j)、頂点 j のブロックに (p_j - p_i) を置く。

モード別ランク条件(v1.1 確定):
- G2 (gauge='convention'): rank(R) = dim·N − dim(dim+1)/2
    3D なら 3N−6、2D なら 2N−3(並進+回転の自由度を除く)。
- G1 (gauge='known'): 既知点を列から除いた縮約行列 R_free について
    rank(R_free) = dim·N_free(既知点ピン留めなので −(自由度) 不要)。
    既知−既知エッジは R_free で全ゼロ行になるため除外する。

**bool 判定に加え最小特異値(必要ランク番目の特異値)と条件数を必ず記録**する
(共面近傍の「ランクは足りるが悪条件」を捕捉するため)。剛性ランクは連続変形に対する
必要条件であり、鏡映等の離散的不定性(大域一意性)の十分条件ではない(§4.4 注意1)。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RigidityResult:
    rigidity_ok: bool          # rank >= required_rank
    rank: int                  # 数値ランク
    required_rank: int         # モード別の必要ランク
    min_singular: float        # 必要ランク番目の特異値(0近傍=悪条件/退化)
    cond: float                # σ_max / min_singular(inf=退化)
    dim: int                   # 3(3D) / 2(2D)
    gauge: str
    n_edges: int


def edges_from_matrix(dist_matrix_mm: np.ndarray) -> list[tuple[int, int]]:
    """欠測(NaN)でない上三角ペア (i<j) をエッジとして列挙。"""
    n = dist_matrix_mm.shape[0]
    edges: list[tuple[int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if np.isfinite(dist_matrix_mm[i, j]):
                edges.append((i, j))
    return edges


def rigidity_matrix(
    xyz_mm: np.ndarray, edges: list[tuple[int, int]], dim: int
) -> np.ndarray:
    """剛性行列 R (n_edges, dim·N)。dim=2 のときは x,y のみ使用。"""
    n = xyz_mm.shape[0]
    R = np.zeros((len(edges), dim * n))
    for r, (i, j) in enumerate(edges):
        diff = xyz_mm[i, :dim] - xyz_mm[j, :dim]
        R[r, dim * i:dim * i + dim] = diff
        R[r, dim * j:dim * j + dim] = -diff
    return R


def check_rigidity(
    xyz_mm: np.ndarray,
    dist_matrix_mm: np.ndarray,
    gauge: str,
    known_idx=None,
    dim: int = 3,
) -> RigidityResult:
    """配置とエッジ集合から剛性を判定する。

    xyz_mm には真配置(または収束推定配置)を渡す。gauge='known' では known_idx の
    列を除いた縮約行列で判定する。
    """
    n = xyz_mm.shape[0]
    edges = edges_from_matrix(dist_matrix_mm)
    R = rigidity_matrix(xyz_mm, edges, dim)

    if gauge == "convention":
        R_eff = R
        required_rank = dim * n - dim * (dim + 1) // 2
    elif gauge == "known":
        known = np.asarray([] if known_idx is None else known_idx, dtype=int)
        free_mask = np.ones(n, dtype=bool)
        free_mask[known] = False
        n_free = int(free_mask.sum())
        # 自由頂点の列だけ残す(既知点をピン留め)
        col_keep = np.repeat(free_mask, dim)
        R_eff = R[:, col_keep]
        # 既知−既知エッジ(自由列が全ゼロの行)を除外
        nonzero_rows = np.any(np.abs(R_eff) > 0, axis=1)
        R_eff = R_eff[nonzero_rows]
        required_rank = dim * n_free
    else:
        raise ValueError(f"未知の gauge: {gauge!r}")

    if R_eff.size == 0 or R_eff.shape[0] == 0:
        return RigidityResult(
            rigidity_ok=(required_rank == 0), rank=0,
            required_rank=required_rank, min_singular=0.0, cond=np.inf,
            dim=dim, gauge=gauge, n_edges=len(edges),
        )

    s = np.linalg.svd(R_eff, compute_uv=False)
    # 標準的なランク許容誤差
    tol = max(R_eff.shape) * np.finfo(float).eps * (s[0] if s.size else 0.0)
    rank = int(np.sum(s > tol))

    # 必要ランク番目の特異値(降順)。足りない/退化なら 0。
    if required_rank <= 0:
        min_sv = float(s[0]) if s.size else 0.0
    elif required_rank <= s.size:
        min_sv = float(s[required_rank - 1])
    else:
        min_sv = 0.0
    cond = float(s[0] / min_sv) if min_sv > 0 else np.inf

    return RigidityResult(
        rigidity_ok=(rank >= required_rank),
        rank=rank,
        required_rank=required_rank,
        min_singular=min_sv,
        cond=cond,
        dim=dim,
        gauge=gauge,
        n_edges=len(edges),
    )
