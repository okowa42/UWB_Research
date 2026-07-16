<!--
フォーマット規約:
- 「現在の状態」「次にやること」は常に上書きで最新化(古い内容は残さない)
- 「セッションログ」は新しい日付を上に追記。各回3行以内
- Cowork(Windows側AI)が読むファイル。実装を知らない読者にも状態が伝わる書き方をする
-->
---
last_updated: 2026-07-16
phase: 案B Phase B 実装中（E2スイープ・破綻マップ・V-4/V-5 緑, commit 済）
---
# 実装状態(Cowork連携用)

## 現在の状態
- 案B（月面UWB自己校正）: **Phase A 完了**（42fb055）に続き **Phase B の主要部を実装・コミット済**（41114f8）。
- `selfcal/` パッケージ。A〜E 全段（`pdop.simulation.geometry` の純粋関数のみ単方向再利用, pdop 本体無改変）。
- **E0 受け入れテスト 全緑**（`pytest tests/` = 9 passed）: V-1,2,3,6,7,8（Phase A）＋ **V-4（σ_r増で中央値RMSE単調増）・V-5（G2 Procrustes整列後shape≤整列前abs）**（Phase B）。
- **E2 感度スイープ実装済**: OFAT（σ_r/σ_v/σ_deploy/N_a=[4,6,8,9,12]/R_max）＋2軸グリッド（σ_deploy×σ_r）を `experiments.EXPERIMENTS` に登録。`make_figures.py` が感度曲線／破綻領域ヒートマップをスイープ軸自動判定で描画（PNG生成確認済）。profiler は各試行の `compute_time_s` 列で代替。
- **E1 所見を裏取り確定（N_mc=100 中央値）**: 公称配置（8台中7台 z=1500 平面, 既知1台のみ z=2900）は鉛直の自己校正が弱く、**shape RMSE 水平=55mm / 鉛直=1128mm**（abs 水平97/鉛直2001）。σ_r=0 で完全復元＝実装バグでなく near-coplanar 幾何の必然。H/V分解と rigidity 指標が捕捉。
- 生成物（CSV/PNG）は再生成可能なため git 管理外（`.gitignore: selfcal/results/`）。図生成に matplotlib を追加。

## 次にやること
- [ ] Phase B 仕上げ: σ_v/高さ多様性を主軸にした破綻マップ図・N_a 感度曲線の図出力と考察。
- [ ] Phase C: E3（Nüchter, 2D校正モード, 骨組み）・多スタート一意性検査（鏡映等の離散不定性検出）。

## Coworkへの連絡事項
- Phase A 判定条件（V-1〜3,6〜8 緑＋E1 H/V CSV）に加え Phase B 判定（V-4,V-5 緑＋E2破綻マップ図）も充足。
- 研究主張候補「高さ多様性=3D自己校正の成立条件」を E1 数値（鉛直RMSE≫水平）が支持。Phase C の一意性検査で補強予定。
- TBD 残（実装ブロッカーでない）: TBD-3 Nüchter再現数値（E3骨組みで待機）、TBD-1 PF追加（T-008 上田教授相談待ち）。

## セッションログ
### 2026-07-16
- VS Code再起動で未コミットだった Phase A 成果を確認・保全（42fb055）。status.md を Phase A 完了へ更新。
- Phase B 実装: E2スイープ(OFAT+2軸グリッド)・make_figures(感度曲線/破綻マップ)・V-4/V-5 追加。pytest 9 passed（41114f8）。
- E1 所見を N_mc=100 中央値で裏取り（shape RMSE 水平55/鉛直1128mm）。README の概算値を検算・確定。
### 2026-07-13
- 仕様書 v1.1 を再読し実装計画を確定（v1.0）。σ_v150/非共面G1/G2規約固定/H-V分解/R_max150m/2D校正/V-8 を反映。
- 案B実装依頼を受領。仕様書・NotebookLM①〜④・既存資産を精読し実装計画書 v0.1 を作成。
- Cowork連携セットアップ(フェーズ1〜4)完了・push済み。CLAUDE.mdをインデックス化しrules/分割。
