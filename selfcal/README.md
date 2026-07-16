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
# E2 感度スイープ(experiments.EXPERIMENTS に登録: E2_sigma_r/_v/_deploy/_n_anchors/_r_max/_grid)
.venv/bin/python scripts/run_experiment.py --exp E2_sigma_r --out results/e2_sigma_r.csv
.venv/bin/python scripts/run_experiment.py --exp E2_grid    --out results/e2_grid.csv
# 図(スイープ軸を自動判定: 1軸→感度曲線 / 2軸→破綻領域ヒートマップ)
.venv/bin/python scripts/make_figures.py --csv results/e2_sigma_r.csv --out results/e2_sigma_r.png
.venv/bin/python scripts/make_figures.py --csv results/e2_grid.csv    --out results/e2_grid.png
```

## パイプライン(A→E, §5)
| 段 | モジュール | 内容 |
|---|---|---|
| A | `deployment.py` | 意図配置 + 水平/鉛直分離ガウス展開誤差。既知アンカーは非共面固定 |
| B | `ranging.py` | アンカー間 TWR 測距(欠測=NaN, b_r/NLOS 枠, m回平均) |
| C | `calibration/`, `rigidity.py` | LM(trf) 自己校正。G1既知固定/G2規約固定, dof=3/2。剛性ランク+最小特異値 |
| D | `tag_positioning.py` | 推定/真アンカーでタグ測位(同一ノイズ, ΔRMSE 分離) |
| E | `metrics.py`, `alignment.py` | RMSE(H/V分解), Procrustes整列, PDOP過信度, カバレッジ |

## 現状(Phase B 実装中)
- **E0 全緑**: V-1〜V-8(V-4 単調性・V-5 Procrustes 不変式を追加, `pytest` 9 passed)。
- **E2 感度スイープ実装済**: OFAT(σ_r/σ_v/σ_deploy/N_a/R_max)＋2軸グリッド(σ_deploy×σ_r)。
  `make_figures.py` が感度曲線・破綻領域ヒートマップを自動判定して描画。profiler は各試行の
  `compute_time_s` 列で代替(専用スクリプトは未)。
- **既知の所見(裏取り済 2026-07-16)**: E1 公称配置(8台中7台が z=1500 平面, 既知1台のみ
  z=2900)は鉛直方向の自己校正が極めて弱い。N_mc=100 中央値で **shape RMSE 水平=55mm /
  鉛直=1128mm**(abs は水平97mm/鉛直2001mm)。σ_r=0 では完全復元するため実装バグではなく
  near-coplanar 幾何の必然。H/V 分解と rigidity 指標がこれを捕捉する。
- Phase B 残: σ_v/高さ多様性スイープの図・STEP1 由来の profiler 整理(任意)。
- Phase C: E3(Nüchter, 2D校正)・多スタート一意性検査。
