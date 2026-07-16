"""E0-E3 の条件展開(§6)。

- E1: 公称1条件(ベースケース, Phase A)。
- E2: 感度スイープ(Phase B)。OFAT(1軸感度曲線)と 2軸グリッド(破綻領域ヒートマップ)。

各実験は (config, condition_id) のリストを返す。E2 スイープはアンカー自己校正と
剛性の感度を見るのが目的でタグ測位を要さないため、既定でタグ測位を無効化して高速化する
(PDOP 過信度を含めたい場合は run_experiment.py 側で上書きする)。

破綻領域マップ(追補①)は破綻の種類で2実験に分ける:
- E2_grid(精度破綻): σ_deploy×σ_r。破綻=C(200mm)<95%。coverage 取得のためタグ測位 ON。
- E2_grid_rigidity(剛性破綻): N_a×R_max。破綻=rigidity_ok=False。タグ測位 OFF。
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

from .io.config_loader import deep_merge

# E2 スイープ既定値(仕様書 v1.1 §5-A/§5-B に準拠)。
SIGMA_R_SWEEP = [30.0, 80.0, 130.0, 180.0, 230.0, 280.0]
SIGMA_V_SWEEP = [50.0, 150.0, 300.0]              # v1.1 公称150 を含む
# σ_deploy: 精度破綻(coverage<95%)の境界確認のため 10,000mm まで上方向に拡大(追補①)。
SIGMA_DEPLOY_SWEEP = [100.0, 300.0, 1000.0, 3000.0, 10000.0]
# N_a: 仕様 §5 の全水準 {4,5,6,8,9,10,12,16} を網羅(追補④, 5/10/16 を補完)。
N_ANCHORS_SWEEP = [4, 5, 6, 8, 9, 10, 12, 16]
R_MAX_SWEEP = [80000.0, 100000.0, 120000.0, 150000.0]
# 高さ多様性: 既知1台(index 3)の仰角を上げ、残り3台は z=1500 に固定。
# 「高さ多様性=3D自己校正の成立条件」(V-8 の主張)を鉛直RMSEで定量化する。
# 実現可能域(着陸機構体上部 〜2,900mm 想定)を 500mm 刻みで細分化し(追補③)、
# {10,000, 40,000} は実現性の弱い理論上限の参考点として残す。
HEIGHT_DIVERSITY_SWEEP = [
    1500.0, 2000.0, 2500.0, 3000.0, 3500.0, 4000.0, 4500.0, 5000.0,
    10000.0, 40000.0,  # 参考点(実現性が弱い理論上限)
]

# --- 破綻領域マップ専用スイープ(追補①) ---
# 剛性破綻(rigidity_ok=False): N_a を絞り R_max を 23,000mm 側へ下げると欠測が
# 増え自由アンカーの剛性が割れる。N_a=4 は既知4台と一致し自由アンカー0=退化のため
# 剛性は自明に充足する(破綻は N_a>=5 の自由アンカー領域で現れる)。
N_ANCHORS_RIGIDITY_SWEEP = [5, 6, 8, 10, 12]
R_MAX_RIGIDITY_SWEEP = [23000.0, 40000.0, 70000.0, 110000.0, 150000.0]

# スイープは校正・剛性の感度が対象。タグ測位を切って計算負荷を落とす。
_SWEEP_BASE = {"tag_positioning": {"enabled": False}}


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


def grid2(
    base_cfg: Mapping[str, Any],
    sec1: str, key1: str, vals1: list[Any],
    sec2: str, key2: str, vals2: list[Any],
) -> list[tuple[dict, int]]:
    """2軸グリッド: (key1×key2) の直積を条件列に展開(ヒートマップ用)。

    condition_id は行優先(key1 が外側)で 0..len(vals1)*len(vals2)-1 を割り振る。
    振った2軸の実値は行 dict の該当列に記録されるので集計時に pivot できる。
    """
    conditions: list[tuple[dict, int]] = []
    cid = 0
    for v1 in vals1:
        for v2 in vals2:
            cfg = deep_merge(base_cfg, {sec1: {key1: v1}, sec2: {key2: v2}})
            conditions.append((cfg, cid))
            cid += 1
    return conditions


def _sweep_base(base_cfg: Mapping[str, Any]) -> dict:
    return deep_merge(base_cfg, _SWEEP_BASE)


# --- E2 感度曲線(OFAT) ---
def e2_sigma_r(base_cfg):   # V-4 の感度曲線
    return ofat(_sweep_base(base_cfg), "ranging", "sigma_r_mm", SIGMA_R_SWEEP)


def e2_sigma_v(base_cfg):
    return ofat(_sweep_base(base_cfg), "deployment", "sigma_v_mm", SIGMA_V_SWEEP)


def e2_sigma_deploy(base_cfg):
    return ofat(_sweep_base(base_cfg), "deployment", "sigma_deploy_mm", SIGMA_DEPLOY_SWEEP)


def e2_n_anchors(base_cfg):
    return ofat(_sweep_base(base_cfg), "deployment", "n_anchors", N_ANCHORS_SWEEP)


def e2_r_max(base_cfg):
    return ofat(_sweep_base(base_cfg), "ranging", "r_max_mm", R_MAX_SWEEP)


def e2_height_diversity(base_cfg):
    """既知アンカー1台の仰角スイープ。鉛直自己校正の成立条件を定量化。"""
    known_z_lists = [[1500.0, 1500.0, 1500.0, z] for z in HEIGHT_DIVERSITY_SWEEP]
    return ofat(_sweep_base(base_cfg), "known", "known_z_mm", known_z_lists)


# --- E2 破綻領域マップ(2軸グリッド, 追補①: 2種の破綻を区別) ---
def e2_grid_precision(base_cfg):
    """精度破綻マップ: σ_deploy × σ_r。

    破綻定義はカバレッジ率 C(200mm) < 95%。coverage はタグ測位から得るため、
    このグリッドだけタグ測位を有効のままにする(_sweep_base を通さない)。
    """
    return grid2(
        dict(base_cfg),
        "deployment", "sigma_deploy_mm", SIGMA_DEPLOY_SWEEP,
        "ranging", "sigma_r_mm", SIGMA_R_SWEEP,
    )


def e2_grid_rigidity(base_cfg):
    """剛性破綻マップ: N_a × R_max。

    破綻定義は rigidity_ok=False(校正不能)。N_a を絞り R_max を 23,000mm 側へ
    下げると欠測が増え自由アンカーの剛性が割れる。coverage は不要なのでタグ測位は切る。
    """
    return grid2(
        _sweep_base(base_cfg),
        "deployment", "n_anchors", N_ANCHORS_RIGIDITY_SWEEP,
        "ranging", "r_max_mm", R_MAX_RIGIDITY_SWEEP,
    )


# 実験レジストリ。
EXPERIMENTS: dict[str, Callable[[Mapping[str, Any]], list[tuple[dict, int]]]] = {
    "E1": e1_base,
    "E2_sigma_r": e2_sigma_r,
    "E2_sigma_v": e2_sigma_v,
    "E2_sigma_deploy": e2_sigma_deploy,
    "E2_n_anchors": e2_n_anchors,
    "E2_r_max": e2_r_max,
    "E2_height_diversity": e2_height_diversity,
    "E2_grid": e2_grid_precision,        # 精度破綻(coverage)
    "E2_grid_rigidity": e2_grid_rigidity,  # 剛性破綻(rigidity_ok)
}


def build_conditions(
    exp_id: str, base_cfg: Mapping[str, Any]
) -> list[tuple[dict, int]]:
    if exp_id not in EXPERIMENTS:
        raise KeyError(
            f"未知の実験ID: {exp_id!r}(利用可能: {sorted(EXPERIMENTS)})"
        )
    return EXPERIMENTS[exp_id](base_cfg)
