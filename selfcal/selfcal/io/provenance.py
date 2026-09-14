"""実験結果の出自メタデータ(§7 V-6 補強)。

CSV と同時に `<csv名>.meta.json` を書き出し、「どのコード・どの環境で生成したか」を
CSV 自身から追跡できるようにする。V-6 の「同一 seed → CSV 完全一致」は *同一環境内*
でのみ成立し、numpy/scipy/BLAS が変われば LM の収束経路が変わって個別試行値はズレる。
そのため seed だけでなく commit と環境を必ず併記する(2026-09-14 の実測で確認済み)。

標準ライブラリ + numpy/scipy のみ使用。git が無い環境でも例外を出さない。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import socket
import subprocess
import sys
from typing import Any

SCHEMA_VERSION = 1


def _git(args: list[str], cwd: pathlib.Path) -> str | None:
    """git サブコマンドを実行し stdout を返す。失敗時は None(例外を投げない)。"""
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10,
            # Windows の既定ロケールは cp932。git の出力(日本語のコミット件名や
            # ファイル名)を復号できず UnicodeDecodeError になるため明示する。
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    # strip() は使わない。`git status --porcelain` の 1 行目の先頭スペース
    # (" M path" の XY 欄)まで削ってしまい、パスが 1 文字欠ける。
    return out.stdout.rstrip("\n")


def git_info(repo: pathlib.Path) -> dict[str, Any]:
    """HEAD の commit / branch と working tree の dirty 状態を集める。"""
    commit = _git(["rev-parse", "HEAD"], repo)
    if commit is None:
        return {"available": False}
    status = _git(["status", "--porcelain"], repo)
    return {
        "available": True,
        "commit": commit,
        "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"], repo),
        # dirty=True の結果は再現不能。論文に使う数値は必ず False で取り直すこと。
        "dirty": bool(status),
        "dirty_files": [ln[3:] for ln in status.splitlines()] if status else [],
    }


def env_info() -> dict[str, Any]:
    """実行環境(Python・数値ライブラリ・BLAS・OS)を集める。"""
    info: dict[str, Any] = {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "hostname": socket.gethostname(),
    }
    try:
        import numpy
        info["numpy"] = numpy.__version__
        # BLAS 実装の違いが LM の収束経路を変えるため記録する。
        try:
            cfg = numpy.show_config(mode="dicts")  # numpy >= 1.25
            blas = (cfg or {}).get("Build Dependencies", {}).get("blas", {})
            info["blas"] = {k: blas[k] for k in ("name", "version") if k in blas}
        except (TypeError, AttributeError, KeyError):
            info["blas"] = None
    except ImportError:
        info["numpy"] = None
    try:
        import scipy
        info["scipy"] = scipy.__version__
    except ImportError:
        info["scipy"] = None
    return info


def sha256_file(path: pathlib.Path) -> str:
    """CSV 本体のハッシュ。meta と CSV の対応が壊れていないか後から検証できる。"""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_meta(
    csv_path: pathlib.Path,
    exp_id: str,
    cfg: dict,
    n_rows: int,
    repo: pathlib.Path | None = None,
) -> dict[str, Any]:
    """CSV に添えるメタデータ dict を組み立てる。"""
    csv_path = pathlib.Path(csv_path)
    repo = repo or pathlib.Path(__file__).resolve().parents[3]
    return {
        "schema": SCHEMA_VERSION,
        "exp_id": exp_id,
        "csv": csv_path.name,
        "csv_sha256": sha256_file(csv_path),
        "rows": n_rows,
        "generated_at": datetime.datetime.now().astimezone().isoformat(),
        "seed": cfg.get("montecarlo", {}).get("seed"),
        "n_mc": cfg.get("montecarlo", {}).get("n_mc"),
        "git": git_info(repo),
        "env": env_info(),
        "config": cfg,
    }


def write_meta(
    csv_path: str | pathlib.Path,
    exp_id: str,
    cfg: dict,
    n_rows: int,
    repo: pathlib.Path | None = None,
) -> pathlib.Path:
    """`<csv名>.meta.json` を CSV の隣に書き出し、そのパスを返す。"""
    csv_path = pathlib.Path(csv_path)
    meta = build_meta(csv_path, exp_id, cfg, n_rows, repo=repo)
    out = csv_path.with_suffix(csv_path.suffix + ".meta.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")
    return out
