<!--
フォーマット規約:
- 「現在の状態」「次にやること」は常に上書きで最新化(古い内容は残さない)
- 「セッションログ」は新しい日付を上に追記。各回3行以内
- Cowork(Windows側AI)が読むファイル。実装を知らない読者にも状態が伝わる書き方をする
-->
---
last_updated: 2026-07-16
phase: 案B Phase A 完了（selfcal 骨組み・E0/E1 緑, commit 済）
---
# 実装状態(Cowork連携用)

## 現在の状態
- 案B（月面UWB自己校正）の **Phase A を実装完了・コミット済**（commit 42fb055）。
- `selfcal/` パッケージ新設。A〜E 全段実装（`pdop.simulation.geometry` の純粋関数のみ単方向再利用, pdop 本体は無改変）:
  - A `deployment.py`（水平/鉛直分離ガウス展開誤差, 既知アンカー非共面固定）
  - B `ranging.py`（アンカー間TWR, 欠測NaN, m回平均）
  - C `calibration/`（LM trf 自己校正）+ `rigidity.py`（G1既知固定/G2規約固定, dof=3/2, ランク+最小特異値）
  - D `tag_positioning.py`（推定/真アンカーで測位, ΔRMSE分離）
  - E `metrics.py`（RMSE H/V分解）+ `alignment.py`（Procrustes, PDOP過信度, カバレッジ）
- **受け入れテスト V-1,2,3,6,7,8 全緑**（`pytest tests/` = 7 passed）。V-8 は共面3D/2D両ケース。
- **E1 ベースケース CSV 出力可**（`results/e1_base.csv`, 100試行, H/V分解列含む）。CSVは再生成可能なため git 管理外。
- 所見: E1 公称配置（8台中7台 z=1500 平面, 既知1台のみ z=2900）は鉛直の自己校正が弱く、shape RMSE 鉛直 ≫ 水平。σ_r=0 で完全復元するため実装バグではなく near-coplanar 幾何の必然。H/V分解と rigidity 指標が捕捉。Phase B の σ_v/高さ多様性スイープで定量化する。

## 次にやること
- [ ] Phase B 着手: パラメータスイープ・E2感度曲線/ヒートマップ・profiler・V-4/V-5（STEP1移植を兼ねる）。
- [ ] （Phase B 前の裏取り）README 記載の鉛直RMSE概算値を実CSVの全条件平均で検算し所見を確定。
- [ ] Phase C: E3（Nüchter, 2D校正）・多スタート一意性検査。

## Coworkへの連絡事項
- Phase A の受け入れ判定条件（V-1〜3, V-6〜8 緑 ＋ E1 の H/V 分解 CSV）を全て充足。
- TBD 残（実装ブロッカーでない）: TBD-3 Nüchter再現数値（E3骨組みで待機）、TBD-1 PF追加（T-008 上田教授相談待ち）。

## セッションログ
### 2026-07-16
- VS Code再起動で未コミットだった Phase A 成果を確認・保全。pytest 7 passed 再確認、E1 CSV 再生成確認。
- selfcal/ 実装一式をコミット（42fb055）。status.md を Phase A 完了へ更新。
### 2026-07-13
- 仕様書 v1.1 を再読し実装計画を確定（v1.0）。σ_v150/非共面G1/G2規約固定/H-V分解/R_max150m/2D校正/V-8 を反映。
- 案B実装依頼を受領。仕様書・NotebookLM①〜④・既存資産を精読し実装計画書 v0.1 を作成。
- Cowork連携セットアップ(フェーズ1〜4)完了・push済み。CLAUDE.mdをインデックス化しrules/分割。
