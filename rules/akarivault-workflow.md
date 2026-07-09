# akarivault-workflow — AkariVault hot.md 運用（詳細）

> CLAUDE.md のセッション開始/終了トリガーから参照される詳細手順。
> hot.md は全プロジェクト横断の軽量グローバルメモ。このリポジトリ固有の実装状態は
> `docs/status.md`（→ `rules/cowork-sync.md`）で別管理する。両者は併存させる。

## セッション開始時（詳細）
- 最初に AkariVault の `_Dev/context/hot.md` を読む。前回セッションの状態・次のToDoが記録されている。
- hot.md の `active_project` または会話の文脈から作業対象プロジェクトを判断し、対応する
  `_Dev/context/projects/` 配下のファイルも読む（例: 研究の話なら `projects/研究.md`）。
- 該当ファイルが存在しない場合は読み飛ばしてよい。新規プロジェクトで継続作業が見込まれる場合は
  セッション末に新規作成する。

## セッション終了時（詳細）
- ユーザーが「今日はここまで」「終わります」「セッション終了」などを言ったら、必ず AkariVault の
  `_Dev/context/hot.md` を更新してからセッションを閉じる。
- 更新内容: (1)直近セッションでやったこと, (2)active_project の更新, (3)次回セッションでやること。
  hot.md は300字以内の軽量グローバルメモとして保つ。
- プロジェクト固有の情報（技術詳細・積み残しタスク・ファイル一覧）は
  `_Dev/context/projects/該当プロジェクト.md` を更新する。hot.md には書かない。
- 古くなった情報は削除または `_Dev/context/archive/YYYY-MM-DD.md` に移動する。
