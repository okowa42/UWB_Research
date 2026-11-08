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

# E2c: 未知アンカー(N_a-k 台)の意図高さパターン(依頼 E2c §2, 仕様 v1.2 §6)。
# 既知4台の高さは §4.4 規定(1,500×3 + 2,900)のまま固定し、未知アンカーの
# 高さ分散だけを振って「実現可能域内の複数台高さ分散で鉛直精度が実用域に届くか」を検証する。
# levels は index 順に巡回割当、uniform は試行毎に一様乱数で引き直す。
# 高さは実現可能域(着陸機構体 400〜2,900mm、H4 のみ上限5,000mm 感度確認)に収める。
HEIGHT_PATTERNS = [
    ("H0", {"levels": [1500.0]}),                       # 全台 1,500mm(基準・E1 相当)
    ("H1", {"levels": [400.0, 2900.0]}),                # 2水準交互
    ("H2", {"levels": [400.0, 1650.0, 2900.0, 1650.0]}),  # 3水準層化(4台例: 400/1650/2900/1650)
    ("H3", {"uniform": [400.0, 2900.0]}),               # 一様ランダム(実現可能域)
    ("H4", {"uniform": [400.0, 5000.0]}),               # 一様ランダム(上限拡張・参考)
]

# 追補⑤(2026-09-15, Cowork 回答 260915): 仰角スイープの空白区間を埋める。
# 7月版は 5,000 の次が 10,000mm で、8台全体の高さ std 1.16〜2.81m に測定点が無かった。
# 既存 CSV に足さず別 CSV とし、基準の 1.5/5/10m も同一実行に含める(再実行で個別試行値が変わるため)。
# 5,000mm 超は実現可能域(〜2,900mm)の外で、低下の開始点を特定するための参考条件。
HEIGHT_GAP_SWEEP = [1500.0, 5000.0, 6000.0, 7000.0, 8000.0, 9000.0, 10000.0]

# E2c 外挿検証: 「高さ std の総量だけで決まる」法則は std≤1.15m でしか確かめていない。
# H5 は未知4台を {5000,5000,5000,400} に置き、8台全体 std=1.78m の複数台分散点を作る
# (実現可能域の外・運用案ではない)。同一実行の基準として H0 を含める。
HEIGHT_PATTERNS_EXTRAP = [
    ("H0", {"levels": [1500.0]}),
    ("H5", {"levels": [5000.0, 5000.0, 5000.0, 400.0]}),
]

# E4(2026-11-08 依頼 261108): 配置範囲 L_site の縮小。水平は相似縮小(アンカー perimeter と
# タググリッドを L に比例)、鉛直は固定(既知 1500×3+2900, 未知 1500 = E2c H0 相当)。
# σ_deploy は L に比例させない。100,000mm は同一実行の基準。
AREA_SWEEP = [100000.0, 50000.0, 25000.0, 12500.0]
# タグ格子間隔 = L/20(100,000mm で既定 5,000mm = 21×21×2 = 882 点を全水準で維持)。
TAG_GRID_DIVISIONS = 20
# 共通乱数: E4 の全水準で試行 i の乱数列を同一にする(対応のある比較)。
# 条件番号 0 の乱数列を使うので、L=100,000mm は E2c H0(条件番号0)と同じ乱数列になる。
E4_RNG_CONDITION_ID = 0
# タグ高さ: config 既定は {0, 2000}(E2c・中間発表の数値はこちら)だが、仕様書 §4.5 の公称は
# {0, 1000}。食い違いが判明したため(2026-11-08)両方を実行する。アンカー側の結果は
# タグの乱数より前に決まるので両者で同一になる。
TAG_Z_SPEC_MM = [0.0, 1000.0]

# E6(2026-11-08 依頼「高所アンカーとタグ合格率」): 高所アンカー1台の高さ z_high を振る。
# 2系列: K = 既知アンカー1台(known_idx[3], 座標 (+L/2, 0)。E2_height と同じ台)を上げる。
#        U = 未知アンカー1台を上げる。K と水平位置の条件を揃えるため、K と y 軸対称な辺の中点
#            index 7 (−L/2, 0) を選ぶ(先頭の未知 index 4 は角 (+L/2,+L/2) で水平位置が交絡する)。
#            他は E4/E2c H0 と同じ(既知 1500×3+2900、残りの未知3台 1500)。
# 共通乱数(rng_condition_id=0)で全10条件の試行 i の乱数列を同一にする。U1500 は E2c H0 と同一条件。
HIGH_Z_SWEEP = [1500.0, 5000.0, 10000.0, 20000.0, 40000.0]
E6_U_HIGH_INDEX = 7
# 多スタート一意性検査(§5 確認事項3)。resid_tol_mm=10 は σ_r=100mm・28 辺・rms 残差 ≈70mm のとき
# Δχ² ≈ 4(残差二乗和の差で 2σ 相当)に当たる。これより残差の差が小さい別解は「データで区別できない」とみなす。
E6_UNIQUENESS = {"n_starts": 12, "perturb_mm": 500.0, "resid_tol_mm": 10.0, "cluster_tol_mm": 10.0}

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


def e3_2d_calibration(base_cfg: Mapping[str, Any]) -> list[tuple[dict, int]]:
    """E3: 2D校正モード(dof=2, Nüchter流のz固定平面校正)の骨組み(§6, Phase C)。

    全アンカーの z を意図値に固定し x,y のみ推定する。近共面配置では 3D 校正が鉛直に
    破綻する一方、2D 校正は水平形状を安定に復元する(V-8 の主張)。第一版は公称1条件。
    """
    return [(deep_merge(base_cfg, {"calibration": {"dof": 2}}), 0)]


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


def e2_height_gap(base_cfg):
    """追補⑤: 仰角スイープの空白区間(8台全体 std 1.16〜2.81m)を埋める単一台昇降。"""
    known_z_lists = [[1500.0, 1500.0, 1500.0, z] for z in HEIGHT_GAP_SWEEP]
    return ofat(_sweep_base(base_cfg), "known", "known_z_mm", known_z_lists)


def _height_pattern_conditions(base_cfg, patterns):
    """高さパターン列を1条件ずつ展開。condition_id は 0..len(patterns)-1。"""
    conditions: list[tuple[dict, int]] = []
    for cid, (label, spec) in enumerate(patterns):
        cfg = deep_merge(
            dict(base_cfg),
            {"deployment": {"height_pattern": label, "unknown_z_spec": spec}},
        )
        conditions.append((cfg, cid))
    return conditions


def e2c_height_patterns(base_cfg):
    """E2c: 未知アンカーの高さ分散パターン H0〜H4 を1条件ずつ展開(依頼 E2c)。

    タグ側 C(200mm)・VDOP を答えたい問い(§2)に含むためタグ測位は ON のまま
    (_sweep_base を通さない)。各パターンは height_pattern ラベルと unknown_z_spec を
    deployment に注入する。condition_id は 0..len(HEIGHT_PATTERNS)-1。
    """
    return _height_pattern_conditions(base_cfg, HEIGHT_PATTERNS)


def e2c_extrap(base_cfg):
    """E2c 外挿検証: H5(std 1.78m)が単一台昇降の曲線に乗るか(参考条件, 追補⑤)。

    E2c と揃えてタグ測位は ON。condition_id は H0=0, H5=1。
    """
    return _height_pattern_conditions(base_cfg, HEIGHT_PATTERNS_EXTRAP)


def _area_conditions(base_cfg, tag_z_mm=None):
    """E4: L_site を AREA_SWEEP で振る。condition_id は 0..3、乱数列は全水準共通。"""
    conditions: list[tuple[dict, int]] = []
    for cid, L in enumerate(AREA_SWEEP):
        tp = {
            "enabled": True,
            "grid_span_mm": L,
            "grid_step_mm": L / TAG_GRID_DIVISIONS,
        }
        if tag_z_mm is not None:
            tp["grid_z_mm"] = list(tag_z_mm)
        cfg = deep_merge(
            dict(base_cfg),
            {
                "deployment": {"area_mm": L},
                "tag_positioning": tp,
                # pipeline が読む任意キー(既定 config には置かない)。
                "montecarlo": {"rng_condition_id": E4_RNG_CONDITION_ID},
            },
        )
        conditions.append((cfg, cid))
    return conditions


def e4_area(base_cfg):
    """E4: 配置範囲の縮小(タグ高さは config 既定 = E2c と同条件)。"""
    return _area_conditions(base_cfg)


def e4_area_tagz1000(base_cfg):
    """E4: 同上、タグ高さだけ仕様書 §4.5 公称 {0, 1000}mm。"""
    return _area_conditions(base_cfg, TAG_Z_SPEC_MM)


def e5_e2c_rerun(base_cfg):
    """E5 用: E2c H0〜H3 を同じ乱数列(条件番号 0〜3)で取り直し、評価点ごとの誤差を残す。

    既存の E2c CSV には評価点ごとの誤差が無く、C(500mm) と定義(a)が出せないため。
    """
    return _height_pattern_conditions(base_cfg, HEIGHT_PATTERNS[:4])


def e6_high_anchor(base_cfg):
    """E6: 高所アンカー1台(K: 既知 / U: 未知)の高さを振り、タグ C(ε) を記録する。

    condition_id は K の5水準(0..4)→ U の5水準(5..9)。タグ測位 ON、一意性検査 ON。
    """
    known_idx = list(base_cfg["known"]["known_idx"])
    n = int(base_cfg["deployment"]["n_anchors"])
    unknown = [i for i in range(n) if i not in set(known_idx)]
    u_pos = unknown.index(E6_U_HIGH_INDEX)   # levels は未知アンカーへ index 順に巡回割当
    conditions: list[tuple[dict, int]] = []
    cid = 0
    for series in ("K", "U"):
        for z in HIGH_Z_SWEEP:
            label = f"{series}{int(z)}"
            mc = {
                "rng_condition_id": E4_RNG_CONDITION_ID,
                "uniqueness_check": dict(E6_UNIQUENESS),
                "record_labels": {"e6_series": series, "z_high_mm": z},
            }
            if series == "K":
                over = {
                    "known": {"known_z_mm": [1500.0, 1500.0, 1500.0, z]},
                    "deployment": {"height_pattern": label},
                }
            else:
                levels = [1500.0] * len(unknown)
                levels[u_pos] = z
                over = {"deployment": {"height_pattern": label,
                                       "unknown_z_spec": {"levels": levels}}}
            over["tag_positioning"] = {"enabled": True}
            over["montecarlo"] = mc
            conditions.append((deep_merge(dict(base_cfg), over), cid))
            cid += 1
    return conditions


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
    "E3": e3_2d_calibration,
    "E2_sigma_r": e2_sigma_r,
    "E2_sigma_v": e2_sigma_v,
    "E2_sigma_deploy": e2_sigma_deploy,
    "E2_n_anchors": e2_n_anchors,
    "E2_r_max": e2_r_max,
    "E2_height_diversity": e2_height_diversity,
    "E2_grid": e2_grid_precision,        # 精度破綻(coverage)
    "E2_grid_rigidity": e2_grid_rigidity,  # 剛性破綻(rigidity_ok)
    "E2c": e2c_height_patterns,          # 未知アンカー高さ分散パターン(H0〜H4)
    "E2_height_gap": e2_height_gap,      # 追補⑤: 仰角スイープの空白区間
    "E2c_extrap": e2c_extrap,            # 追補⑤: H5 による総量則の外挿検証(参考条件)
    "E4": e4_area,                       # 配置範囲の縮小(タグ z = config 既定)
    "E4_tagz1000": e4_area_tagz1000,     # 同上、タグ z = 仕様書公称 {0,1000}
    "E5_E2c": e5_e2c_rerun,              # E2c H0〜H3 の取り直し(評価点ごとの誤差を保存)
    "E6": e6_high_anchor,                # 高所アンカー1台(K/U)とタグ合格率
}


def build_conditions(
    exp_id: str, base_cfg: Mapping[str, Any]
) -> list[tuple[dict, int]]:
    if exp_id not in EXPERIMENTS:
        raise KeyError(
            f"未知の実験ID: {exp_id!r}(利用可能: {sorted(EXPERIMENTS)})"
        )
    return EXPERIMENTS[exp_id](base_cfg)
