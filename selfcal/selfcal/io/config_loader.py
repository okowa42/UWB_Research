"""config/default.yaml の読込と軽量スキーマ検証。

未知キー・単位漏れ(想定キーの欠落)を早期に弾く。単位はすべて mm/deg/s。
実験ごとの上書きは experiments.py が差分辞書を deep-merge して行う。
"""
from __future__ import annotations

import copy
import pathlib
from typing import Any, Mapping

import yaml

# パッケージ同梱の既定 config
_DEFAULT_PATH = pathlib.Path(__file__).resolve().parents[2] / "config" / "default.yaml"

# 想定スキーマ: section -> 必須キー集合。ここに無いトップレベルキーは弾く。
_SCHEMA: dict[str, set[str]] = {
    "deployment": {
        "n_anchors", "pattern", "area_mm", "z_nominal_mm",
        "sigma_deploy_mm", "sigma_v_mm", "height_pattern", "unknown_z_spec",
    },
    "known": {"k_known", "known_idx", "known_z_mm"},
    "ranging": {
        "r_max_mm", "sigma_r_mm", "averaging_m", "sigma_r_range_dependent",
    },
    "calibration": {
        "gauge", "dof", "estimator", "lm_method", "max_nfev", "ftol", "xtol",
    },
    "tag_positioning": {
        "enabled", "grid_span_mm", "grid_step_mm", "grid_z_mm",
    },
    "montecarlo": {"n_mc", "seed"},
    "metrics": {"coverage_level", "epsilon_thr_mm"},
    "tbd": {"p_nlos", "mu_nlos_mm", "b_r_mm"},
}


class ConfigError(ValueError):
    """config スキーマ違反。"""


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """override を base に再帰的に重ねた新しい dict を返す(破壊しない)。"""
    out = copy.deepcopy(dict(base))
    for key, val in override.items():
        if (
            key in out
            and isinstance(out[key], Mapping)
            and isinstance(val, Mapping)
        ):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def validate(cfg: Mapping[str, Any]) -> None:
    """スキーマ検証。未知トップキー・未知サブキー・必須欠落を弾く。"""
    unknown_top = set(cfg) - set(_SCHEMA)
    if unknown_top:
        raise ConfigError(f"未知のトップレベルキー: {sorted(unknown_top)}")
    for section, allowed in _SCHEMA.items():
        if section not in cfg:
            raise ConfigError(f"必須セクション欠落: {section!r}")
        sub = cfg[section]
        if not isinstance(sub, Mapping):
            raise ConfigError(f"セクション {section!r} は mapping である必要がある")
        unknown = set(sub) - allowed
        if unknown:
            raise ConfigError(f"{section!r} に未知キー: {sorted(unknown)}")
        missing = allowed - set(sub)
        if missing:
            raise ConfigError(f"{section!r} に必須キー欠落: {sorted(missing)}")

    # 既知アンカーの整合(k_known == len(known_idx) == len(known_z_mm))
    k = cfg["known"]
    if not (len(k["known_idx"]) == len(k["known_z_mm"]) == k["k_known"]):
        raise ConfigError(
            "known: k_known / known_idx / known_z_mm の長さが不一致"
        )


def load_config(
    path: str | pathlib.Path | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """config を読み込み(overrides を deep-merge し)検証して返す。"""
    path = pathlib.Path(path) if path is not None else _DEFAULT_PATH
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ConfigError(f"config が mapping でない: {path}")
    if overrides:
        cfg = deep_merge(cfg, overrides)
    validate(cfg)
    return cfg
