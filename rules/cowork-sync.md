# cowork-sync — Cowork（Windows側AI）連携運用（詳細）

> CLAUDE.md のセッション開始/終了トリガーから参照される詳細手順。
> 出典: 研究フォルダ `Claude用参考資料/UWBリポジトリ_Cowork連携計画書.md`。
> チャネル設計: 各チャネルの書き込み主体は1つだけ（競合ゼロ）。

## チャネル一覧
| チャネル | 方向 | 場所 | 書く者 | 読む者 |
|---|---|---|---|---|
| 実装報告 | Code→Cowork | リポジトリ `docs/status.md`（正本）を研究フォルダへミラー | Claude Code | Cowork |
| 設計指示 | Cowork→Code | 研究フォルダ `Claude用参考資料/` | Cowork・ユーザー | Claude Code（読取専用） |
| コード規約 | 参照のみ | 研究フォルダ `CLAUDE.md` | ユーザー | Claude Code（読取専用） |

## 重要パス（WSL側表記）
```
研究フォルダ:   /mnt/c/Users/ahiro/OneDrive/デスクトップ/Claude/大学/研究/
設計指示置き場: 上記 + Claude用参考資料/
ミラー先:       上記 + Claude用参考資料/ClaudeCode_status_mirror.md
```

## セッション開始時（詳細）
- `docs/status.md` を読む（前回の状態・次のToDo）。
- 研究フォルダ `Claude用参考資料/` に新しい設計文書・指示ファイルがあれば読む（読取専用）。

## セッション終了時（詳細）
1. `docs/status.md` を更新（書式は下記「status.md 書式」）。
2. ミラーコピーと検証:
   ```bash
   cp docs/status.md "/mnt/c/Users/ahiro/OneDrive/デスクトップ/Claude/大学/研究/Claude用参考資料/ClaudeCode_status_mirror.md"
   cmp docs/status.md "/mnt/c/Users/ahiro/OneDrive/デスクトップ/Claude/大学/研究/Claude用参考資料/ClaudeCode_status_mirror.md"
   ```
   `cmp` で一致を必ず確認（OneDrive 破損対策の検証習慣）。
3. `git add -A && git commit`（メッセージ: 日本語で「何をなぜ」1行）。
4. push はユーザーに確認してから実行。

## status.md 書式
```markdown
<!--
フォーマット規約:
- 「現在の状態」「次にやること」は常に上書きで最新化(古い内容は残さない)
- 「セッションログ」は新しい日付を上に追記。各回3行以内
- Cowork(Windows側AI)が読むファイル。実装を知らない読者にも状態が伝わる書き方をする
-->
---
last_updated: YYYY-MM-DD
phase: セットアップ
---
# 実装状態(Cowork連携用)

## 現在の状態
(実装済み機能・動作確認状況)

## 次にやること
- [ ]

## Coworkへの連絡事項
(設計判断が必要な点、研究.md に反映してほしい決定事項。なければ「なし」)

## セッションログ
### YYYY-MM-DD
-
```

## 禁止事項（再掲・CLAUDE.md 本体が正）
- /mnt/c 配下への書き込み禁止。唯一の例外は `ClaudeCode_status_mirror.md` の上書きコピー。
- /mnt/c 配下の既存ファイルの編集・移動・削除は一切しない（読み取りは可）。
- リポジトリを /mnt/c 配下に配置しない。
- push は毎回ユーザーの確認を取る。
