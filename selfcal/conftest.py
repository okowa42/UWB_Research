"""pytest 用ブートストラップ。

`selfcal` パッケージ(<repo>/selfcal/selfcal)と、依存先 `pdop`(<repo>/pdop)の
両方を import 可能にするため、リポジトリルートと selfcal プロジェクトディレクトリを
sys.path へ追加する。
"""
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent      # <repo>/selfcal
_ROOT = _HERE.parent                                  # <repo>

for _p in (str(_HERE), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
