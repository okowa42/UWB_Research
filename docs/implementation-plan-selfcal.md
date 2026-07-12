<!--
実装計画書（案B: 月面UWB自己校正シミュレーション）
出典依頼: Claude用参考資料/ClaudeCode実装依頼_260713.md
準拠仕様: Claude用参考資料/シミュ設計仕様書_月面UWB自己校正_260713.md v1.0
本書は「どう実装するか」の提案。灯の承認後に着手する。未着手（コード未変更）。
-->
---
version: 0.1 (灯レビュー待ち)
date: 2026-07-13
author: Claude Code (WSL, ~/UWB_Research)
status: 提案 — 承認後に Phase A から着手
---

# 実装計画 — 月面UWBアンカー自己校正シミュレーション（案B）

## 0. スコープ確認
- 本書は**実装計画のみ**。コードは未着手。承認後 Phase A→B→C（仕様書§6）で実装する。
- 準拠の正本は仕様書 v1.0。数値・受け入れ基準はそれに従う。矛盾は §9 に列挙し、実装前に潰したい。

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
- **TBDプレースホルダは config の1エントリに集約**し、確定時に値の差し替えだけで済ませる: `p_nlos: 0.0`, `mu_nlos_mm: 3800`, `b_r_mm: 0`, `epsilon_thr_mm: 200`, `coverage_level: 0.95`, `k_known: 4`。コード分岐は増やさない。
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
                  known_idx: Sequence[int],       # 固定する既知アンカーindex(G1)
                  rng: np.random.Generator) -> CalibrationResult: ...
```
- 第一実装 `LMEstimator`（`scipy.optimize.least_squares`, method は G2 のランク落ち耐性から **`trf`** を第一候補、`lm` は比較用）。
- T-008 の結論で PF 等を足す際は、同じ `Estimator` プロトコルを実装するだけで `pipeline.py` を変更しない。

## 5. パイプライン各段の実装方針（要点）
- **A 展開 (`deployment.py`)**: patterns移植で意図配置生成 → §4.2 の**水平/鉛直分離ガウス** `diag(σ_deploy², σ_deploy², σ_v²)` を `Generator` で付加。既知アンカーには誤差を与えない。
- **B 測距 (`ranging.py`)**: R_max以内の全ペアに `d + b_r + N(0,σ_r²)`、`d>R_max`はNaN。NLOSは `p_NLOS` 枠のみ実装（公称0）。`m回平均`オプション（実効σ_r/√m）。
- **C 自己校正 (`calibration/`)**: 初期値=意図配置。既知アンカー固定。剛性チェック→ランク不足なら「校正不能」フラグを立てて**集計には残す**（破綻領域の情報）。
- **D タグ測位 (`tag_positioning.py`)**: タググリッド各点で、推定アンカー座標＋σ_rノイズ→`pdop.trilateration`。可視アンカー<4は「測位不能」。**同一ノイズ実現で真アンカー版も計算**しΔRMSEを分離（§4.5）。
- **E 集計 (`metrics.py`)**: RMSE_anchor_abs/shape, RMSE_tag, ΔRMSE_tag, PDOP_true/est, PDOP過信度, カバレッジ率C(ε_thr), 収束率, 計算時間。

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
- V-6 が RNG設計の要。全乱数を `rng.py` の Generator 経由に統一（グローバル `np.random` 禁止）。

## 7. 実装順序と完了判定
| Phase | 内容 | 完了判定 |
|---|---|---|
| **A** | `selfcal/` 骨組み・config・A〜E単体・LM推定器・E0/E1が回る | V-1〜V-3,V-6,V-7 が緑。E1ベースケースのCSVが出る |
| **B** | スイープ(experiments)・集計・E2a感度曲線・E2bヒートマップ・profiler | V-4,V-5 が緑。E2の破綻領域マップ図が出る。**STEP1移植の完了を兼ねる** |
| **C** | E3(Nüchter対応,骨組み)・多スタート一意性検査・(T-008次第)推定器比較 | E3スケルトンが回る。多スタートで一意性破れを検出 |

## 8. 実装フェーズのモデル運用方針（Opus/Sonnet分担案）
指示役（本オーケストレータ）が設計・レビュー・統合を担い、実装を以下で分担する:
- **Opus 担当（アルゴリズムの核・誤ると全体が狂う所）**: 自己校正LM（ゲージ不定性・trf設定）、剛性行列構成とランク判定、Procrustes整列、誤差伝搬の分離評価ロジック。
- **Sonnet 担当（仕様が明確で定型な所）**: patterns移植（m→mm）、config_loader/exporters移植、CSV長形式出力、テストの雛形、感度曲線・ヒートマップ描画スクリプト。
- 各担当の成果は指示役が仕様書§10と照合してレビューし、diffを灯に提示してから適用。

## 9. 仕様書への疑問・矛盾・要確認事項
実装前に潰したい点。**[重]=設計を左右／[軽]=記載明確化で足りる**。

### 9.1 モデルの物理的妥当性
- **[重] σ_v=50mm は鉛直誤差を過小評価の疑い**（Sonnet指摘・調査③）。レゴリスへの沈み込み・バウンド（σ_env, 数百mmオーダー）は水平より鉛直に効きやすいが、σ_v は σ_mech(10〜50mm) のみ基準。高さ多様性/VDOP評価が σ_v を固定前提にしているため、値の妥当性を確認したい（σ_env の鉛直寄与を σ_v に含めるか、別項にするか）。
- **[軽] R_max=200,000mm でパスロス遷移(≈180,000mm, 1/R²→1/R⁴; 調査②)を超える**。現モデルは R_max 超を単純欠測にするのみで、レンジ依存の測距劣化(σ_r増大)を持たない。200m水準は「完全グラフ化の代表」との位置づけ(§8)だが、遷移超で σ_r 一定は楽観的。距離依存σ_rは範囲外で良いか確認。
- **[軽] B_rsl（信号強度依存バイアス, 数百mm; 調査②）が b_r(定数)にもNLOSにも対応付かない**。第一版 LOS では無視で良いか。

### 9.2 パラメータ選定
- **[軽] ベースケース E1 の N_a=8 が推奨下限9(調査③④)を下回る**（Sonnet指摘）。基準点をあえて下限未満に置く意図の確認（破綻を見やすくするため？）。
- **[軽] σ_r 公称100mm の選定根拠が §8 に無い**（範囲30〜280の採否のみ裁定）。公称値の出所を明記したい。

### 9.3 アルゴリズム仕様の欠落（独自決定が必要な箇所）
- **[重] G1 の剛性ランク条件が未定義**（「既知点の分だけ条件が変わる」のみ）。実装では `rank(R_free)=3·N_free`（既知点でピン留めのため −6 不要、と推測）で決め打ちする予定。この解釈で良いか。
- **[重] G2 のゲージ不定性への数値的対処が未指定**（Sonnet指摘・調査④）。ヤコビアンが並進3+回転3+鏡映で特異になり、素の LM(`method='lm'`)はランク落ちに弱い。`trf`＋擬似逆行列/ゲージ拘束付与で対処する方針で良いか（§4のI/Fはこれを吸収可能に設計済み）。
- **[軽] 多スタートの反復回数目安（調査①: 平均誤差<500mm→16回, <1000mm→64回）を Phase C の既定値に採用して良いか。**
- **[軽] 剛性行列 R(G,p) の構成法・Procrustes は NotebookLM に裏付けが無く標準理論からの独自実装**（Sonnet指摘）。実装後に単体テスト（V-3,V-5）で妥当性を担保する方針で良いか。

### 9.4 運用（実装外だが重要）
- **[重] OneDrive パス変更**: ミラー先が `OneDrive/...` から `OneDrive - Chiba Institute of Technology/...` に変わった。CLAUDE.md・rules/cowork-sync.md・保留中フェーズ5フックの旧パスが全て無効。**別途パス更新を提案する**（本計画とは独立の保守作業）。

## 10. 見積り（粗）
- Phase A: 中規模（新規アルゴリズム核＋テスト）。Phase B: 小〜中（既存資産移植中心）。Phase C: 中（一意性検査・比較）。
- 計算負荷の懸念: タググリッド(100m/5m間隔×2高さ≒882点) × N_mc=100 × 多数条件。ただし自己校正(重)は試行あたり1回、タグ測位(軽)は線形。Phase B で profiler により実測してから条件数を確定する。
