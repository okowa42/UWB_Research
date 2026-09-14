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
- **WSL からの /mnt/c 配下への書き込み禁止**（読み取りは可）。
  理由: OneDrive 同期が WSL/FUSE 経由の書き込みでファイルを破損させた実績があるため。
  → 2026-09-14 以降このプロジェクトで WSL は使わないため、通常は抵触しない。
- push は毎回ユーザーの確認を取る。

## 実行環境（2026-09-14 確定・Windows ネイティブ一本）
- **リポジトリ正本**: `C:\dev\UWB_Research`（これ1つだけ）
  - 2026-09-14 に OneDrive 配下から移設。理由: 同期フォルダに git リポジトリを置くと `.git` の
    整合性が同期のタイミングに左右されうるための予防措置。バックアップは GitHub remote に任せる。
  - ※移設時に「HEAD が1コミット古く見えた・results/ のファイルが途中で出現した」を OneDrive
    同期遅延の実例として挙げたが、**誤り**。実際は同じリポジトリで動いていた並行 Claude Code
    セッションの作業だった（2026-09-14 訂正）。
- **Python**: `C:\Users\ahiro\.venvs\uwb\Scripts\python.exe`（OneDrive 外に配置）
  - 依存は `selfcal/requirements.txt` にピン。再構築は
    `python -m venv C:\Users\ahiro\.venvs\uwb` → `pip install -r selfcal/requirements.txt`
  - Windows の **system Python には numpy が入っていない**。必ず上記 venv を使う。
- **WSL はこのプロジェクトでは使わない**。旧クローンは 2026-09-14 に整理済み
  （Ubuntu-20.04 は削除、Ubuntu-22.04 の `~/UWB_Research` は結果回収後に残置）。
- **AkariVault** (`C:\Users\ahiro\AkariVault`) は OneDrive 配下ではない。ネイティブ書き込み可。

## 実験結果の扱い（再現性）
- `selfcal/results/*.csv` は **git 管理下**（PNG のみ gitignore）。再実行しても同じ値に
  ならないため「生成物」ではなく「実験記録」として扱う。
- `run_experiment.py` は CSV と同時に `<csv名>.meta.json`（commit・環境・config・
  CSVハッシュ）を出力する。**図に使った数値は必ず meta とセットで残すこと。**
- seed を固定しても、同じ実験を再実行すると個別試行値が**全行で変わる**ことがある
  （2026-09-14 実測: 仰角スイープ・E2c とも全行不一致、分布はほぼ一致）。コアコードは不変で、
  実行環境の差が有力候補だが原因は未特定。論文・発表では中央値・四分位で語り、
  個別試行値には依拠しない。

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
