import math
import stat
import sys
import textwrap

import pytest
from synthetic import star_field, write_fits

from advastro.readers import read_frame
from advastro.sky.catalog import load
from advastro.sky.identify import identify
from advastro.sky.solve import (
    SkyField,
    SolveError,
    detect_astap,
    field_from_pointing,
    locate,
    parse_astap_ini,
    solve_astap,
)

WCS = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRPIX1": 200.5, "CRPIX2": 150.5,
       "CRVAL1": 314.82, "CRVAL2": 44.53, "CD1_1": -4.76e-4, "CD1_2": 0.0,
       "CD2_1": 0.0, "CD2_2": 4.76e-4}


def test_catalog_lookup_by_any_name():
    c = load()
    for name in ("M31", "NGC 224", "ngc0224", "Andromeda Galaxy"):
        assert c.by_name(name).id == "NGC 224"
    assert c.by_name("C 20").label == "North America Nebula"
    assert c.by_name("NGC7000_NorthAmerica_2026").id == "NGC 7000"
    assert c.by_name("Not a real object") is None


def test_wcs_in_header_means_solved(tmp_path):
    path = write_fits(tmp_path / "solved.fits", star_field(shape=(300, 400)), **WCS)
    sky = locate(read_frame(path))
    assert sky.level == "solved"
    assert sky.ra == pytest.approx(314.82, abs=1e-3) and sky.dec == pytest.approx(44.53, abs=1e-3)
    assert sky.scale_arcsec == pytest.approx(1.714, abs=0.01)


def test_pointing_fallback(tmp_path):
    path = write_fits(tmp_path / "p.fits", star_field(shape=(300, 400)), RA=10.68, DEC=41.27)
    sky = locate(read_frame(path))
    assert sky.level == "pointing" and sky.rotation_deg is None


def test_identify_solved_field_and_neighbours():
    sky = SkyField(ra=314.68, dec=44.04, width_deg=1.83, height_deg=1.03, scale_arcsec=1.71,
                   rotation_deg=107.5, level="solved", source="test")
    r = identify(sky, [])
    assert r.target.id == "NGC 7000" and r.family == "emission"
    assert r.constellation == "Cygnus" and r.milky_way
    assert r.framing == "fills_field"
    assert any(o.id == "NGC 6997" for o in r.others)


def test_identify_by_name_only_and_unknown():
    r = identify(None, ["M 51"])
    assert r.confidence == "name" and r.family == "galaxy"
    assert identify(None, ["no such thing"]).confidence == "none"


def test_small_galaxy_framing():
    sky = SkyField(ra=202.47, dec=47.2, width_deg=1.83, height_deg=1.03, scale_arcsec=1.71,
                   rotation_deg=0, level="solved", source="test")
    r = identify(sky, [])
    assert r.target.messier == "M 51" and r.framing in ("small", "tiny", "well_framed")


def test_parse_astap_ini():
    ini = parse_astap_ini("PLTSOLVD=T\nCRVAL1=314.8\nCRVAL2= 44.5 / comment\nCD1_1=-0.0004\n")
    assert ini["PLTSOLVD"] == "T" and ini["CRVAL2"] == "44.5"


@pytest.mark.skipif(sys.platform == "win32", reason="the fake solver is a shell script")
def test_solve_with_astap_round_trip(tmp_path):
    """A stand-in ASTAP checks our command line and reads back a solution."""
    db = tmp_path / "db"
    db.mkdir()
    (db / "d50_0101.1476").write_bytes(b"")
    fake = tmp_path / "astap_cli"
    fake.write_text(textwrap.dedent(f"""\
        #!{sys.executable}
        import sys
        args = sys.argv[1:]
        out = args[args.index("-o") + 1]
        assert "-f" in args and "-d" in args and "-fov" in args
        open(out + ".ini", "w").write(
            "PLTSOLVD=T\\nCRVAL1=314.8200\\nCRVAL2=44.5300\\n"
            "CD1_1=-9.52E-04\\nCD1_2=0\\nCD2_1=0\\nCD2_2=9.52E-04\\n")
        """))
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    install = detect_astap(str(fake), str(db))
    assert install.ready and install.databases == ["D50"]
    frame = read_frame(write_fits(tmp_path / "x.fits", star_field(shape=(300, 400)),
                                  BAYERPAT="RGGB", RA=314.8, DEC=44.5))
    sky = solve_astap(frame, install)
    assert sky.level == "solved" and sky.source == "ASTAP"
    # The solver saw a 2x2 superpixel image; the scale must come back in native pixels.
    assert sky.scale_arcsec == pytest.approx(1.714, abs=0.01)
    assert math.isclose(sky.ra, 314.82, abs_tol=1e-6)


def test_solve_reports_missing_astap(tmp_path):
    frame = read_frame(write_fits(tmp_path / "x.fits", star_field(shape=(100, 100))))
    with pytest.raises(SolveError):
        solve_astap(frame, detect_astap(str(tmp_path / "nope"), str(tmp_path)))
    assert field_from_pointing(frame, None) is None


def test_databases_in_subfolder_like_windows_installer(tmp_path):
    """ASTAP on Windows: astap_cli.exe in the program folder, databases in 'Database'."""
    program = tmp_path / "astap"
    (program / "Database").mkdir(parents=True)
    exe = program / "astap_cli.exe"
    exe.write_bytes(b"")
    for name in ("d05_0101.1476", "d05_0201.1476", "d20_0101.1476"):
        (program / "Database" / name).write_bytes(b"")
    found = detect_astap(str(exe))
    assert found.ready and found.databases == ["D05", "D20"]
    assert found.database_dir == program / "Database"
    # Pointing at the program folder or at the parent of Database also works.
    assert detect_astap(str(program)).executable == exe
    assert detect_astap(str(exe), str(program)).databases == ["D05", "D20"]
