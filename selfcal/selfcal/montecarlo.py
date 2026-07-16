"""1条件 = N_mc 試行(§2)。UWB_Sim runner.py の MC 構造を移植。

各試行は独立 Generator(rng 階層)で回るため、逐次でも並列でも結果は同一(V-6)。
"""
from __future__ import annotations

from typing import Iterator

from .pipeline import run_single_trial


def run_condition(cfg: dict, condition_id: int = 0) -> list[dict]:
    """1条件を N_mc 試行実行し、行 dict のリストを返す。"""
    return list(iter_condition(cfg, condition_id))


def iter_condition(cfg: dict, condition_id: int = 0) -> Iterator[dict]:
    n_mc = int(cfg["montecarlo"]["n_mc"])
    for trial_id in range(n_mc):
        yield run_single_trial(cfg, condition_id, trial_id)
