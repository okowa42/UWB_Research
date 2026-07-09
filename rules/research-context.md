# research-context — 研究文脈と STEP 計画

> CLAUDE.md から参照される詳細ルール。研究の背景・現在地を把握するとき読むこと。
> プロジェクト全体の文脈の正本は AkariVault `_Dev/context/projects/研究.md`（Windows側 Cowork が管理）。

## Current research context

This codebase supports research at 千葉工業大学 未来ロボティクス学科 上田研究室 on the impact of
extraterrestrial disturbances (Mars dust, NLOS terrain occlusion) on 3D UWB positioning for
planetary exploration. See `_Dev/context/projects/研究.md` in AkariVault for full research context
and the 3-step research plan (STEP1: 3D conversion, STEP2: dust model, STEP3: NLOS model).

**STEP1 status**: the 3D core engine (≥4 non-coplanar anchors, N-dimensional trilateration,
PDOP/HDOP/VDOP via `geometry.dop_components`) is implemented in `pdop/` (see
`rules/architecture-pdop.md`) and verified working. Still missing for STEP1 completion — a batch
evaluation pipeline: 3D anchor pattern generation (corners/perimeter/circle/grid/random +
height-diverse variants), Monte Carlo 3D RMSE, and computation-time benchmarking, aggregated to
CSV/plots. The sibling project `~/UWB_Sim` (2D, separate repo) already has this batch pipeline
(`scenario/patterns.py`, `simulation/runner.py`'s `run_monte_carlo`, `metrics/profiler.py`,
`scripts/make_pareto.py`) and is the design reference for porting it into `pdop/`.
