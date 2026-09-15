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
# E2 感度スイープ(EXPERIMENTS: E2_sigma_r/_v/_deploy/_n_anchors/_r_max/_height_diversity/_height_gap/_grid/_grid_rigidity)
.venv/bin/python scripts/run_experiment.py --exp E2_sigma_r --out results/e2_sigma_r.csv
# 破綻領域マップ2種(追補①): 精度破綻(σ_deploy×σ_r, タグ測位ON) と 剛性破綻(N_a×R_max, タグ測位OFF)
.venv/bin/python scripts/run_experiment.py --exp E2_grid          --out results/e2_grid.csv --n-mc 40
.venv/bin/python scripts/run_experiment.py --exp E2_grid_rigidity --out results/e2_grid_rigidity.csv
# 高さ多様性スイープ(鉛直自己校正の成立条件を定量化。1500-5000を500刻み+{10000,40000}参考点)
.venv/bin/python scripts/run_experiment.py --exp E2_height_diversity --out results/e2_height.csv
# E2c 未知アンカーの高さ分散パターン H0〜H4(タグ測位 ON。既知4台の高さは §4.4 規定のまま固定)
.venv/bin/python scripts/run_experiment.py --exp E2c --out results/e2c_patterns.csv
# 追補⑤: 仰角スイープの空白区間(別CSV, 1.5/5/10m を同一実行の基準に含む)と H5 外挿検証(タグ測位 ON)
.venv/bin/python scripts/run_experiment.py --exp E2_height_gap --out results/e2_height_gap.csv
.venv/bin/python scripts/run_experiment.py --exp E2c_extrap    --out results/e2c_extrap.csv
# 追補⑤の判定(基準は docstring で実行前に固定)と、高さ std 共通軸の統合図
.venv/bin/python scripts/analyze_height_gap.py
.venv/bin/python scripts/plot_unified_height.py --out results/e2c_unified_height.png
# 図(スイープ軸を自動判定: 1軸→感度曲線 / 2軸→破綻領域ヒートマップ。破綻は×剛性/△精度で色分け)
.venv/bin/python scripts/make_figures.py --csv results/e2_sigma_r.csv        --out results/e2_sigma_r.png
.venv/bin/python scripts/make_figures.py --csv results/e2_grid.csv           --out results/e2_grid.png --metric coverage
.venv/bin/python scripts/make_figures.py --csv results/e2_grid_rigidity.csv  --out results/e2_grid_rigidity.png
.venv/bin/python scripts/make_figures.py --csv results/e2_height.csv         --out results/e2_height_v.png --metric rmse_anchor_shape_v_mm
# カテゴリ群の箱ひげ(--group)。裾が長い指標は --logy(タグ鉛直は発散試行で線形軸だと潰れる)
.venv/bin/python scripts/make_figures.py --csv results/e2c_patterns.csv --out results/e2c_anchor_v.png --group height_pattern --metric rmse_anchor_shape_v_mm
.venv/bin/python scripts/make_figures.py --csv results/e2c_patterns.csv --out results/e2c_tag_v.png --group height_pattern --metric rmse_tag_v_mm --logy
```

## パイプライン(A→E, §5)
| 段 | モジュール | 内容 |
|---|---|---|
| A | `deployment.py` | 意図配置 + 水平/鉛直分離ガウス展開誤差。既知アンカーは非共面固定 |
| B | `ranging.py` | アンカー間 TWR 測距(欠測=NaN, b_r/NLOS 枠, m回平均) |
| C | `calibration/`, `rigidity.py` | LM(trf) 自己校正。G1既知固定/G2規約固定, dof=3/2。剛性ランク+最小特異値 |
| D | `tag_positioning.py` | 推定/真アンカーでタグ測位(同一ノイズ, ΔRMSE 分離) |
| E | `metrics.py`, `alignment.py` | RMSE(H/V分解), Procrustes整列, PDOP過信度, カバレッジ |

## 現状(Phase B + 追補①〜⑤ 完了 / Phase C: 一意性検査・E3・E2c 完了)
- **E0 全緑**: V-1〜V-9(V-9 多スタート一意性を追加, `pytest` 11 passed)。
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
  (5000mm の値は乱数列が別の独立な実行で 964mm。所見7参照)
- **所見3(追補②誤差伝搬)**: E1 でタグ側 RMSE_tag 鉛直=3078mm(水平=138mm)。真アンカー版
  (5990mm)より小さく **ΔRMSE_tag_v が負** = 近共面は VDOP≈9〜12 が測距ノイズを増幅し幾何自体が
  破綻(校正誤差の加算では説明できない)。高さ多様40mでは VDOP≈2, ΔRMSE_tag_v≈+3mm と正常化。
  C(200mm)=4%, C(100mm)=1%。
- **所見4(追補①破綻マップ)**: 剛性破綻=R_max≲70m で全域 rigidity_ok=False(周長配置の対角
  ≈141m が閾。N_a には非依存)。精度破綻=近共面基底では σ_deploy×σ_r 全30セルで C(200mm)<10%
  (σ_r が支配, σ_deploy はほぼ無関係)=幾何律速。
- **所見5(追補④N_a)**: N_a=5→16 で鉛直 shape RMSE は ≈530→1000mm と頭打ち。台数を増やしても
  同一平面上なら鉛直は改善せず ⇒ 効くのは台数でなく高さ多様性(所見2改を補強)。
- **所見6(E2c: 主張後段の棄却)**: 未知アンカー4台の意図高さを H0〜H4 で振っても、鉛直 shape RMSE は
  1128→1006mm(最良 H4)にとどまり **H0 との差は統計的に有意でない**(Mann-Whitney p=0.057〜0.913、
  中央値差のブートストラップ95%CI が 0 を跨ぐ)。タグ C(200mm) も 4.0→4.3% で不変。
  ⇒ 「複数台高さ分散で確保する」という主張は成立しない。
  旧記述の「効くのは高さ分散の総量だけ(E2c の点が追補③の曲線に乗る)」は所見7で棄却した。
  旧記述の「改善は std ≳1800mm から」は図に手で書いた数字が本文に流れたもので根拠がなく、削除した。
  副次的発見: 近共面ではタグ測位が数%の試行で発散する(tag_v 最大 2.4e8 mm, 校正自体は収束・剛性OK)
  ため、**評価は平均でなく中央値で行う**こと。
- **所見7(追補⑤: 空白区間の追試と総量則の外挿検証, 2026-09-15)**: 実現可能域は 400〜2,900mm に確定
  (5,000mm は参考条件)。この範囲での8台全体の高さ std の上限は 0.987m。判定基準は実行前に固定した
  (`scripts/analyze_height_gap.py` の docstring, commit 078d806)。
  - 単一台昇降(`E2_height_gap`): 1.5m 比で Holm 補正後に有意に下がる最初の水準は **5,000mm(std 1.16m)**
    で、検定した最低水準で既に有意(1156→964mm)。7月版の 2.0〜4.5m(1.5m 比 −5〜−13%)と合わせ、
    横ばいから急落するのではなく緩やかに下がると読む。10,000mm でも 648mm。
    同じ 5m でも7月版は 1061mm。条件番号が違うと乱数列が別(独立標本)になり、100試行の中央値は ±100mm 程度揺れる。
  - H5(未知4台={5000,5000,5000,400}, std 1.78m)は 1035mm で、単一台 7m(std 1.82m)の 804mm から
    外れる(差 +231mm, 95%CI [131,338])。同一実行の H0(1128mm)とも有意差なし(p=0.145)。
    ⇒ **「同じ std なら1台を上げても複数台に散らしても同じ」は成り立たない**。std≤1.15m で重なって
    見えたのは、どちらも横ばいの区間だったため。
  - 探索的所見(事後に選んだ軸・未検証): H5 は傾いた平面に近く、最良近似平面からの厚み(RMS)は 0.86m と
    z std の約半分。厚みで比べると単一台 4.5〜5m と整合する。ただし既知/未知どちらを上げたかとも交絡している。
  - 実現可能域での結論(単一昇降・台数増・複数台分散のいずれでも実用水準に届かない)は維持。
  - 同一環境の再実行で compute_time_s 以外の全列が一致。`provenance.py` の dirty 判定が出力 CSV 自身を
    拾い常に True になっていた不具合を修正(出力先ディレクトリ配下を除外)。
### Phase C(一意性検査・E3・E2c 完了)
- **多スタート一意性検査(`uniqueness.py`, V-9)**: 剛性ランクは局所一意性の必要条件だが鏡映等の
  離散不定性(大域一意性)は捕捉できない(§4.4 注意1)。複数初期値から自己校正し低残差解を
  回転のみ Procrustes で形状クラスタリング、相異なる解が2つ以上なら「離散不定性あり」と判定。
  **三脚(頂点を非共線3点に距離拘束)は剛性ランク充足(rigidity_ok=True)でも頂点反転の2解を検出**
  = 一意性検査は剛性検査が原理的に見逃す破綻を捕捉する。既知非共面(E1)なら1解=大域一意。
- **E3 2D校正モード(`--exp E3`, dof=2)**: 全アンカー z を意図値固定で x,y のみ推定。近共面E1で
  **アンカー鉛直 abs 2001→95mm / shape 1128→72mm と劇的に安定化**(鉛直の誤推定を回避)。ただし
  **タグ鉛直測位は 3078→6194mm と悪化**(z固定でアンカーがより共面化し VDOP 悪化)。⇒ 2D校正は
  アンカー自己校正を救うがタグ測位の律速(近共面 VDOP)は救えない=高さ多様性が本質という主張を補強。
- **E2c 高さ分散パターン(`--exp E2c`)**: 未知アンカーの意図高さを levels(層化巡回)/uniform(試行毎乱数)
  で振る。既知4台は §4.4 規定固定。結果は所見6(主張後段の棄却)。σ_deploy=300mm(config既定)と
  1,000mm(仕様書 §5 の E1 公称)の両系列で実行し全指標が一致 = σ_deploy 非依存を再確認。
- 残: E3 の多条件スイープ化、一意性検査の MC 組込み、TBD-3 Nüchter 数値照合、
  「平面からの厚み」仮説と「既知/未知どちらを上げたか」仮説の切り分け(**未検証**)、
  「std/D 比(D=配置スパン)が支配」仮説の検証(area_mm スイープ, **未検証**)。
  推定器比較・PF 追加は T-008 決着(PF不採用・最小二乗固定)によりクローズ。
