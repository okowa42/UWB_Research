"""seed 階層管理(実験 -> 条件 -> 試行)。V-6 再現性の要。

全乱数はここで生成した ``np.random.Generator`` 経由に統一する。グローバル
``np.random`` は使用禁止(seed 再現が壊れるため)。同一 (root_seed, condition_id,
trial_id) からは常に同一の Generator が得られる。
"""
from __future__ import annotations

import numpy as np

# SeedSequence の spawn key に混ぜる固定ドメイン定数。用途間の衝突を避ける。
_DOMAIN = 0x5E1FCA1


def make_root(root_seed: int) -> np.random.SeedSequence:
    """実験ルート SeedSequence を作る。"""
    return np.random.SeedSequence([_DOMAIN, int(root_seed)])


def trial_generator(
    root_seed: int, condition_id: int, trial_id: int
) -> np.random.Generator:
    """(実験, 条件, 試行) から決定的に Generator を得る。

    SeedSequence.spawn_key で階層を表現する。異なる condition/trial は独立、
    同じ組は完全再現。
    """
    root = make_root(root_seed)
    child = np.random.SeedSequence(
        entropy=root.entropy,
        spawn_key=(*root.spawn_key, int(condition_id), int(trial_id)),
    )
    return np.random.default_rng(child)
