"""Turn measurements, context and preferences into the facts that rules use."""

from __future__ import annotations

import math
import re

from advastro.engine.session import SessionSummary
from advastro.frame import FrameMeta
from advastro.naming import short_names
from advastro.session_context import SessionContext
from advastro.sky.identify import TargetReport

DUAL_BAND = re.compile(r"dual|duo|tri.?band|quad|l[- ]?(extreme|enhance|ultimate|ultra|pro)|"
                       r"alp[- ]?t|nbz|antlia.*alp|optolong.*l|hoo|ha.?oiii", re.I)


def _hms(deg: float) -> str:
    h = deg / 15
    return f"{int(h):02d}h {int(h * 60 % 60):02d}m {h * 3600 % 60:04.1f}s"


def _dms(deg: float) -> str:
    sign = "−" if deg < 0 else "+"
    d = abs(deg)
    return f"{sign}{int(d):02d}° {int(d * 60 % 60):02d}′ {d * 3600 % 60:02.0f}″"


def build_facts(summary: SessionSummary, keep: dict[str, bool], meta: FrameMeta | None,
                context: SessionContext | None, target: TargetReport | None,
                profile: dict, scale: float | None, calibration=None) -> dict:
    subs = summary.subs
    kept_subs = [s for s in subs if keep.get(s.file, True)]
    m = summary.medians
    f: dict = {}

    # --- session and measurements
    f["total"] = len(subs)
    f["kept"] = len(kept_subs)
    f["rejected"] = len(subs) - len(kept_subs)
    exposure = meta.exposure_s if meta else None
    f["exposure_s"] = exposure
    f["integration_h"] = (sum(s.exposure_s or exposure or 0 for s in kept_subs) / 3600) or None
    f["fwhm_px"] = m.get("fwhm_px")
    f["fwhm_arcsec"] = m.get("fwhm_arcsec")
    f["ecc"] = m.get("eccentricity")
    f["stars"] = m.get("star_count")
    f["snr"] = m.get("snr_estimate")
    f["gradient_pct"] = m.get("gradient_pct")
    grads = [s.gradient_pct for s in subs if s.gradient_pct is not None]
    f["gradient_spread"] = (max(grads) - min(grads)) if len(grads) > 1 else None
    f["sampling"] = summary.sampling
    f["scale"] = scale
    f["dithered"] = summary.dithered
    f["dither_px"] = summary.dither_px
    f["drift_px"] = summary.drift_px
    best = min((s for s in kept_subs if s.fwhm_px), key=lambda s: s.fwhm_px, default=None)
    f["best_sub"] = best.file if best else None
    f["best_sub_short"] = short_names([s.file for s in subs]).get(best.file) if best else None
    f["best_fwhm"] = best.fwhm_px if best else None

    # --- camera and filters
    f["is_osc"] = bool(meta and meta.bayer_pattern)
    f["bayer"] = meta.bayer_pattern if meta else None
    filter_name = (meta.filter_name if meta else None) or ""
    mk = context.mksession if context else None
    mk_filters = mk.gear.filters if mk else {}
    f["filter"] = filter_name or None
    f["dual_band"] = bool(DUAL_BAND.search(filter_name)) or bool(mk_filters.get("dual"))
    f["is_color"] = f["is_osc"]  # mono RGB sets: multi-filter sessions come in a later phase
    f["temp_text"] = (f"{meta.temperature_c:.0f} °C" if meta and meta.temperature_c is not None
                      else "the same sensor temperature")
    f["bortle"] = mk.bortle if mk else None
    f["bortle_text"] = f", Bortle {f['bortle']} sky" if f["bortle"] else ""

    # --- calibration
    cal = context.calibration if context else None
    for kind in ("darks", "flats", "bias", "darkflats"):
        f[f"has_{kind}"] = bool(cal and cal.has(kind))
    names = {"darks": "darks", "flats": "flats", "bias": "bias", "darkflats": "flat darks"}
    found = [names[k] for k in names if f[f"has_{k}"]]
    f["cal_list"] = " and ".join([", ".join(found[:-1]), found[-1]] if len(found) > 1
                                 else found) if found else None
    details = []
    if cal:
        for k in names:
            if cal.counts.get(k):
                details.append(f"{cal.counts[k]} {names[k]}")
            elif k in cal.masters:
                details.append(f"a master {names[k].rstrip('s')}")
    f["cal_found"] = ", ".join(details) or None
    # Measured calibration frames (when analyzed) are the better source.
    if calibration is not None:
        for kind in ("darks", "flats", "bias", "darkflats"):
            if calibration.count(kind):
                f[f"has_{kind}"] = True
        issues = [n.text for n in calibration.notes if n.level in ("bad", "warn")]
        f["cal_issue_count"] = len(issues)
        f["cal_issues"] = " ".join(issues)
        darks = calibration.group("darks")
        noise = darks.medians.get("noise_adu") if darks else None
        glow = darks.medians.get("glow_adu") if darks else None
        f["dark_glow"] = bool(noise and glow and glow > 3 * noise)
        f["darks_match"] = any(n.kind == "darks" and n.level == "good" and "match" in n.text
                               for n in calibration.notes)
    else:
        f["cal_issue_count"], f["cal_issues"] = 0, ""
        f["dark_glow"], f["darks_match"] = False, False
    f["flat_cal"] = ("the flat darks" if f["has_darkflats"] else
                     "the bias frames" if f["has_bias"] else "nothing (none found)")
    f["dark_optimize"] = ("off (the darks match the lights)" if f["darks_match"] else
                          "off (amp glow)" if f["dark_glow"] else "on")
    f["cosmetic_extra"] = (" Without darks, a slightly lower hot-pixel threshold catches more."
                           if not f["has_darks"] else "")

    # --- target and sky
    t = target
    f["solved"] = bool(t and t.confidence == "solved")
    f["located"] = bool(t and t.sky is not None)
    f["family"] = t.family if t else "unknown"
    f["target_label"] = (t.target.label if t and t.target else "the target")
    f["target_id"] = t.target.id if t and t.target else None
    f["target_mag"] = t.target.magnitude if t and t.target else None
    f["framing"] = t.framing if t else None
    f["coverage"] = t.coverage if t else None
    f["coverage_pct"] = (t.coverage * 100) if t and t.coverage else None
    f["milky_way"] = bool(t and t.milky_way)
    f["abs_b"] = abs(t.galactic_latitude) if t and t.galactic_latitude is not None else None
    sky = t.sky if t else None
    f["fov_w"] = sky.width_deg * 60 if sky else None
    f["fov_h"] = sky.height_deg * 60 if sky else None
    obj = t.target if t else None
    mag = obj.magnitude if obj else None
    # A bright, concentrated core: bright galaxies (M31, M81, M104...) and cluster-lit
    # nebulae such as M42. Large diffuse nebulae (NGC 7000) are bright overall but have none.
    f["bright_core"] = bool(obj and mag is not None and (
        (obj.family == "galaxy" and mag < 8.5)
        or (obj.type == "Cl+N" and mag <= 5.0)
        or (obj.family == "planetary" and mag < 9.0)))

    # --- software
    software = {s.lower() for s in profile.get("software", [])}
    addons = {s.lower() for s in profile.get("paid_addons", [])}
    f["has_pixinsight"] = "pixinsight" in software
    f["has_siril"] = "siril" in software
    f["graxpert"] = "graxpert" in software
    f["starnet"] = "starnet" in software
    f["bxt"] = "blurxterminator" in addons
    f["nxt"] = "noisexterminator" in addons
    f["sxt"] = "starxterminator" in addons
    f["aesthetic"] = profile.get("aesthetic", "natural")
    f["skill"] = profile.get("skill", "intermediate")

    _derived(f, sky)
    return f


def _derived(f: dict, sky) -> None:
    """Pre-written reasons and choices that depend on several facts."""
    family = f["family"]

    # Drizzle
    kept = f["kept"]
    undersampled = f["sampling"] == "undersampled"
    if f["dithered"] and undersampled and kept >= 15:
        f["drizzle_recommended"], f["drizzle_scale"] = True, 2
        f["drizzle_reason"] = (f"Stars are only {f['fwhm_px']:.1f} px wide (undersampled) and "
                               f"the subs are dithered ({f['dither_px']:.0f} px between subs), so "
                               f"2x drizzle with {kept} subs recovers real resolution.")
    elif f["dithered"] and f["is_osc"] and kept >= 20:
        f["drizzle_recommended"], f["drizzle_scale"] = True, 1
        f["drizzle_reason"] = ("Dithered colour data can be stacked with Bayer drizzle at 1x: "
                               "each colour comes from real pixels instead of interpolation, "
                               "which gives cleaner colour and finer stars.")
    else:
        f["drizzle_recommended"], f["drizzle_scale"], f["drizzle_reason"] = False, None, None
    f["bayer_drizzle"] = bool(f["drizzle_recommended"] and f["is_osc"])

    f["drift_note"] = (f" The field drifted {f['drift_px']:.0f} px over the session; "
                       "registration handles that, but check polar alignment."
                       if f["drift_px"] and f["drift_px"] > 50 and not f["dithered"] else "")

    # Gradient removal
    grad = f["gradient_pct"]
    strong = (grad is not None and grad > 8) or (f["bortle"] or 0) >= 6
    f["gradient_strength"] = " (strong)" if strong else ""
    if f["framing"] in ("fills_field", "larger_than_field"):
        how = (f"{f['target_label']} fills the frame, so there is little empty sky: place "
               "background samples only on truly dark patches, or use an AI model such as "
               "GraXpert, and avoid automatic polynomial fits that can remove faint nebulosity.")
    elif family == "galaxy":
        how = ("There is plenty of empty sky around the galaxy, so an automatic fit "
               "(low degree) or a few manual samples away from the galaxy's faint halo works well.")
    else:
        how = "Place samples on empty sky across the frame, avoiding stars and nebulosity."
    level = (f"The background varies by about {grad:.0f} % across the frame"
             if grad is not None else "Every sky has some gradient")
    f["gradient_reason"] = f"{level}{f['bortle_text']}. {how}"

    # Plate solving and colour calibration
    if sky is not None and f["solved"]:
        f["solve_reason"] = (f"Colour calibration needs it. Your session is already solved: "
                             f"centre RA {_hms(sky.ra)}, Dec {_dms(sky.dec)}, "
                             f"{sky.scale_arcsec:.2f}″/px. Enter these to solve in seconds.")
    elif sky is not None:
        f["solve_reason"] = (f"Colour calibration needs it. Start from the telescope pointing: "
                             f"RA {_hms(sky.ra)}, Dec {_dms(sky.dec)}, about "
                             f"{sky.scale_arcsec:.2f}″/px.")
    else:
        f["solve_reason"] = ("Colour calibration needs an astrometric solution. Enter the image "
                             "scale and the target name or coordinates to help the solver.")
    if f["dual_band"]:
        f["color_reason"] = ("Use narrowband mode with your filter's Hα (656 nm) and OIII "
                             "(500 nm) passbands, so the colours match what the filter "
                             "really transmits.")
    elif family == "galaxy":
        f["color_reason"] = ("Measures star colours against a photometric catalog. Use an "
                             "average spiral galaxy as white reference for natural galaxy colour.")
    else:
        f["color_reason"] = ("Measures the colours of stars in the field against a photometric "
                             "catalog and corrects your camera's colour response.")

    # Deconvolution target
    f["deconv_target"] = {
        "galaxy": ": spiral arms and dust lanes benefit the most",
        "planetary": ": the small shell structure benefits the most",
        "emission": " in filaments and dark lanes; keep nebula sharpening moderate",
    }.get(family, "")

    # Narrowband palette
    aesthetic = (f["aesthetic"] or "natural").upper()
    f["palette_text"] = "HOO" if aesthetic in ("HOO", "NATURAL") else aesthetic
    f["sho_note"] = (" A true SHO palette needs SII data; an SHO look from Hα/OIII alone is an "
                     "approximation." if aesthetic == "SHO" else "")

    # Stretch
    f["stretch_reason"] = {
        "galaxy": ("Use a generalized hyperbolic stretch with highlight protection so the core "
                   "does not burn out while the faint outer arms come up."),
        "cluster": "Use a gentle arcsinh stretch: it brightens faint stars without bleaching "
                   "star colour.",
        "globular": "Use a gentle arcsinh stretch and protect the dense core from saturating.",
    }.get(family, ("Use a generalized hyperbolic stretch with the symmetry point at the "
                   "background peak: faint nebulosity comes up without bloating the sky."))

    f["contrast_reason"] = {
        "galaxy": "Medium-scale contrast on the spiral arms brings out dust lanes and HII "
                  "regions; keep it subtle so the halo stays smooth.",
        "planetary": "Small-scale contrast brings out shell structure; protect the background.",
    }.get(family, "Local histogram equalization at large scale brings out filaments and depth "
                  "in the nebula; apply it to the starless image.")

    f["saturation_reason"] = ("Raise saturation on the nebula through a mask, keeping the "
                              "background neutral." if family != "galaxy" else
                              "Raise saturation gently on the galaxy (blue arms, pink HII "
                              "regions), keeping the background neutral.")
    f["milky_way_note"] = (" — in this Milky Way field, reducing star strength by 20–40 % "
                           "keeps the nebula in front" if f["milky_way"] else "")
    f["abs_b"] = f["abs_b"] if f["abs_b"] is not None else None
    f["panels"] = max(2, math.ceil(f["coverage"])) if f["coverage"] else None
