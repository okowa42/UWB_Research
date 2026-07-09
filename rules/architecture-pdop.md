# architecture-pdop — pdop（3D拡張）のアーキテクチャ

> CLAUDE.md から参照される詳細ルール。pdop で作業するとき読むこと。
> gdop の3層構造・規約は `rules/architecture-gdop.md` を前提とする。

## Architecture (pdop)

`pdop/` mirrors `gdop/`'s three-layer structure (`simulation/` / `data/` / `presentation/`)
and shares its conventions ("Conventions to preserve" in `rules/architecture-gdop.md` applies
here too), but is a 3D, trimmed-down rebuild:

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
