"""A: 意図配置生成 + 展開誤差モデル(§4.1/4.2)。

- 意図配置: 平面パターン(perimeter/grid)を生成し、一般アンカーは公称高さ z_nominal、
  既知アンカー(G1)は非共面高さ known_z_mm を与える。**既知アンカーが共面だと鏡映を
  固定できない**ため、非共面配置(3台 z=1500, 1台 z=2900 等)を強制する。
- 展開誤差: 水平/鉛直分離ガウス diag(σ_deploy², σ_deploy², σ_v²) を Generator で付加。
  **既知アンカーには誤差を与えない**(真値として固定する)。

戻り値は (intended_xyz, true_xyz) の両方。true は誤差付き実配置、intended は
自己校正の初期値。単位はすべて mm。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class Deployment:
    intended_xyz_mm: np.ndarray   # (N,3) 意図配置(校正初期値)
    true_xyz_mm: np.ndarray       # (N,3) 展開誤差付き実配置(真値)
    known_idx: np.ndarray         # (k,)  既知アンカー index (G1)


def _perimeter_xy(n: int, area_mm: float) -> np.ndarray:
    """一辺 area_mm の正方形周上に n 点を等間隔配置した (n,2)。

    角を確実に含めるため、周長パラメータ [0,4) を n 等分する。n>=4 では四隅付近が
    含まれ、非共線性(剛性に有利)を確保しやすい。
    """
    half = area_mm / 2.0
    # 正方形の周を [0,4) でパラメトライズ(各辺が長さ1)
    t = np.linspace(0.0, 4.0, n, endpoint=False)
    pts = np.empty((n, 2))
    for i, ti in enumerate(t):
        side = int(ti)
        f = ti - side
        if side == 0:      # 下辺: 左下 -> 右下
            pts[i] = [-half + f * area_mm, -half]
        elif side == 1:    # 右辺: 右下 -> 右上
            pts[i] = [half, -half + f * area_mm]
        elif side == 2:    # 上辺: 右上 -> 左上
            pts[i] = [half - f * area_mm, half]
        else:              # 左辺: 左上 -> 左下
            pts[i] = [-half, half - f * area_mm]
    return pts


def _grid_xy(n: int, area_mm: float) -> np.ndarray:
    """area_mm 四方に n 点を格子状(概ね正方格子)に配置した (n,2)。"""
    side = int(np.ceil(np.sqrt(n)))
    xs = np.linspace(-area_mm / 2.0, area_mm / 2.0, side)
    grid = np.array([[x, y] for y in xs for x in xs])
    return grid[:n]


def _apply_unknown_height_spec(
    z: np.ndarray,
    known_idx: np.ndarray,
    spec: dict | None,
    rng: np.random.Generator | None,
) -> None:
    """未知アンカー(known_idx 以外)の意図高さを spec に従って上書きする(E2c)。

    spec の形式:
      - {"levels": [...]}    : レベル列を index 順に巡回割当(層化・交互配置)。
      - {"uniform": [lo,hi]} : 一様乱数で試行毎に引き直す(rng 必須)。
    spec が None のときは既定(全台 z_nominal)のまま何もしない。
    """
    if spec is None:
        return
    n = z.shape[0]
    known_set = set(int(i) for i in known_idx.tolist())
    unknown = np.array([i for i in range(n) if i not in known_set], dtype=int)
    if unknown.size == 0:
        return
    levels = spec.get("levels")
    uniform = spec.get("uniform")
    if levels is not None:
        lv = np.asarray(levels, dtype=float)
        # index 順に巡回割当(未知アンカー数 > レベル数でも循環でカバー)
        z[unknown] = lv[np.arange(unknown.size) % lv.size]
    elif uniform is not None:
        if rng is None:
            raise ValueError("uniform 高さ spec には rng が必要(試行毎の引き直し)")
        lo, hi = float(uniform[0]), float(uniform[1])
        z[unknown] = rng.uniform(lo, hi, unknown.size)
    else:
        raise ValueError(f"未知の高さ spec: {spec!r}(levels か uniform を指定)")


def intended_layout(
    cfg: dict, rng: np.random.Generator | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """意図配置 (N,3) と既知アンカー index を返す(誤差なし)。

    rng は未知アンカー高さの一様ランダム spec(E2c H3/H4)でのみ消費する。
    それ以外の spec / spec なしでは rng を引かないため既存実験の乱数列は不変。
    """
    dep = cfg["deployment"]
    known = cfg["known"]
    n = int(dep["n_anchors"])
    pattern = dep["pattern"]
    area = float(dep["area_mm"])

    if pattern == "perimeter":
        xy = _perimeter_xy(n, area)
    elif pattern == "grid":
        xy = _grid_xy(n, area)
    else:
        raise ValueError(f"未知の配置パターン: {pattern!r}")

    z = np.full(n, float(dep["z_nominal_mm"]))

    known_idx = np.asarray(known["known_idx"], dtype=int)
    known_z = np.asarray(known["known_z_mm"], dtype=float)
    if known_idx.size:
        if known_idx.max() >= n:
            raise ValueError("known_idx がアンカー数を超えている")
        # 既知アンカーは非共面高さで上書き(G1: 鏡映固定のため)
        z[known_idx] = known_z

    # E2c: 未知アンカーの意図高さパターン(spec なしなら全台 z_nominal のまま)。
    _apply_unknown_height_spec(z, known_idx, dep.get("unknown_z_spec"), rng)

    xyz = np.column_stack([xy, z])
    return xyz, known_idx


def add_deployment_error(
    intended_xyz_mm: np.ndarray,
    known_idx: Sequence[int],
    sigma_deploy_mm: float,
    sigma_v_mm: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """意図配置に水平/鉛直分離ガウス誤差を付加した true 配置を返す。

    既知アンカー(known_idx)には誤差を与えず intended を保持する。
    """
    true_xyz = np.array(intended_xyz_mm, dtype=float, copy=True)
    n = true_xyz.shape[0]
    # diag(σ_deploy², σ_deploy², σ_v²)
    noise = np.column_stack([
        rng.normal(0.0, sigma_deploy_mm, n),
        rng.normal(0.0, sigma_deploy_mm, n),
        rng.normal(0.0, sigma_v_mm, n),
    ])
    true_xyz += noise
    known_idx = np.asarray(known_idx, dtype=int)
    if known_idx.size:
        true_xyz[known_idx] = intended_xyz_mm[known_idx]  # 既知は真値固定
    return true_xyz


def build_deployment(cfg: dict, rng: np.random.Generator) -> Deployment:
    """A 段の統括: 意図配置生成 + 展開誤差付加。"""
    dep = cfg["deployment"]
    intended, known_idx = intended_layout(cfg, rng)
    true_xyz = add_deployment_error(
        intended,
        known_idx,
        float(dep["sigma_deploy_mm"]),
        float(dep["sigma_v_mm"]),
        rng,
    )
    return Deployment(
        intended_xyz_mm=intended,
        true_xyz_mm=true_xyz,
        known_idx=known_idx,
    )
