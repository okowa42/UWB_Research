# architecture-gdop — gdop（2D原本）のアーキテクチャ

> CLAUDE.md から参照される詳細ルール。gdop で作業するとき読むこと。

## Repository layout

This top-level directory is not itself a git repo; it bundles separate research projects:

- `gdop/` — the original project. A PyQt5/matplotlib desktop app for real-time 2D GDOP/PDOP
  (Geometric/Position Dilution of Precision) calculation and visualization of UWB anchor/tag
  setups. This is its own git repository (forked from `schwarzfelix/gdop`).
- `pdop/` — the 3D extension of the GDOP work (see `rules/research-context.md`). Mirrors
  `gdop/`'s three-layer structure but with 3D (`[x, y, z]`) positions, PDOP/HDOP/VDOP, and a
  trimmed-down feature set (no CSV import, streaming, or scenario-comparison plot). Not a git
  repo. See `rules/architecture-pdop.md` for the differences from `gdop/`.

Commands below assume `cd gdop` or `cd pdop` respectively.

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

## Workspace data format

`workspace/<scenario_name>/` holds:
- `scenario.json` — station layout: `{"stations": [{"name", "type": "ANCHOR"|"TAG", "position": [x, y]}, ...]}`
  in `gdop` (2D) or `[x, y, z]` in `pdop` (3D). ANCHOR entries require `position`; a TAG
  entry's optional `position` becomes `tag_truth`.
- `rtt-log-*.csv` — RTT measurement logs with columns including `time(ms)`, `true_range(m)`,
  `est._range(m)`, `std_dev(m)`, `ap-ssid` (column names are normalized/lower-cased on read).
  `gdop` only — `pdop` has no CSV import.
