<!--
実装計画書（案B: 月面UWB自己校正シミュレーション）
出典依頼: Claude用参考資料/ClaudeCode実装依頼_260713.md
準拠仕様: Claude用参考資料/シミュ設計仕様書_月面UWB自己校正_260713.md v1.1
本書は「どう実装するか」の提案。未着手（コード未変更）。仕様 v1.1 で全要確認事項が裁定済みのため確定版。
-->
---
version: 1.0 (確定・v1.1準拠)
date: 2026-07-13
author: Claude Code (WSL, ~/UWB_Research)
status: 確定 — Phase A 着手可（灯の最終GOで開始）
---

# 実装計画 — 月面UWBアンカー自己校正シミュレーション（案B）

## 0. スコープ確認
- 本書は**実装計画**。コードは未着手。Phase A→B→C（仕様書§6）で実装する。
- 準拠の正本は仕様書 **v1.1**。数値・受け入れ基準はそれに従う。
- v0.1 で挙げた要確認事項は **v1.1 で全件裁定済み**（対応表は §9）。設計を左右する未解決点は残っていない。

## 1. アーキテクチャ判断（依頼の3つの問いへの回答）

### 1.1 配置場所 → UWB_Research 直下に新規パッケージ `selfcal/`
- `pdop/` の**中には作らない**。pdop は PyQt5 GUI デスクトップアプリで、バッチ評価（ヘッドレス・大量試行）と混ぜると UI 依存が染み出し、CI/再現性が損なわれる。
- 新規ヘッドレスパッケージ `selfcal/`（名称は仮）を切り、`pdop.simulation.geometry` の純粋関数のみを依存として import する。
- **理由**: 依存方向を `selfcal/ → pdop/simulation/geometry`（単方向）に保つ。pdop 側は一切変更しない（回帰リスクゼロ、V-7 が自明に成立）。

### 1.2 既存 pdop との接続 → geometry の純粋関数を再利用、乱数は再利用しない
| 再利用する | 用途 | 注意 |
|---|---|---|
| `geometry.trilateration(anchors, distances)` | §4.5 D タグ測位 | 決定的。そのまま可 |
| `geometry.dop_components(...)` / `geometry_matrix` / `covariance_matrix` | §4.6 PDOP/HDOP/VDOP・**V-7回帰** | 決定的。そのまま可 |
| **再利用しない**: `geometry.euclidean_distances` | 測距ノイズ生成 | グローバル `np.random.normal` 使用 → **V-6（seed完全再現）と衝突**。測距は自前の `Generator` 注入版を新規実装 |

- UWB_Sim/3d の重複 DOP 実装（`metrics/gdop.py`）は**使わない**。V-7 が「pdop の出力と一致」を要求するため、単一の真実源（pdop）に統一する。

### 1.3 STEP1バッチ評価パイプライン移植との関係 → 統合（案Bが内包）
- **結論: STEP1移植を独立タスクとして別実行しない。案Bを先行し、その Phase B が STEP1バッチ基盤を内包する。**
- 根拠: STEP1の要素（3Dアンカーパターン生成・モンテカルロ・計算時間ベンチ・CSV/プロット集計）は、案B §6 の E2 スイープ基盤と**大部分重複**する。案Bはその上に「展開誤差＋自己校正」層を足したもの。別々に作ると sweep/集計/IO を二重実装する。
- 移植元 `~/UWB_Sim/3d` の資産（`scenario/patterns.py`, `simulation/runner.py` の MC構造, `io/` の config/export, `metrics/profiler.py`）は案B `selfcal/` の該当モジュールへ**移植して転用**する（単位 m→mm 変換を伴う）。
- ※これは依頼ヘッダ「STEP1移植より本件を先行するか」への回答＝**案Bを先行**。要・灯の承認。

## 2. モジュール分割案（`selfcal/`）

```
selfcal/
├── config/
│   └── default.yaml          # 全パラメータの正本（§5）。TBDはプレースホルダ値で記載
├── selfcal/                  # パッケージ本体
│   ├── geometry_bridge.py    # pdop.simulation.geometry への薄いアダプタ（import集約点）
│   ├── rng.py                # seed階層管理（実験→条件→試行, np.random.Generator）§3.2
│   ├── deployment.py         # A: 意図配置生成(patterns移植) + 展開誤差モデル §4.1/4.2
│   ├── ranging.py            # B: アンカー間TWR測距(欠測・bias・NLOS枠) §4.3
│   ├── rigidity.py           # 剛性行列構成・ランク検査 §4.4
│   ├── calibration/
│   │   ├── base.py           # 推定器I/F(抽象): CalibrationResult, Estimator §4.4/TBD-1
│   │   └── lm_estimator.py   # LM最小二乗(第一実装) §4.4
│   ├── alignment.py          # Procrustes整列(並進・回転・鏡映) §4.6 G2
│   ├── tag_positioning.py    # D: 推定アンカーでタグ測位(pdop流用) §4.5
│   ├── metrics.py            # E: RMSE/PDOP過信度/カバレッジ率 §4.6
│   ├── pipeline.py           # A→E を1試行実行する統括(run_single_trial)
│   ├── montecarlo.py         # 1条件=N_mc試行(runner.py移植) §2
│   ├── experiments.py        # E0-E3の条件展開(OFAT/2軸グリッド) §6
│   └── io/
│       ├── config_loader.py  # yaml読込(UWB_Sim移植)
│       └── exporters.py      # long-format CSV出力 §7
├── scripts/
│   ├── run_experiment.py     # 実験ID指定でバッチ実行
│   └── make_figures.py       # 感度曲線・ヒートマップ・PDOPマップ §7
└── tests/                    # V-1〜V-7 (pytest) §10
```

- ドメイン層（deployment〜metrics）は matplotlib/PyQt 非依存に保つ（テスト容易性）。可視化は scripts のみ。

## 3. パラメータ管理方式（§9 TBD差し替え対応）
- 全パラメータを `config/default.yaml` に外出し。**単位はすべて mm/deg/s**（キー名に単位サフィックス、例 `sigma_deploy_mm`）。
- 実験ごとの上書きは `experiments.py` が base config に差分辞書を重ねて条件を生成（OFAT・2軸グリッドを宣言的に定義）。
- **TBDプレースホルダは config の1エントリに集約**し、確定時に値の差し替えだけで済ませる（仕様§9 の TBD-1〜6 に対応）: `p_nlos: 0.0`, `mu_nlos_mm: 3800`, `b_r_mm: 0`, `epsilon_thr_mm: 200`, `coverage_level: 0.95`, `k_known: 4`, `sigma_r_range_dependent: false`(TBD-6)。コード分岐は増やさない。
- v1.1 で確定した公称値を base config に反映: `sigma_v_mm: 150`, `r_max_mm: 150000`, `z_nominal_mm: 1500`。既知アンカー高さは非共面（`known_z_mm: [1500,1500,1500,2900]`, §4.4/G1）。
- config はスキーマ検証（軽量）を1関数で行い、未知キー・単位漏れを早期に弾く。

## 4. 推定器インターフェース設計（TBD-1: PF後付け対応）
```python
# calibration/base.py（設計イメージ、単位mm）
@dataclass(frozen=True)
class CalibrationResult:
    anchor_positions_mm: np.ndarray   # (N,3) 推定アンカー座標
    residuals_mm: np.ndarray          # 測距残差
    iterations: int
    converged: bool
    rigidity_ok: bool                 # 剛性チェック結果 §4.4
    info: dict                        # 推定器固有の付随情報

class Estimator(Protocol):
    def calibrate(self,
                  dist_matrix_mm: np.ndarray,     # (N,N) 欠測はNaN
                  intended_xyz_mm: np.ndarray,    # 初期値=意図配置 §4.4
                  known_idx: Sequence[int],       # 固定する既知アンカーindex(G1)。空ならG2
                  gauge: str,                     # 'known'(G1) | 'convention'(G2規約固定)
                  dof: int,                       # 3=3D校正 / 2=z固定2D校正(E3, v1.1)
                  rng: np.random.Generator) -> CalibrationResult: ...
```
- 第一実装 `LMEstimator`（`scipy.optimize.least_squares`, method は共面付近のランク落ち耐性から **`trf`** を第一候補、`lm` は比較用）。仕様 v1.1 で `trf` に確定。
- **G2 のゲージ処理 = 規約固定**（v1.1 確定）: アンカー1を原点・2をx軸上(y=z=0)・3をxy平面内(z=0)に拘束して6自由度を消す。固定3点は非共線に選ぶ（perimeter なら角3点）。**Moore-Penrose 擬似逆による自由網調整は不採用**（scipy 既製がなく自前実装がバグ源のため）。規約固定点の誤差による座標系の歪みは、評価が Procrustes 整列後の形状誤差なので影響しない。
- **2D 校正モード（`dof=2`）**: 全アンカーの z を既知固定し水平2成分のみ推定。共面配置は 3D では原理的に校正不能（§4.4 注意2）のため E3 の Nüchter 退化ケースに使う。V-8 で検証。
- T-008 の結論で PF 等を足す際は、同じ `Estimator` プロトコルを実装するだけで `pipeline.py` を変更しない（TBD-1）。

## 5. パイプライン各段の実装方針（要点）
- **A 展開 (`deployment.py`)**: patterns移植で意図配置生成 → §4.2 の**水平/鉛直分離ガウス** `diag(σ_deploy², σ_deploy², σ_v²)` を `Generator` で付加。公称 σ_v=150mm、Phase B で {50,150,300} スイープ。既知アンカーには誤差を与えず、**非共面に配置（3台 z=1500mm・1台 z=2900mm, §4.4/G1）**——共面だと鏡映が固定できないため必須。
- **B 測距 (`ranging.py`)**: R_max（公称150,000mm）以内の全ペアに `d + b_r + N(0,σ_r²)`、`d>R_max`はNaN。NLOSは `p_NLOS` 枠のみ実装（公称0）。`m回平均`オプション（実効σ_r/√m）。σ_r は距離非依存（TBD-6: R_max≤150m の限り影響なし）。
- **C 自己校正 (`calibration/`+`rigidity.py`)**: 初期値=意図配置。ゲージは G1=既知点固定／G2=規約固定（§4）。**剛性チェックはモード別ランク条件**——G2: `rank(R)=3·N_a−6`、G1: 縮約行列 `rank(R_free)=3·N_free`（既知点ピン留めで−6不要、既知−既知エッジのゼロ行は除外）。**bool判定に加え最小特異値（or条件数）を必ず記録**（共面近傍の「ランクは足りるが悪条件」を捕捉）。ランク不足でも「校正不能」フラグを立て**集計に残す**（破綻領域の情報）。E3 は `dof=2` の2D校正モード。
- **D タグ測位 (`tag_positioning.py`)**: タググリッド各点で、推定アンカー座標＋σ_rノイズ→`pdop.trilateration`。可視アンカー<4は「測位不能」。**同一ノイズ実現で真アンカー版も計算**しΔRMSEを分離（§4.5）。
- **E 集計 (`metrics.py`)**: RMSE_anchor_abs/shape, RMSE_tag, ΔRMSE_tag, **水平/鉛直分解（RMSE_{anchor,tag}_{h,v}, v1.1追加）**, PDOP_true/est, PDOP過信度, カバレッジ率C(ε_thr), 収束率, 計算時間。共面近傍では鉛直のみ極端に劣化するため H/V 分解が必須。

## 6. テスト計画（V-1〜V-7 を pytest 自動化 = E0）
| ID | テスト内容 | 実装方針 |
|---|---|---|
| V-1 | σ_r=0,σ_deploy=0,完全グラフ→誤差<1e-6mm | 無雑音で恒等復元をassert |
| V-2 | σ_r=0,σ_deploy=1000,G1(k=4),完全グラフ→機械精度で真値復元 | 無雑音なら解=真値 |
| V-3 | 剛性不足(N_a=4,R_max絞る)→「校正不能」検出 | rigidity_ok=False を検証 |
| V-4 | σ_r 30→280 で RMSE 単調増加(N_mc=100中央値) | 統計的単調性 |
| V-5 | G2 Procrustes: 整列後RMSE_shape ≤ 整列前絶対RMSE | 全試行で成立をassert |
| V-6 | 同一seed再実行→CSV完全一致 | seed階層の再現性 |
| V-7 | 真値配置PDOP = pdop/ 出力と一致 | pdop.dop_components と直接比較(回帰) |
| V-8 | 共面配置(全アンカー同一高さ)を3D/2D両モードへ入力 | 3Dモード=剛性チェックが「校正不能」検出／2Dモード=σ_r=0で真値復元(V-2相当)。v1.1追加 |
- V-6 が RNG設計の要。全乱数を `rng.py` の Generator 経由に統一（グローバル `np.random` 禁止）。
- V-8 は「高さ多様性=3D自己校正の成立条件」という研究主張候補を担保する。`dof=2` モードと剛性チェックの両実装が Phase A で揃う必要がある。

## 7. 実装順序と完了判定
| Phase | 内容 | 完了判定 |
|---|---|---|
| **A** | `selfcal/` 骨組み・config・A〜E単体・LM推定器(trf)・2D校正モード・剛性チェック(モード別＋最小特異値)・E0/E1が回る | V-1〜V-3,V-6,V-7,**V-8** が緑。E1ベースケースのCSV（H/V分解列を含む）が出る |
| **B** | スイープ(experiments)・集計・E2a感度曲線・E2bヒートマップ・σ_v/σ_deploy/R_maxスイープ・profiler | V-4,V-5 が緑。E2の破綻領域マップ図が出る。**STEP1移植の完了を兼ねる** |
| **C** | E3(Nüchter対応,2D校正モードで実行,骨組み)・多スタート一意性検査・(T-008次第)推定器比較 | E3スケルトンが回る。多スタートで一意性破れ（鏡映等の離散不定性）を検出 |

## 8. 実装フェーズのモデル運用方針（Opus/Sonnet分担案）
指示役（本オーケストレータ）が設計・レビュー・統合を担い、実装を以下で分担する:
- **Opus 担当（アルゴリズムの核・誤ると全体が狂う所）**: 自己校正LM（ゲージ不定性・trf設定）、剛性行列構成とランク判定、Procrustes整列、誤差伝搬の分離評価ロジック。
- **Sonnet 担当（仕様が明確で定型な所）**: patterns移植（m→mm）、config_loader/exporters移植、CSV長形式出力、テストの雛形、感度曲線・ヒートマップ描画スクリプト。
- 各担当の成果は指示役が仕様書§10と照合してレビューし、diffを灯に提示してから適用。

## 9. v0.1 要確認事項の裁定結果（v1.1 で全件解決）

v0.1 で挙げた疑問・矛盾は仕様 v1.1 で全て裁定された。対応を以下に記録する（**設計を左右する未解決点は残っていない**）。

| v0.1 の指摘 | v1.1 の裁定 | 計画への反映 |
|---|---|---|
| [重] σ_v=50mm は過小評価の疑い | 公称 **150mm** に引き上げ＋Phase B で {50,150,300} スイープ。値は争わず感度で評価 | §5-A・config `sigma_v_mm:150` |
| [重] G1 剛性ランク条件が未定義 | **`rank(R_free)=3·N_free`**（−6不要）で確定＝推測どおり。既知−既知エッジのゼロ行は除外 | §5-C・`rigidity.py` |
| [重] G2 ゲージ不定性の数値処理が未指定 | **規約固定**（1=原点/2=x軸/3=xy平面）＋trf に確定。**擬似逆は不採用** | §4・§5-C |
| [軽] R_max=200m がパスロス遷移超で楽観的 | **150,000mm に変更**（対角141m超で完全グラフ代表、遷移180m未満で σ_r 一定と整合）。距離依存σ_rは TBD-6 | §5-B・config `r_max_mm:150000` |
| [軽] B_rsl が b_r/NLOS に対応付かない | b_r の感度枠 ±100mm に吸収（TBD-6）。第一版LOSは無視でよい | ranging の b_r 枠 |
| [軽] E1 の N_a=8 が推奨下限9未満 | 意図的。N_a に **9 を追加**したうえで E1 公称は 8 のまま（推奨下限との差自体が結果） | §5-B・N_a スイープ |
| [軽] σ_r 公称100mm の根拠不明 | DW1000 標準性能 ±100mm（調査②・信頼度A）と明記 | §8 で確定・記載のみ |
| [軽] 剛性/Procrustes が標準理論からの独自実装 | 単体テスト（V-3,V-5,**V-8**）で妥当性担保。Procrustes は `scipy.linalg.orthogonal_procrustes` 使用（独自実装しない） | §6・`alignment.py` |
| [軽] 多スタート反復回数（<500mm→16, <1000mm→64） | Phase C の既定値に採用 | §7 Phase C |

### 9.1 実装時に独自決定として残る点（仕様が委任・TBD 隔離済み）
- **TBD-5（k=3 の鏡映不定性）**: 公称 k=4 非共面で回避済み。k=3 モードは数値実験で鏡映解の残存を確認するのみ（ブロッカーでない）。
- **TBD-3（Nüchter 再現数値）**: E3 は骨組みのみ。原典座標・σ は灯＋Cowork の抽出待ち。実装は差し替え可能に。
- **鏡映＝離散的不定性はランク検査で検出不可**（仕様§4.4 注意1）。多スタートで経験的に検出する（Phase C）。剛性ランクは連続変形の必要条件であり大域一意性の十分条件でない点を、コメントに明記する。

### 9.2 運用（実装外・別作業として完了済み）
- **OneDrive パス変更**（`OneDrive/...`→`OneDrive - Chiba Institute of Technology/...`）は rules/cowork-sync.md・CLAUDE.md 側で対応済み（コミット 8152174）。本計画とは独立。

## 10. 見積り（粗）
- Phase A: 中規模（新規アルゴリズム核＋テスト）。Phase B: 小〜中（既存資産移植中心）。Phase C: 中（一意性検査・比較）。
- 計算負荷の懸念: タググリッド(100m/5m間隔×2高さ≒882点) × N_mc=100 × 多数条件。ただし自己校正(重)は試行あたり1回、タグ測位(軽)は線形。Phase B で profiler により実測してから条件数を確定する。
