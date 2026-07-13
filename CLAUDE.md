# CLAUDE.md — UWB_Research

このファイルはセッション開始時に必ず読み込まれる。**行動トリガー（言語・安全・役割・
セッション開始/終了）のみをここに置き**、詳細な仕様・手順は `rules/` に分割している。
必要になった時点で該当ファイルを読むこと。

---

## 重要ルール（常時）
- **日本語で回答する事。**
- **役割**: ユーザーの意見を肯定するばかりでなく、可能な限り批判的に意見を述べる。

## 安全管理・禁止事項（常時・最優先）
- ファイルの編集・移動・削除の際は必ずユーザーに確認を求める。勝手に削除しない。
- **/mnt/c 配下への書き込み禁止**。唯一の例外は
  `.../Claude用参考資料/ClaudeCode_status_mirror.md` の上書きコピーのみ。
- /mnt/c 配下の既存ファイルの編集・移動・削除は一切しない（読み取りは可）。
- リポジトリを /mnt/c 配下に配置しない。
- push は毎回ユーザーの確認を取る。
- 理由: OneDrive 同期が WSL/FUSE 経由の書き込みでファイルを破損させた実績があるため。

## セッション開始ルール
1. **`docs/status.md`** を読む（このリポジトリの前回状態・次のToDo）。
2. **AkariVault `_Dev/context/hot.md`** を読む（全プロジェクト横断の軽量メモ）。
   → 詳細手順: `rules/akarivault-workflow.md`
3. 研究フォルダ `Claude用参考資料/` に新しい設計文書・指示があれば読む（読取専用）。
   → 連携運用の詳細: `rules/cowork-sync.md`

## セッション終了ルール（「今日はここまで」等の合図で実行）
1. `docs/status.md` を更新 → ミラーコピー＋`cmp`検証。手順: `rules/cowork-sync.md`
2. 自己ふりかえり: 今回の修正指示・繰り返された指示・違和感FBを `_Dev/improvements.md` に起票
3. `_Dev/tasks.md` を更新（完了・差し戻し・新規起票）
4. `hot.md` 更新（300字以内厳守。溢れた分は `_Dev/context/archive/YYYY-MM-DD.md` へ）
5. active_project の作業ログcanvas（`01_Projects/<プロジェクト>/`）を更新
6. プロジェクト詳細 → `_Dev/context/projects/` に記録
7. `04_Context` 追記候補があれば差分案を提示し、**ユーザー承認を得てから**書き込む（承認なしの書き込みは経路を問わず禁止）
8. `git add -A && git commit`（日本語で「何をなぜ」1行）。push はユーザー確認後。
---

## rules/ インデックス（必要時に読む詳細）
- `rules/architecture-gdop.md` — gdop（2D原本）の3層アーキテクチャ・規約・データ形式・実行方法
- `rules/architecture-pdop.md` — pdop（3D拡張）のアーキテクチャと gdop との差分
- `rules/research-context.md` — 研究文脈・STEP1〜3計画・現在の実装状況
- `rules/akarivault-workflow.md` — AkariVault hot.md の運用詳細
- `rules/cowork-sync.md` — Cowork連携（docs/status.md 運用・ミラー手順・書式）

## リポジトリ構成（概要）
- `gdop/` — 2D GDOP/PDOP 可視化デスクトップアプリ（独立 git submodule, PyQt5/matplotlib）
- `pdop/` — その3D拡張（PDOP/HDOP/VDOP, ≥4非平面アンカー）。詳細は `rules/architecture-pdop.md`
- `docs/` — Cowork連携用の実装状態（`status.md`）
