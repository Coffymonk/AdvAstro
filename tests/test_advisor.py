import pytest

from advastro.advisor.engine import advise, render, to_markdown
from advastro.advisor.expr import ExpressionError, evaluate


def base_facts(**over):
    f = dict(total=40, kept=36, rejected=4, exposure_s=300, integration_h=3.0, fwhm_px=2.8,
             fwhm_arcsec=4.8, ecc=0.3, stars=600, snr=80, gradient_pct=6, gradient_spread=4,
             sampling="well sampled", scale=1.71, dithered=True, dither_px=8, drift_px=20,
             best_sub="best.fits", best_fwhm=2.5, is_osc=True, bayer="RGGB", filter=None,
             dual_band=False, is_color=True, temp_text="-10 °C", bortle=5, bortle_text="",
             has_darks=True, has_flats=True, has_bias=True, has_darkflats=False,
             cal_list="darks, flats and bias", cal_found="20 darks", cosmetic_extra="",
             solved=True, located=True, family="emission", target_label="Test Nebula",
             target_mag=6.0, framing="well_framed", coverage=0.5, coverage_pct=50,
             milky_way=False, abs_b=30, fov_w=110, fov_h=62, bright_core=False,
             has_pixinsight=True, has_siril=True, graxpert=False, starnet=True, bxt=False,
             nxt=False, sxt=False, aesthetic="natural", skill="intermediate",
             drizzle_recommended=False, drizzle_scale=None, drizzle_reason=None,
             bayer_drizzle=False, drift_note="", gradient_strength="", gradient_reason="g",
             solve_reason="s", color_reason="c", deconv_target="", palette_text="HOO",
             sho_note="", stretch_reason="st", contrast_reason="lc", saturation_reason="sat",
             milky_way_note="", panels=None, cal_issue_count=0, cal_issues="",
             flat_cal="the flat darks", dark_optimize="on", dark_glow=False, darks_match=True)
    f.update(over)
    return f


def ids(advice):
    return {r.id for r in advice.insights + advice.steps}


def test_expressions_are_safe():
    assert evaluate("kept < 8 and family in ['galaxy']", {"kept": 5, "family": "galaxy"})
    assert evaluate("missing > 3", {}) is False
    assert evaluate("'a' if x else 'b'", {"x": None}) == "b"
    for bad in ["__import__('os')", "open('x')", "x.__class__", "[i for i in y]"]:
        with pytest.raises(ExpressionError):
            evaluate(bad, {"x": 1, "y": [1]})


def test_render_never_fails():
    assert render("{a:.1f} {b} {c:.2f}", {"a": 1.234, "c": "n/a"}) == "1.2 ? n/a"


def test_galaxy_and_nebula_get_different_workflows():
    neb = ids(advise(base_facts()))
    gal = ids(advise(base_facts(family="galaxy", bright_core=True)))
    assert "star_separation" in neb and "star_separation" not in gal
    assert "hdr" in gal and "hdr" not in neb
    cl = ids(advise(base_facts(family="cluster")))
    assert "cluster_stars" in cl and "deconvolution" not in cl


def test_rejection_algorithm_follows_sub_count():
    def rejection(kept):
        step = next(s for s in advise(base_facts(kept=kept)).steps if s.id == "integrate")
        return step.params["rejection"]
    assert rejection(5) == "percentile clipping"
    assert rejection(12) == "Winsorized sigma clipping"
    assert rejection(25) == "linear fit clipping"
    assert rejection(60) == "generalized ESD"


def test_paid_tools_switch_variants():
    plain = next(s for s in advise(base_facts()).steps if s.id == "deconvolution")
    bxt = next(s for s in advise(base_facts(bxt=True)).steps if s.id == "deconvolution")
    assert plain.tools["pixinsight"].process == "Deconvolution"
    assert bxt.tools["pixinsight"].process == "BlurXTerminator"
    assert "Deconvolution" in bxt.tools["siril"].process  # Siril has no BXT


def test_unsolved_session_is_told_how_to_improve():
    a = advise(base_facts(family="unknown", solved=False, located=False))
    assert "identify_target" in ids(a)
    assert a.level == "none"
    color = next(s for s in a.steps if s.id == "color_calibration")
    assert color.confidence == "medium"


def test_markdown_export_has_every_step():
    a = advise(base_facts(dual_band=True))
    md = to_markdown(a, "siril")
    assert "extract_HaOIII" in md and md.count("**") >= 2 * len(a.steps)


def test_calibration_issues_become_an_insight():
    a = advise(base_facts(cal_issue_count=1, cal_issues="Darks do not match the lights."))
    issue = next(r for r in a.insights if r.id == "calibration_issues")
    assert "do not match" in issue.why
    step = next(s for s in a.steps if s.id == "calibrate")
    assert any("flat darks" in s for s in step.tools["pixinsight"].settings)
