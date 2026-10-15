"""Where is the image pointing? Three levels of certainty, best first.

1. solved:     a real astrometric solution, from WCS keywords already in the file
               (PixInsight ImageSolver, ASTAP, NINA...) or from running ASTAP.
2. pointing:   the telescope's reported RA/Dec plus the image scale; centre is
               approximate (mount pointing error) and rotation unknown.
3. none:       no position at all.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from astropy.io import fits as afits

from advastro.frame import Frame

ASTAP_DB = re.compile(r"^([a-z]\d\d)_\d{4}\.\w+$", re.IGNORECASE)


@dataclass
class SkyField:
    ra: float                    # centre, degrees
    dec: float
    width_deg: float
    height_deg: float
    scale_arcsec: float          # per native pixel
    rotation_deg: float | None   # north angle; None when unknown
    level: str                   # "solved" | "pointing"
    source: str                  # human description of where it came from
    flipped: bool | None = None
    seconds: float | None = None
    wcs: dict | None = None      # FITS WCS keywords for native pixels, when solved

    @property
    def radius_deg(self) -> float:
        return 0.5 * math.hypot(self.width_deg, self.height_deg)

    def contains(self, ra: float, dec: float, margin: float = 0.0) -> bool:
        """Is a position inside the frame? Uses rotation when known, else a circle."""
        x, y = _tangent(ra, dec, self.ra, self.dec)
        if self.rotation_deg is None:
            return math.hypot(x, y) <= 0.5 * min(self.width_deg, self.height_deg) + margin
        a = math.radians(self.rotation_deg)
        u = x * math.cos(a) + y * math.sin(a)
        v = -x * math.sin(a) + y * math.cos(a)
        return abs(u) <= self.width_deg / 2 + margin and abs(v) <= self.height_deg / 2 + margin


def _tangent(ra: float, dec: float, ra0: float, dec0: float) -> tuple[float, float]:
    """Gnomonic projection offsets in degrees (east, north)."""
    r, d, r0, d0 = map(math.radians, (ra, dec, ra0, dec0))
    cosc = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(r - r0)
    if cosc <= 0:
        return 180.0, 180.0
    x = math.cos(d) * math.sin(r - r0) / cosc
    y = (math.cos(d0) * math.sin(d) - math.sin(d0) * math.cos(d) * math.cos(r - r0)) / cosc
    return math.degrees(x), math.degrees(y)


# ---- 1a: solution already in the file ------------------------------------------
def field_from_wcs_header(header: dict, width: int, height: int) -> SkyField | None:
    if not str(header.get("CTYPE1", "")).startswith("RA") or "CRVAL1" not in header:
        return None
    try:
        from astropy.wcs import WCS

        hdr = afits.Header()
        for k, v in header.items():
            if isinstance(k, str) and len(k) <= 8:
                try:
                    hdr[k] = v
                except (ValueError, KeyError):
                    pass
        hdr["NAXIS"], hdr["NAXIS1"], hdr["NAXIS2"] = 2, width, height
        w = WCS(hdr, naxis=2)
        center = w.pixel_to_world_values(width / 2 - 0.5, height / 2 - 0.5)
        scales = w.proj_plane_pixel_scales()
        scale = float(np.mean([s.to_value("deg") if hasattr(s, "to_value") else s
                               for s in scales])) * 3600
        cd = w.pixel_scale_matrix
        rotation = math.degrees(math.atan2(cd[1, 0], cd[1, 1])) % 360
        flipped = bool(np.linalg.det(cd) > 0)
    except Exception:
        return None
    keep = ("CTYPE1", "CTYPE2", "CRVAL1", "CRVAL2", "CRPIX1", "CRPIX2", "CD1_1", "CD1_2",
            "CD2_1", "CD2_2", "CDELT1", "CDELT2", "CROTA1", "CROTA2", "PC1_1", "PC1_2", "PC2_1",
            "PC2_2", "CUNIT1", "CUNIT2", "EQUINOX", "RADESYS", "LONPOLE", "LATPOLE")
    wcs_keys = {k: header[k] for k in keep if k in header}
    wcs_keys.update({k: v for k, v in header.items()
                     if isinstance(k, str) and k[:2] in ("A_", "B_") and k[2:3].isdigit()})
    for k in ("A_ORDER", "B_ORDER"):
        if k in header:
            wcs_keys[k] = header[k]
    return SkyField(
        wcs=wcs_keys,
        ra=float(center[0]) % 360, dec=float(center[1]),
        width_deg=width * scale / 3600, height_deg=height * scale / 3600,
        scale_arcsec=scale, rotation_deg=rotation, level="solved",
        source="ASTAP solution in the file" if header.get("PLTSOLVD") else
        "solution in the file header",
        flipped=flipped)


# ---- 2: telescope pointing ---------------------------------------------------------
def field_from_pointing(frame: Frame, scale_arcsec: float | None) -> SkyField | None:
    m = frame.meta
    scale = m.pixel_scale_arcsec or scale_arcsec
    if m.ra_deg is None or m.dec_deg is None or not scale:
        return None
    h, w = frame.data.shape[-2:]
    return SkyField(ra=m.ra_deg % 360, dec=m.dec_deg, width_deg=w * scale / 3600,
                    height_deg=h * scale / 3600, scale_arcsec=scale, rotation_deg=None,
                    level="pointing", source="telescope pointing in the file header")


# ---- 1b: ASTAP -------------------------------------------------------------------------
@dataclass
class AstapInstall:
    executable: Path | None
    database_dir: Path | None
    databases: list[str]

    @property
    def ready(self) -> bool:
        return self.executable is not None and bool(self.databases)


def _candidates() -> list[Path]:
    names = ["astap_cli", "astap"]
    found = [Path(p) for n in names if (p := shutil.which(n))]
    if sys.platform == "win32":
        for base in filter(None, [os.environ.get("ProgramFiles"),
                                  os.environ.get("ProgramFiles(x86)"),
                                  os.environ.get("LOCALAPPDATA")]):
            found += [Path(base) / "astap" / "astap_cli.exe", Path(base) / "astap" / "astap.exe"]
        found += [Path("C:/astap/astap_cli.exe"), Path("C:/astap/astap.exe")]
    elif sys.platform == "darwin":
        found += [Path("/Applications/ASTAP.app/Contents/MacOS/astap"),
                  Path("/Applications/astap.app/Contents/MacOS/astap"),
                  Path("/usr/local/bin/astap_cli"), Path("/opt/homebrew/bin/astap_cli"),
                  Path("/usr/local/opt/astap/astap_cli")]
    else:
        found += [Path("/opt/astap/astap_cli"), Path("/opt/astap/astap"),
                  Path("/usr/bin/astap_cli"), Path("/usr/local/bin/astap_cli")]
    return found


def _database_dirs(executable: Path | None) -> list[Path]:
    dirs = []
    if executable:
        dirs += [executable.parent, executable.parent.parent / "Resources"]
    if sys.platform == "win32":
        for base in filter(None, [os.environ.get("ProgramFiles"),
                                  os.environ.get("ProgramFiles(x86)"),
                                  os.environ.get("LOCALAPPDATA")]):
            dirs.append(Path(base) / "astap")
        dirs.append(Path("C:/astap"))
    elif sys.platform == "darwin":
        dirs += [Path("/usr/local/opt/astap"), Path("/opt/homebrew/opt/astap"),
                 Path.home() / "Library" / "Application Support" / "astap"]
    else:
        dirs += [Path("/opt/astap"), Path("/usr/share/astap"), Path.home() / ".astap"]
    return dirs


def list_databases(folder: Path | None) -> list[str]:
    if not folder or not folder.is_dir():
        return []
    try:
        names = [f.name for f in folder.iterdir()]
    except OSError:
        return []
    return sorted({m.group(1).upper() for n in names if (m := ASTAP_DB.match(n))})


def find_database_dir(folder: Path | None) -> Path | None:
    """The folder holding star databases: the folder itself or one of its subfolders.

    ASTAP's Windows installer puts the databases in a 'Database' subfolder of the
    program folder; other layouts keep them next to the program.
    """
    if not folder or not folder.is_dir():
        return None
    if list_databases(folder):
        return folder
    try:
        children = sorted((c for c in folder.iterdir() if c.is_dir()),
                          key=lambda c: c.name.lower() not in ("database", "databases"))
    except OSError:
        return None
    return next((c for c in children if list_databases(c)), None)


def detect_astap(executable: str = "", database_dir: str = "") -> AstapInstall:
    """Find ASTAP and its star databases. Configured paths win over detection."""
    exe = Path(executable) if executable else None
    if exe is not None and exe.is_dir():  # the user picked the ASTAP folder
        exe = next((exe / n for n in ("astap_cli.exe", "astap_cli", "astap.exe", "astap")
                    if (exe / n).is_file()), None)
    if exe is None or not exe.is_file():
        exe = next((p for p in _candidates() if p.is_file()), None)
    db_dir = find_database_dir(Path(database_dir)) if database_dir else None
    if db_dir is None:
        db_dir = next((d for d in map(find_database_dir, _database_dirs(exe)) if d), None)
    return AstapInstall(exe, db_dir, list_databases(db_dir))


def _solver_image(frame: Frame) -> tuple[np.ndarray, int]:
    """Mono image for solving; colour (CFA) data as 2x2 superpixels. Returns (image, bin)."""
    from advastro.engine.metrics import luminance_plane

    img, factor = luminance_plane(frame)
    lo, hi = np.percentile(img, [1, 99.98])
    scaled = np.clip((img - lo) / max(hi - lo, 1e-9), 0, 1) * 65535
    return scaled.astype(np.uint16), factor


def parse_astap_ini(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip().upper()] = v.split("/")[0].strip().strip("'")
    return out


class SolveError(RuntimeError):
    pass


def solve_astap(frame: Frame, install: AstapInstall, scale_hint: float | None = None,
                radius_deg: float = 30.0, timeout_s: float = 90.0,
                downsample: int = 0, auto_fov: bool = False) -> SkyField:
    """Plate solve with ASTAP on a temporary FITS copy; never writes next to user files."""
    if not install.executable:
        raise SolveError("ASTAP was not found")
    if not install.databases:
        raise SolveError("No ASTAP star database was found")
    img, factor = _solver_image(frame)
    h, w = img.shape
    m = frame.meta
    scale = m.pixel_scale_arcsec or scale_hint
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="advastro-solve-") as tmp:
        src = Path(tmp) / "solve.fits"
        hdr = afits.Header()
        if m.ra_deg is not None and m.dec_deg is not None:
            hdr["RA"], hdr["DEC"] = m.ra_deg, m.dec_deg
        afits.PrimaryHDU(img, header=hdr).writeto(src)
        cmd = [str(install.executable), "-f", str(src), "-r", f"{radius_deg:g}",
               "-z", str(downsample), "-o", str(Path(tmp) / "solution"), "-wcs"]
        if scale:
            cmd += ["-fov", f"{h * factor * scale / 3600:.4f}"]
        elif auto_fov:
            cmd += ["-fov", "0"]          # ASTAP tries a range of field sizes
        if m.ra_deg is not None and m.dec_deg is not None:
            cmd += ["-ra", f"{m.ra_deg / 15:.6f}", "-spd", f"{m.dec_deg + 90:.6f}"]
        if install.database_dir:
            cmd += ["-d", str(install.database_dir)]
        try:
            subprocess.run(cmd, capture_output=True, timeout=timeout_s,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired as exc:
            raise SolveError(f"ASTAP did not finish within {timeout_s:.0f} s") from exc
        except OSError as exc:
            raise SolveError(f"Could not start ASTAP: {exc}") from exc
        ini_path = Path(tmp) / "solution.ini"
        if not ini_path.exists():
            raise SolveError("ASTAP did not write a result")
        ini = parse_astap_ini(ini_path.read_text(errors="replace"))
    if ini.get("PLTSOLVD", "F").upper() != "T":
        reason = ini.get("ERROR") or ini.get("WARNING") or "no match with the star database"
        raise SolveError(f"Plate solving failed: {reason}")
    try:
        ra, dec = float(ini["CRVAL1"]), float(ini["CRVAL2"])
        if "CD1_1" in ini:
            cd = np.array([[float(ini["CD1_1"]), float(ini["CD1_2"])],
                           [float(ini["CD2_1"]), float(ini["CD2_2"])]])
        else:
            c1, c2 = float(ini["CDELT1"]), float(ini["CDELT2"])
            rot = math.radians(float(ini.get("CROTA2", 0)))
            cd = np.array([[c1 * math.cos(rot), -c2 * math.sin(rot)],
                           [c1 * math.sin(rot), c2 * math.cos(rot)]])
    except (KeyError, ValueError) as exc:
        raise SolveError("ASTAP result could not be read") from exc
    binned_scale = math.sqrt(abs(np.linalg.det(cd))) * 3600
    try:
        crpix = ((float(ini["CRPIX1"]) - 0.5) * factor + 0.5,
                 (float(ini["CRPIX2"]) - 0.5) * factor + 0.5)
    except (KeyError, ValueError):
        crpix = (w * factor / 2 + 0.5, h * factor / 2 + 0.5)
    wcs = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRVAL1": ra, "CRVAL2": dec,
           "CRPIX1": crpix[0], "CRPIX2": crpix[1], "CD1_1": cd[0, 0] / factor,
           "CD1_2": cd[0, 1] / factor, "CD2_1": cd[1, 0] / factor, "CD2_2": cd[1, 1] / factor}
    native = binned_scale / factor
    full_h, full_w = frame.data.shape[-2:]
    return SkyField(
        ra=ra % 360, dec=dec, width_deg=full_w * native / 3600, height_deg=full_h * native / 3600,
        scale_arcsec=native, rotation_deg=math.degrees(math.atan2(cd[1, 0], cd[1, 1])) % 360,
        level="solved", source="ASTAP", flipped=bool(np.linalg.det(cd) > 0),
        seconds=time.monotonic() - started, wcs=wcs)


def locate(frame: Frame, scale_hint: float | None = None) -> SkyField | None:
    """Best position available without running a solver."""
    h, w = frame.data.shape[-2:]
    return field_from_wcs_header(frame.meta.raw_header, w, h) or \
        field_from_pointing(frame, scale_hint)
