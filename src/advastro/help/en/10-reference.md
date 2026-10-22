<!-- id: reference -->
# Reference

<!-- id: reference.shortcuts -->
## Keyboard shortcuts

| Keys | Action |
| --- | --- |
| Ctrl+O | Open a session folder (main window) or a picture (Rate my pic) |
| F5 | Analyze again |
| Esc | Stop a running analysis |
| Space / K / R | Toggle / keep / reject the selected subs |
| Ctrl+1 / Ctrl+2 / Ctrl+3 | Session / Calibration / Rate my pic |
| Ctrl+R | Rate my pic |
| Ctrl+, | Settings |
| Ctrl+N | Night mode |
| F1 | Help for what you are looking at |
| Mouse wheel, drag, double-click | Zoom, pan, fit / 100 % in the preview |
| Double-click a calibration frame | Its full analysis, with the hot-pixel map |

<!-- id: reference.glossary -->
## Glossary

**ADU**: the camera's raw pixel value. **Sub**: a single exposure (light frame).
**FWHM**: star diameter at half its peak brightness. **Eccentricity / elongation**: 0 is a
round star; higher is more stretched. **σ (sigma)**: a measure of spread; AdvAstro uses a
robust version that ignores outliers. **Linear / stretched**: data straight from stacking is
linear and looks almost black; stretching brightens the faint parts. **Plate solving**:
finding exactly where in the sky an image points by matching its stars against a catalogue.
**Limiting magnitude**: the faintest star brightness an image shows (larger numbers are
fainter). **Dithering**: moving the telescope a few pixels between subs. **Drizzle**: a
stacking method that recovers resolution from undersampled, dithered data. **Gradient**:
uneven background brightness from light pollution, moonlight or imperfect flats.
**Mottle**: blotchy background noise. **SCNR**: removes a colour cast, usually green.
**OSC**: one-shot colour camera. **Hα, OIII**: emission lines of hydrogen (red) and oxygen
(teal) used by narrowband and dual-band filters.

<!-- id: reference.faq -->
## Troubleshooting and questions

**AdvAstro does not find ASTAP.** Open *Settings › Plate solving* and point at the ASTAP
program or its folder. Check that a star database (D05, D20, D50, …) is installed.

**Plate solving fails.** Check focal length and pixel size, install a database that suits
your field (D50 for most setups), raise the search radius or time limit. For Rate my pic,
type the object's name in the Object field.

**Sky checks or comparisons say they cannot connect.** They need the internet (Gaia and
survey images come from the CDS in Strasbourg; AstroBin from astrobin.com). Check the
connection or a firewall. Everything else works offline.

**AstroBin returns nothing.** Check the key and secret in *Settings › Compare*, and try the
object's catalogue name (for example *NGC 7000* rather than a nickname).

**Many good subs are flagged.** Choose *Lenient* in *Settings › Sub selection*. Remember that
flags compare subs within the session: in a very even session, small differences stand out.

**Star sizes are shown only in pixels.** AdvAstro needs focal length and pixel size, from the
headers, *Settings › Equipment*, or a `.mksession` file.

**Windows or macOS refuses to start the app.** The packages are not code-signed yet; see
[Installing](help:start.install).

**Does AdvAstro change my files?** No. It only reads them. Plate solving uses a temporary
copy, and reports are saved only where you choose.

**Where are my settings?** See [Settings](help:settings).

**How do I report a problem or suggest something?** Through the GitHub page or
<https://miklosoft.se/main>. Include the version (Help › About) and, if you can, the JSON
report.
