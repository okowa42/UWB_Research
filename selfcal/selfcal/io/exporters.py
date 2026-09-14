"""long-format CSV 出力(§7)。

1試行 = 1行。列は行 dict のキー和集合(欠損は空欄)。決定的な列順で書き出す。

V-6 の「同一 seed → CSV 完全一致」は *同一環境内* でのみ成立する。numpy/scipy/BLAS
が変わると LM の収束経路が変わり個別試行値はズレる(2026-09-14 実測: 分布は一致、
全行の値は不一致)。出自は provenance.write_meta が別途 .meta.json に記録する。
標準ライブラリのみ使用。
"""
from __future__ import annotations

import csv
import pathlib
from typing import Iterable, Mapping, Sequence


def _ordered_fields(rows: Sequence[Mapping]) -> list[str]:
    """識別子列を先頭に固定し、残りは初出順で安定化した列順を返す。"""
    preferred = [
        "condition_id", "trial_id", "n_anchors", "gauge", "dof",
        "sigma_r_mm", "sigma_deploy_mm", "sigma_v_mm",
    ]
    seen: list[str] = []
    for row in rows:
        for key in row:
            if key not in seen:
                seen.append(key)
    head = [k for k in preferred if k in seen]
    tail = [k for k in seen if k not in head]
    return head + tail


def write_long_csv(rows: Iterable[Mapping], path: str | pathlib.Path) -> pathlib.Path:
    """行 dict の列を CSV へ書き出し、書き込んだパスを返す。"""
    rows = list(rows)
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = _ordered_fields(rows) if rows else []
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path
