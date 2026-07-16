"""pdop.simulation.geometry への薄いアダプタ(import 集約点)。

依存を1ファイルに集約し、依存方向 selfcal/ -> pdop/simulation/geometry を単方向に
保つ。pdop 側は一切変更しない。

pdop.simulation の ``__init__`` は scenario -> station 等 GUI 寄りの副作用を連鎖
import するため、パッケージ経由では取り込めない。geometry.py は numpy と logging
のみに依存する純粋モジュールなので、**ファイル単位で直接ロード**して副作用を避ける
(計画の「純粋関数のみ再利用」に一致)。

**測距ノイズ生成には geometry.euclidean_distances を使わない**(グローバル np.random
を使うため V-6 と衝突) — ranging.py が Generator 注入版を独自実装する。ここで再輸出
するのは決定的な純粋関数のみ。
"""
from __future__ import annotations

import importlib.util
import pathlib

_GEOMETRY_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "pdop" / "simulation" / "geometry.py"
)

_spec = importlib.util.spec_from_file_location(
    "pdop_geometry_isolated", _GEOMETRY_PATH
)
if _spec is None or _spec.loader is None:  # pragma: no cover - パス破損時のみ
    raise ImportError(f"pdop geometry を読めない: {_GEOMETRY_PATH}")
_geometry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_geometry)

# 決定的な純粋関数のみ再輸出(euclidean_distances は意図的に除外)
trilateration = _geometry.trilateration
geometry_matrix = _geometry.geometry_matrix
covariance_matrix = _geometry.covariance_matrix
dop_components = _geometry.dop_components

__all__ = [
    "trilateration",
    "geometry_matrix",
    "covariance_matrix",
    "dop_components",
]
