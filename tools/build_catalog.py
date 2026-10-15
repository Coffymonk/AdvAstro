"""Build src/advastro/data/openngc.csv from the OpenNGC database.

OpenNGC by Mattia Verga, https://github.com/mattiaverga/OpenNGC, CC-BY-SA-4.0.
Usage: python tools/build_catalog.py path/to/NGC.csv path/to/addendum.csv

Keeps real deep-sky objects (drops duplicates, single stars and non-existent
entries), converts coordinates to degrees and collects every alias (Messier,
Caldwell, NGC/IC cross-references, LBN, Barnard, ...) for name lookups.
"""

import csv
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "src" / "advastro" / "data" / "openngc.csv"
SKIP_TYPES = {"Dup", "NonEx", "*", "**", "Nova", "Other"}
ALIAS_PREFIXES = ("C ", "LBN ", "LDN ", "Sh2", "B ", "vdB", "Ced ", "Mel ", "Cr ", "Abell ",
                  "PK ", "UGC ", "PGC ", "Arp ", "Barnard", "Stock ", "Tr ", "Berkeley ")


def pretty(name: str) -> str:
    """NGC0224 -> NGC 224, IC0434 -> IC 434, B033 -> B 33, C009 -> C 9."""
    m = re.fullmatch(r"([A-Za-z]+)0*(\d+)(.*)", name)
    return f"{m.group(1)} {m.group(2)}{m.group(3)}" if m else name


def hms(text: str, hours: bool) -> float | None:
    if not text:
        return None
    sign = -1.0 if text.strip().startswith("-") else 1.0
    d, m, s = (abs(float(x)) for x in text.replace("+", "").replace("-", "").split(":"))
    deg = sign * (d + m / 60 + s / 3600)
    return round(deg * 15 if hours else deg, 5)


def aliases(row: dict) -> list[str]:
    out = []
    if row.get("M"):
        out.append(f"M {int(row['M'])}")
    if row.get("NGC"):
        out += [f"NGC {int(x)}" for x in row["NGC"].split(",") if x.strip().isdigit()]
    if row.get("IC"):
        out += [f"IC {int(x)}" for x in row["IC"].split(",") if x.strip().isdigit()]
    for ident in (row.get("Identifiers") or "").split(","):
        ident = ident.strip()
        if ident.startswith(ALIAS_PREFIXES):
            out.append(re.sub(r"^(\w+) 0*(\d)", r"\1 \2", ident))
    return out


def main(ngc: str, addendum: str) -> None:
    rows = []
    for path in (ngc, addendum):
        with open(path, encoding="utf-8") as fh:
            rows += list(csv.DictReader(fh, delimiter=";"))
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "type", "ra", "dec", "const", "maj", "min", "pa", "mag", "aliases",
                    "names"])
        kept = 0
        for r in rows:
            if r["Type"] in SKIP_TYPES or not r["RA"]:
                continue
            mag = r.get("V-Mag") or r.get("B-Mag") or ""
            w.writerow([pretty(r["Name"]), r["Type"], hms(r["RA"], True), hms(r["Dec"], False),
                        r["Const"], r["MajAx"], r["MinAx"], r["PosAng"], mag,
                        "|".join(aliases(r)), "|".join(
                            n.strip() for n in (r.get("Common names") or "").split(",")
                            if n.strip())])
            kept += 1
    print(f"wrote {kept} objects to {OUT}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
