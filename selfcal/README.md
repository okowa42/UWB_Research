# selfcal — 月面UWBアンカー自己校正シミュレーション(案B)

ヘッドレス・バッチ評価パッケージ。`pdop.simulation.geometry` の純粋関数のみを
単方向依存で再利用し、pdop 本体は変更しない。準拠仕様は
`docs/implementation-plan-selfcal.md`(仕様書 v1.1)。単位はすべて mm/deg/s。

## セットアップ
```bash
python3 -m venv selfcal/.venv
selfcal/.venv/bin/pip install numpy scipy pyyaml pytest
```

## 実行
```bash
cd selfcal
# 受け入れ基準テスト(E0: V-1,2,3,6,7,8)
.venv/bin/python -m pytest tests/ -q
# E1 ベースケース(CSV 出力)
.venv/bin/python scripts/run_experiment.py --exp E1 --out results/e1_base.csv
```

## パイプライン(A→E, §5)
| 段 | モジュール | 内容 |
|---|---|---|
| A | `deployment.py` | 意図配置 + 水平/鉛直分離ガウス展開誤差。既知アンカーは非共面固定 |
| B | `ranging.py` | アンカー間 TWR 測距(欠測=NaN, b_r/NLOS 枠, m回平均) |
| C | `calibration/`, `rigidity.py` | LM(trf) 自己校正。G1既知固定/G2規約固定, dof=3/2。剛性ランク+最小特異値 |
| D | `tag_positioning.py` | 推定/真アンカーでタグ測位(同一ノイズ, ΔRMSE 分離) |
| E | `metrics.py`, `alignment.py` | RMSE(H/V分解), Procrustes整列, PDOP過信度, カバレッジ |

## 現状(Phase A 完了)
- V-1,2,3,6,7,8 緑。E1 ベースケース CSV(H/V 分解列含む)を出力可能。
- **既知の所見**: E1 公称配置(8台中7台が z=1500 平面, 既知1台のみ z=2900)は鉛直方向の
  自己校正が極めて弱い(shape RMSE 水平≈55mm に対し鉛直≈1130mm)。σ_r=0 では完全復元
  するため実装バグではなく、near-coplanar 幾何の必然。H/V 分解と rigidity_cond が
  これを捕捉する。Phase B の σ_v / 高さ多様性スイープで定量化する対象。
- Phase B: スイープ・E2感度曲線/ヒートマップ・profiler・V-4/V-5(STEP1移植を兼ねる)。
- Phase C: E3(Nüchter, 2D校正)・多スタート一意性検査。
