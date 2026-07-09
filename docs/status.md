<!--
フォーマット規約:
- 「現在の状態」「次にやること」は常に上書きで最新化(古い内容は残さない)
- 「セッションログ」は新しい日付を上に追記。各回3行以内
- Cowork(Windows側AI)が読むファイル。実装を知らない読者にも状態が伝わる書き方をする
-->
---
last_updated: 2026-07-09
phase: セットアップ完了
---
# 実装状態(Cowork連携用)

## 現在の状態
- Cowork連携セットアップ完了。リポジトリは WSL ext4 内 (`~/UWB_Research`)、GitHub認証はSSHで疎通。
- CLAUDE.md をインデックス化し、詳細ルールを `rules/` 配下5ファイルに分割:
  architecture-gdop / architecture-pdop / research-context / akarivault-workflow / cowork-sync。
- `docs/status.md`（本ファイル）を新設。Cowork へのミラー先は
  研究フォルダ `Claude用参考資料/ClaudeCode_status_mirror.md`。
- 実装本体の現在地: STEP1 の3Dコアエンジン（≥4非平面アンカー・N次元trilateration・
  PDOP/HDOP/VDOP）は `pdop/` に実装済み・動作確認済み（スモークテストで PDOP=1.552 等を確認）。

## 次にやること
- [ ] STEP1完成に向けたバッチ評価パイプラインの `pdop/` への移植
      (3Dアンカーパターン生成・モンテカルロ3D RMSE・計算時間ベンチ・CSV/プロット集計)。
      設計参照元は姉妹プロジェクト `~/UWB_Sim`(2D)。
- [ ] (任意) フェーズ5: セッション終了時ミラーコピーの hooks(SessionEnd) による自動化。

## Coworkへの連絡事項
- CLAUDE.md を「本体=行動トリガーのみ+rules/へのインデックス」構成に変更した。
  セッション routine は AkariVault `hot.md`(横断メモ) と `docs/status.md`(本リポジトリ実装状態)の
  2系統併存とした。研究.md 側の運用に取り込む際はこの前提で。
- 上記以外に設計判断が必要な点は現時点でなし。

## セッションログ
### 2026-07-09
- Cowork連携計画書に沿ってフェーズ1〜4を実施(環境確認→配置確認→CLAUDE.md統合→終了ルーチン)。
- CLAUDE.md をインデックス化+rules/分割、docs/status.md 新設、ミラー運用を確立。
