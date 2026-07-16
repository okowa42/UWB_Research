"""selfcal — 月面UWBアンカー自己校正シミュレーション(案B, ヘッドレス)。

依存方向は selfcal/ -> pdop.simulation.geometry の単方向のみ(pdop は変更しない)。
単位はすべて mm / deg / s。乱数は rng.py の Generator 経由に統一する
(グローバル np.random 禁止 = V-6 再現性の要)。
"""

__version__ = "0.1.0"
