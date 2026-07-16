# selfcal — 月面UWBアンカー自己校正シミュレーション(案B)

ヘッドレス・バッチ評価パッケージ。`pdop.simulation.geometry` の純粋関数のみを
単方向依存で再利用し、pdop 本体は変更しない。準拠仕様は
`docs/implementation-plan-selfcal.md`(仕様書 v1.1)。単位はすべて mm/deg/s。

## セットアップ
```bash
python3 -m venv selfcal/.venv
selfcal/.venv/bin/pip install numpy scipy pyyaml pytest matplotlib
# matplotlib は図生成(scripts/make_figures.py)のみで使用。ドメイン層は非依存。
```

## 実行
```bash
cd selfcal
# 受け入れ基準テスト(E0: V-1〜V-8)
.venv/bin/python -m pytest tests/ -q
# E1 ベースケース(CSV 出力)
.venv/bin/python scripts/run_experiment.py --exp E1 --out results/e1_base.csv
# E2 感度スイープ(EXPERIMENTS: E2_sigma_r/_v/_deploy/_n_anchors/_r_max/_height_diversity/_grid)
.venv/bin/python scripts/run_experiment.py --exp E2_sigma_r --out results/e2_sigma_r.csv
.venv/bin/python scripts/run_experiment.py --exp E2_grid    --out results/e2_grid.csv
# 高さ多様性スイープ(鉛直自己校正の成立条件を定量化)
.venv/bin/python scripts/run_experiment.py --exp E2_height_diversity --out results/e2_height.csv
# 図(スイープ軸を自動判定: 1軸→感度曲線 / 2軸→破綻領域ヒートマップ)
.venv/bin/python scripts/make_figures.py --csv results/e2_sigma_r.csv --out results/e2_sigma_r.png
.venv/bin/python scripts/make_figures.py --csv results/e2_grid.csv    --out results/e2_grid.png
.venv/bin/python scripts/make_figures.py --csv results/e2_height.csv  --out results/e2_height_v.png --metric rmse_anchor_shape_v_mm
```

## パイプライン(A→E, §5)
| 段 | モジュール | 内容 |
|---|---|---|
| A | `deployment.py` | 意図配置 + 水平/鉛直分離ガウス展開誤差。既知アンカーは非共面固定 |
| B | `ranging.py` | アンカー間 TWR 測距(欠測=NaN, b_r/NLOS 枠, m回平均) |
| C | `calibration/`, `rigidity.py` | LM(trf) 自己校正。G1既知固定/G2規約固定, dof=3/2。剛性ランク+最小特異値 |
| D | `tag_positioning.py` | 推定/真アンカーでタグ測位(同一ノイズ, ΔRMSE 分離) |
| E | `metrics.py`, `alignment.py` | RMSE(H/V分解), Procrustes整列, PDOP過信度, カバレッジ |

## 現状(Phase B 完了)
- **E0 全緑**: V-1〜V-8(V-4 単調性・V-5 Procrustes 不変式を追加, `pytest` 9 passed)。
- **E2 感度スイープ実装済**: OFAT(σ_r/σ_v/σ_deploy/N_a/R_max/high_diversity)＋2軸グリッド(σ_deploy×σ_r)。
  `make_figures.py` が感度曲線・破綻領域ヒートマップを自動判定して描画。profiler は
  `run_experiment.py` が試行あたり計算時間(median/max/total)を出力＋`compute_time_s` 列。
- **所見1(裏取り済)**: E1 公称配置(8台中7台が z=1500 平面, 既知1台のみ z=2900)は鉛直の
  自己校正が極めて弱い。N_mc=100 中央値で **shape RMSE 水平=55mm / 鉛直=1128mm**(abs は
  水平97/鉛直2001)。σ_r=0 で完全復元＝実装バグでなく near-coplanar 幾何の必然。
- **所見2(研究主張の定量化)**: 既知1台の仰角を 1500→40000mm へ上げると鉛直 shape RMSE が
  **1161→147mm(約8倍改善)**、水平は≈53mmで不変。剛性ランクは全域で充足したまま鉛直精度
  だけが単調改善 → 「高さ多様性=3D自己校正の成立条件」を定量的に支持(V-8 の主張の連続版)。
- Phase C: E3(Nüchter, 2D校正)・多スタート一意性検査。
