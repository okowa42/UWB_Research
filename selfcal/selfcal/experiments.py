"""E0-E3 の条件展開(§6)。Phase A は E1 ベースケースまで。

各実験は (config, condition_id) のリストを返す。スイープ(E2 の OFAT / 2軸グリッド)は
Phase B で拡張するが、宣言的に条件を積む骨組みを先に用意する。
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

from .io.config_loader import deep_merge


def e1_base(base_cfg: Mapping[str, Any]) -> list[tuple[dict, int]]:
    """E1: 公称パラメータ1条件(ベースケース)。"""
    return [(dict(base_cfg), 0)]


def ofat(
    base_cfg: Mapping[str, Any],
    section: str,
    key: str,
    values: list[Any],
) -> list[tuple[dict, int]]:
    """One-Factor-At-a-Time: 1パラメータを values で振った条件列。"""
    conditions: list[tuple[dict, int]] = []
    for cid, val in enumerate(values):
        cfg = deep_merge(base_cfg, {section: {key: val}})
        conditions.append((cfg, cid))
    return conditions


# 実験レジストリ(Phase A で使うもののみ)。
EXPERIMENTS: dict[str, Callable[[Mapping[str, Any]], list[tuple[dict, int]]]] = {
    "E1": e1_base,
}


def build_conditions(
    exp_id: str, base_cfg: Mapping[str, Any]
) -> list[tuple[dict, int]]:
    if exp_id not in EXPERIMENTS:
        raise KeyError(
            f"未知の実験ID: {exp_id!r}(利用可能: {sorted(EXPERIMENTS)})"
        )
    return EXPERIMENTS[exp_id](base_cfg)
