"""Short, readable names for subs whose file names are mostly identical."""

from __future__ import annotations

import re


def short_names(names: list[str]) -> dict[str, str]:
    """Keep only the name parts that differ between files.

    'Light_NGC 7000_300.0s_Bin1_gain201_20261014-212101_287deg_-10.0C_0009.fit'
    becomes '20261014-212101_287deg_0009' when the other parts are the same for all.
    """
    if len(names) < 2:
        return {n: n for n in names}
    tokens = {n: re.split(r"[_ ]", n.rsplit(".", 1)[0]) for n in names}
    common = set.intersection(*(set(t) for t in tokens.values()))
    out = {}
    for n, toks in tokens.items():
        kept = [t for t in toks if t not in common]
        out[n] = "_".join(kept) if kept else n
    return out
