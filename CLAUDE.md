# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

***重要ルール***
*日本語で回答する事

**安全管理ルール**
*ファイルの編集・移動・削除の際は必ずユーザーに確認を求めること。勝手に削除しない。

**役割**
*ユーザーと協力してより優れた成果を出すために、ユーザーの意見を肯定するばかりでなく、可能な限り批判的に意見を述べること。

**セッション開始時のルール**
*最初に AkariVault の `_Dev/context/hot.md` を読むこと。前回セッションの状態・次のToDoが記録されている。
*hot.md の `active_project` または会話の文脈から作業対象プロジェクトを判断し、対応する `_Dev/context/projects/` 配下のファイルも読むこと（例: 研究の話なら `projects/研究.md`）。
*該当ファイルが存在しない場合は読み飛ばしてよい。新規プロジェクトで継続作業が見込まれる場合はセッション末に新規作成すること。

**セッション終了時のルール**
*ユーザーが「今日はここまで」「終わります」「セッション終了」などを言ったら、必ず AkariVault の `_Dev/context/hot.md` を更新してからセッションを閉じること。
*更新内容: (1)直近セッションでやったこと, (2)active_projectの更新, (3)次回セッションでやること。hot.mdは300字以内の軽量グローバルメモとして保つ。
*プロジェクト固有の情報（技術詳細・積み残しタスク・ファイル一覧）は `_Dev/context/projects/該当プロジェクト.md` を更新すること。hot.mdには書かない。
*古くなった情報は削除または `_Dev/context/archive/YYYY-MM-DD.md` に移動する。

---

## Repository layout

This top-level directory is not itself a git repo; it bundles separate research projects:

- `gdop/` — the original project. A PyQt5/matplotlib desktop app for real-time 2D GDOP/PDOP
  (Geometric/Position Dilution of Precision) calculation and visualization of UWB anchor/tag
  setups. This is its own git repository (forked from `schwarzfelix/gdop`).
- `pdop/` — the 3D extension of the GDOP work (see "current research context" below). Mirrors
  `gdop/`'s three-layer structure but with 3D (`[x, y, z]`) positions, PDOP/HDOP/VDOP, and a
  trimmed-down feature set (no CSV import, streaming, or scenario-comparison plot). Not a git
  repo. See "Architecture (pdop)" below for the differences from `gdop/`.

Commands in "Setup & running" / "Architecture" below assume `cd gdop` or `cd pdop` respectively.

## Setup & running (gdop / pdop)

```bash
cd gdop   # or: cd pdop
python3 -m venv env && source env/bin/activate   # a venv ("env" or ".venv") already exists in gdop's checkout
pip install -r requirements.txt
python app.py
```

There is no automated test suite yet, but `.vscode/launch.json` has a pytest debug config
(`pytest -q`) ready for when tests are added — place new tests alongside the module under test.

## Architecture (gdop)

Three layers, kept intentionally separate:

- **`simulation/`** — domain model and math, no UI/Qt dependencies.
  - `station.py`: `Anchor` (fixed position) and `Tag` (position derived via trilateration from
    measurements) — both subclass `Station`. `Tag.position()` recursively trilaterates from
    whichever anchors/tags it has measurement relations to (via `geometry.trilateration`),
    excluding itself to avoid cycles.
  - `measurements.py`: `Measurements` stores distances keyed by `frozenset({station_a, station_b})`
    in `self.relation`. This frozenset-pair convention is used everywhere measurements are
    read or written — preserve it when adding new code paths.
  - `geometry.py`: pure numpy math — `trilateration`, `euclidean_distances`,
    `dilution_of_precision` (GDOP via the geometry/covariance matrix), `angle_*` helpers.
  - `scenario.py`: `Scenario` aggregates `stations` (mixed Anchors/Tags) + a `Measurements`
    instance + a `tag_truth` (an `Anchor` representing ground truth) + `sigma` (noise stddev).
    `SandboxScenario` (in `sandbox_scenario.py`) is the default scenario used by `app.py`;
    it builds 3 anchors + 1 tag and synthesizes noisy measurements against `tag_truth` via
    `generate_measurements()`.

- **`data/`** — pure data import/streaming, no UI dependencies.
  - `import_scenario.py` loads station layout from `workspace/<scenario>/scenario.json`
    (`stations: [{name, type: ANCHOR|TAG, position?}]`; a TAG entry with a `position` sets
    `scenario.tag_truth`).
  - `import_measurements.py` reads all `workspace/<scenario>/*.csv` RTT logs (tolerant of
    `//` comment lines and a `#`-prefixed header row), normalizes column names.
  - `importer.py` ties these together: `import_scenario_data()` / `import_scenario()` load the
    JSON config, then aggregate the CSV's `est._range(m)` per `ap-ssid` using one of
    `newest|lowest|mean|median` (default `lowest`) and call `measurements.update_relation()`
    against the first TAG in the scenario.
  - `sse_streamer.py` / `mqtt_streamer.py`: background-thread streamers that push live
    distance updates into `scenario.measurements` (SSE is wired up; MQTT parsing is a stub —
    see `data_tab.py` TODO).

- **`presentation/`** — PyQt5 UI; reads/mutates `simulation` objects and re-renders.
  - `mainwindow.py`: `MainWindow` owns one `TrilatPlot` (per-scenario 2D plot) and one
    `ComparisonPlot` (bar chart of first-tag GDOP across all loaded scenarios), plus a
    `QTabWidget`. `update_all(anchors, tags, measurements)` is the central refresh entry
    point — UI code that mutates state should emit one of `TrilatPlot`'s
    `anchors_changed` / `tags_changed` / `measurements_changed` signals (connected back to
    `update_all`) rather than calling plot updates directly.
  - `trilatplot.py`: draggable/clickable matplotlib plot of anchors, tag estimates, tag truth,
    measurement circles/lines — driven by `DisplayConfig` flags (`displayconfig.py`).
  - `tabs/`: `TreeTab` (browse/import/activate scenarios from `workspace/`, edit/delete
    stations), `DisplayTab` (toggle `DisplayConfig` flags), `SandboxTab` (sigma/noise
    slider), `DataTab` (streaming source config), `PlotTab` (toolbar). All extend
    `BaseTab` (`create_widget()` + `tab_name` abstract; lazily built via `get_widget()`).

### Conventions to preserve
- Domain (`simulation/`) and data (`data/`) layers must stay free of PyQt imports.
- Measurement keys are always `frozenset({station1, station2})`, two elements.
- UI mutations should go through the `*_changed` signals so `MainWindow.update_all` stays the
  single refresh path.

## Architecture (pdop)

`pdop/` mirrors `gdop/`'s three-layer structure (`simulation/` / `data/` / `presentation/`)
and shares its conventions ("Conventions to preserve" above applies here too), but is a 3D,
trimmed-down rebuild:

- **`simulation/`** — positions are `[x, y, z]` everywhere (`Tag.position()`'s no-anchor
  fallback is `[0.0, 0.0, 0.0]`, `tag_truth` defaults to the 3D origin). `geometry.py` keeps
  `gdop`'s dimension-agnostic math unchanged and adds `dop_components(anchor_positions,
  tag_position, distances=None)`, which decomposes the covariance matrix into
  `pdop = sqrt(trace(cov))`, `hdop = sqrt(cov[0,0] + cov[1,1])` and
  `vdop = sqrt(cov[2,2])`. `Tag.dop_components()` exposes this per-tag.
  `Scenario.generate_measurements(tag_estimate, tag_truth)` is a new base-class method
  (synthesizes noisy anchor↔tag distances with stddev `sigma`); `SandboxScenario` builds
  4 non-coplanar anchors (one elevated, e.g. on a mast) + 1 tag and calls it.
- **`data/`** — `import_scenario.py` is unchanged from `gdop` (already dimension-agnostic).
  `importer.py` is a simplified rewrite with no pandas/CSV/streaming: `get_available_scenarios()`
  scans `workspace/*/scenario.json`, and `import_scenario()` loads the JSON and calls
  `generate_measurements()` for each tag against `tag_truth`.
- **`presentation/`** — `trilatplot3d.py`'s `TrilatPlot3D` renders an `Axes3D` scene
  (`ax.scatter`/`_offsets3d` for points, `Line3D.set_data_3d` for anchor-anchor and
  tag-anchor lines, `Text3D`/`set_position_3d` for labels, wireframe spheres
  recreated each update for anchor distance uncertainty, and an `ax.text2D` HUD overlay for
  PDOP/HDOP/VDOP). View navigation is mpl's standard `Axes3D` rotate/zoom — there is **no**
  drag-to-move or right-click anchor editing. All position editing goes through
  `tabs/tree_tab.py`'s `StationDialog` (a QDialog with name + X/Y/Z `QDoubleSpinBox` fields),
  used for both "Add Anchor" and editing existing stations. `tabs/` is reduced to
  `TreeTab`, `DisplayTab`, `SandboxTab` (no `DataTab`/`PlotTab`); `mainwindow.py` has a single
  3D canvas and no `ComparisonPlot`. `displayconfig.py`'s flags are
  `showAnchorSpheres`, `showAnchorLabels`, `showBetweenAnchorsLines`,
  `showBetweenAnchorsLabels`, `showTagAnchorLines`, `showTagAnchorLabels`, `showTagLabels`,
  `showGDOP` (no `rightClickAnchors`/`dragAnchors`).

CSV import, SSE/MQTT streaming, and the scenario-comparison plot from `gdop` are intentionally
out of scope for `pdop`.

## Workspace data format

`workspace/<scenario_name>/` holds:
- `scenario.json` — station layout: `{"stations": [{"name", "type": "ANCHOR"|"TAG", "position": [x, y]}, ...]}`
  in `gdop` (2D) or `[x, y, z]` in `pdop` (3D). ANCHOR entries require `position`; a TAG
  entry's optional `position` becomes `tag_truth`.
- `rtt-log-*.csv` — RTT measurement logs with columns including `time(ms)`, `true_range(m)`,
  `est._range(m)`, `std_dev(m)`, `ap-ssid` (column names are normalized/lower-cased on read).
  `gdop` only — `pdop` has no CSV import.

## Current research context

This codebase supports research at 千葉工業大学 未来ロボティクス学科 上田研究室 on the impact of
extraterrestrial disturbances (Mars dust, NLOS terrain occlusion) on 3D UWB positioning for
planetary exploration. The 3D extension (≥4 non-coplanar anchors, PDOP/HDOP/VDOP) is
implemented in `pdop/` (see "Architecture (pdop)" above). See
`_Dev/context/projects/研究.md` in AkariVault for full research context.
