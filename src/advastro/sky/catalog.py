"""Deep-sky object catalog (OpenNGC): look up objects by name or by position."""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

import numpy as np

# OpenNGC type codes -> (description key, processing family)
TYPES = {
    "G": ("galaxy", "galaxy"),
    "GPair": ("galaxy_pair", "galaxy"),
    "GTrpl": ("galaxy_triplet", "galaxy"),
    "GGroup": ("galaxy_group", "galaxy"),
    "HII": ("hii_region", "emission"),
    "EmN": ("emission_nebula", "emission"),
    "Neb": ("nebula", "emission"),
    "Cl+N": ("cluster_nebula", "emission"),
    "SNR": ("supernova_remnant", "emission"),
    "RfN": ("reflection_nebula", "reflection"),
    "DrkN": ("dark_nebula", "reflection"),
    "PN": ("planetary_nebula", "planetary"),
    "OCl": ("open_cluster", "cluster"),
    "*Ass": ("stellar_association", "cluster"),
    "GCl": ("globular_cluster", "globular"),
}
FAMILIES = ("galaxy", "emission", "reflection", "planetary", "cluster", "globular")


@dataclass
class SkyObject:
    id: str
    type: str
    ra: float
    dec: float
    constellation: str
    major_arcmin: float | None
    minor_arcmin: float | None
    position_angle: float | None
    magnitude: float | None
    aliases: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)

    @property
    def type_key(self) -> str:
        return TYPES.get(self.type, ("object", "unknown"))[0]

    @property
    def family(self) -> str:
        return TYPES.get(self.type, ("object", "unknown"))[1]

    @property
    def common_name(self) -> str | None:
        return self.names[0] if self.names else None

    @property
    def messier(self) -> str | None:
        return next((a for a in self.aliases if a.startswith("M ")), None)

    @property
    def label(self) -> str:
        """Best short label: common name, else Messier number, else catalog id."""
        return self.common_name or self.messier or self.id

    @property
    def designations(self) -> list[str]:
        """Catalog ids in a sensible order: Messier first, then the main id, then aliases."""
        out = [a for a in (self.messier,) if a]
        out.append(self.id)
        out += [a for a in self.aliases if a not in out and not a.startswith(("PGC", "UGC"))]
        return out


def normalize(name: str) -> str:
    """'NGC 0224', 'ngc224', 'NGC-224' -> 'NGC224'; 'Sh 2-155' -> 'SH2155'."""
    text = re.sub(r"[\s_\-]+", "", name.upper())
    text = text.replace("MESSIER", "M").replace("CALDWELL", "C")
    return re.sub(r"(?<=[A-Z])0+(?=\d)", "", text)


class Catalog:
    def __init__(self, objects: list[SkyObject]) -> None:
        self.objects = objects
        self._index: dict[str, SkyObject] = {}
        for obj in objects:
            for key in [obj.id, *obj.aliases]:
                self._index.setdefault(normalize(key), obj)
        for obj in objects:  # common names last, so ids win on conflicts
            for name in obj.names:
                self._index.setdefault(normalize(name), obj)
        ra = np.radians([o.ra for o in objects])
        dec = np.radians([o.dec for o in objects])
        self._xyz = np.stack([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)], 1)

    def by_name(self, name: str | None) -> SkyObject | None:
        if not name:
            return None
        key = normalize(name)
        if key in self._index:
            return self._index[key]
        # "NGC 7000 North America", "M31_Andromeda": try leading designation tokens.
        m = re.match(r"\s*((?:NGC|IC|M|C|B|LBN|LDN|SH2|VDB|CED|MEL|CR|SH)\s*[-_ ]?\s*\d+)",
                     name, re.IGNORECASE)
        if m and normalize(m.group(1)) in self._index:
            return self._index[normalize(m.group(1))]
        folded = name.casefold().strip()
        if len(folded) >= 5:
            for obj in self.objects:
                if any(folded in n.casefold() for n in obj.names):
                    return obj
        return None

    def cone(self, ra: float, dec: float, radius_deg: float) -> list[tuple[SkyObject, float]]:
        """Objects within radius of a position, with their separation in degrees."""
        r, d = math.radians(ra), math.radians(dec)
        v = np.array([math.cos(d) * math.cos(r), math.cos(d) * math.sin(r), math.sin(d)])
        sep = np.degrees(np.arccos(np.clip(self._xyz @ v, -1.0, 1.0)))
        idx = np.nonzero(sep <= radius_deg)[0]
        return sorted(((self.objects[i], float(sep[i])) for i in idx), key=lambda t: t[1])


def _num(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


@cache
def load() -> Catalog:
    text = resources.files("advastro.data").joinpath("openngc.csv").read_text("utf-8")
    objects = []
    for row in csv.DictReader(text.splitlines()):
        objects.append(SkyObject(
            id=row["id"], type=row["type"], ra=float(row["ra"]), dec=float(row["dec"]),
            constellation=row["const"], major_arcmin=_num(row["maj"]),
            minor_arcmin=_num(row["min"]), position_angle=_num(row["pa"]),
            magnitude=_num(row["mag"]),
            aliases=[a for a in row["aliases"].split("|") if a],
            names=[n for n in row["names"].split("|") if n],
        ))
    return Catalog(objects)
