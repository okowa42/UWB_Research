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
# E2 感度スイープ(EXPERIMENTS: E2_sigma_r/_v/_deploy/_n_anchors/_r_max/_height_diversity/_grid/_grid_rigidity)
.venv/bin/python scripts/run_experiment.py --exp E2_sigma_r --out results/e2_sigma_r.csv
# 破綻領域マップ2種(追補①): 精度破綻(σ_deploy×σ_r, タグ測位ON) と 剛性破綻(N_a×R_max, タグ測位OFF)
.venv/bin/python scripts/run_experiment.py --exp E2_grid          --out results/e2_grid.csv --n-mc 40
.venv/bin/python scripts/run_experiment.py --exp E2_grid_rigidity --out results/e2_grid_rigidity.csv
# 高さ多様性スイープ(鉛直自己校正の成立条件を定量化。1500-5000を500刻み+{10000,40000}参考点)
.venv/bin/python scripts/run_experiment.py --exp E2_height_diversity --out results/e2_height.csv
# 図(スイープ軸を自動判定: 1軸→感度曲線 / 2軸→破綻領域ヒートマップ。破綻は×剛性/△精度で色分け)
.venv/bin/python scripts/make_figures.py --csv results/e2_sigma_r.csv        --out results/e2_sigma_r.png
.venv/bin/python scripts/make_figures.py --csv results/e2_grid.csv           --out results/e2_grid.png --metric coverage
.venv/bin/python scripts/make_figures.py --csv results/e2_grid_rigidity.csv  --out results/e2_grid_rigidity.png
.venv/bin/python scripts/make_figures.py --csv results/e2_height.csv         --out results/e2_height_v.png --metric rmse_anchor_shape_v_mm
```

## パイプライン(A→E, §5)
| 段 | モジュール | 内容 |
|---|---|---|
| A | `deployment.py` | 意図配置 + 水平/鉛直分離ガウス展開誤差。既知アンカーは非共面固定 |
| B | `ranging.py` | アンカー間 TWR 測距(欠測=NaN, b_r/NLOS 枠, m回平均) |
| C | `calibration/`, `rigidity.py` | LM(trf) 自己校正。G1既知固定/G2規約固定, dof=3/2。剛性ランク+最小特異値 |
| D | `tag_positioning.py` | 推定/真アンカーでタグ測位(同一ノイズ, ΔRMSE 分離) |
| E | `metrics.py`, `alignment.py` | RMSE(H/V分解), Procrustes整列, PDOP過信度, カバレッジ |

## 現状(Phase B + 追補 完了)
- **E0 全緑**: V-1〜V-8(V-4 単調性・V-5 Procrustes 不変式を追加, `pytest` 9 passed)。
- **E2 感度スイープ実装済**: OFAT(σ_r/σ_v/σ_deploy/N_a/R_max/high_diversity)＋破綻領域マップ2種
  (精度破綻=σ_deploy×σ_r タグ測位ON / 剛性破綻=N_a×R_max タグ測位OFF)。`make_figures.py` が
  感度曲線・破綻マップを自動判定し、剛性破綻(×赤)/精度破綻(△橙 C(200mm)<95%)を凡例付きで色分け。
- **所見1(裏取り済)**: E1 公称配置(8台中7台が z=1500 平面, 既知1台のみ z=2900)は鉛直の
  自己校正が極めて弱い。N_mc=100 中央値で **shape RMSE 水平=55mm / 鉛直=1128mm**(abs は
  水平97/鉛直2001)。σ_r=0 で完全復元＝実装バグでなく near-coplanar 幾何の必然。
- **所見2改(追補③で修正)**: 既知1台の仰角スイープを実現可能域で細分化した結果、
  **1500→5000mm では鉛直 shape RMSE は 1168→1061mm(≈9%減)にとどまる**。大幅改善(10000mm
  で564mm, 40000mm で134mm)は実現性の弱いタワー級高さでのみ生じる。⇒「単一アンカーを上げる」
  だけでは実用域で不足。旧「40mで8倍改善」は理論上限であり主張を要修正。
- **所見3(追補②誤差伝搬)**: E1 でタグ側 RMSE_tag 鉛直=3078mm(水平=138mm)。真アンカー版
  (5990mm)より小さく **ΔRMSE_tag_v が負** = 近共面は VDOP≈9〜12 が測距ノイズを増幅し幾何自体が
  破綻(校正誤差の加算では説明できない)。高さ多様40mでは VDOP≈2, ΔRMSE_tag_v≈+3mm と正常化。
  C(200mm)=4%, C(100mm)=1%。
- **所見4(追補①破綻マップ)**: 剛性破綻=R_max≲70m で全域 rigidity_ok=False(周長配置の対角
  ≈141m が閾。N_a には非依存)。精度破綻=近共面基底では σ_deploy×σ_r 全30セルで C(200mm)<10%
  (σ_r が支配, σ_deploy はほぼ無関係)=幾何律速。
- **所見5(追補④N_a)**: N_a=5→16 で鉛直 shape RMSE は ≈530→1000mm と頭打ち。台数を増やしても
  同一平面上なら鉛直は改善せず ⇒ 効くのは台数でなく高さ多様性(所見2改を補強)。
- Phase C: 多スタート一意性検査(離散不定性検出)・E3(2D校正モード)・(T-008)推定器比較。
