<!-- id: settings -->
# Settings

Open with **Settings** in the toolbar (Ctrl+,). Changes are saved in your settings file when
you click *Save* and apply at once; the subs are not measured again. The settings file is:

- Windows: `%APPDATA%\AdvAstro\config.toml`
- macOS: `~/Library/Application Support/AdvAstro/config.toml`
- Linux: `~/.config/advastro/config.toml`

<!-- id: settings.general -->
## General

- **Language**: English or Svenska. Takes effect when you restart the app.
- **Parallel workers**: how many subs are measured at the same time. Pick from the list:
  *Automatic* uses every processor core (the number is shown); a lower number keeps the
  computer responsive during long analyses.

<!-- id: settings.equipment -->
## Equipment

**Focal length** and **pixel size** are used only when the file headers do not say. Most
capture programs (NINA, ASIAIR, SharpCap) write both. With them, AdvAstro shows star sizes
in arcseconds and can judge sampling and plate solve faster.

<!-- id: settings.selection -->
## Sub selection

How far a sub may stand out from the rest of the session before it is suggested for
rejection.

| Strictness | Star size | Max elongation | Min stars | Sky brightness |
| --- | --- | --- | --- | --- |
| Lenient | 4 σ | 0.7 | 45 % | 5 σ |
| Normal | 3 σ | 0.6 | 60 % | 4 σ |
| Strict | 2 σ | 0.5 | 75 % | 3 σ |

σ is the robust spread of the session; star count is a share of the session median. Set the
values yourself for *Custom*. **Also check bias, darks, flats and flat darks** turns the
[calibration checks](help:calibration) on or off.

The *?* next to each value opens its explanation below.

<!-- id: settings.selection.fwhm -->
### Star size limit (σ above median)

Rejects subs whose stars are much larger than the session's typical size. Large stars mean
a blurred sub: focus drift as the temperature falls, poor seeing, wind or a guiding hiccup.
The limit is in σ, the session's own spread: with 3 σ, a sub is flagged when its star size
is three spreads above the median, so a steady session and a variable one are both judged
fairly. Lower is stricter.

<!-- id: settings.selection.ecc -->
### Maximum star elongation

Rejects subs whose stars are stretched. The value is the eccentricity: 0 is perfectly round,
0.5 is about 15 % longer than wide (just visible), 0.6 about 25 % longer (clearly oval) and
0.8 about 70 % longer. Causes: wind, guiding
errors, balance, periodic error, or a cable dragging. Unlike the other limits, this one is
absolute, not relative to the session: a session where every sub is trailed is still
flagged. Lower is stricter.

<!-- id: settings.selection.stars -->
### Minimum stars (share of median)

Rejects subs with too few stars compared with the session's typical count. Stars disappear
behind clouds, haze, dew on the optics, or when the sub is badly out of focus. With 0.6, a
sub with fewer than 60 % of the usual number of stars is flagged. Higher is stricter.

<!-- id: settings.selection.sky -->
### Sky brightness limit (σ above median)

Rejects subs with a much brighter sky than the rest: the Moon rising, clouds lit by town
light, dawn, or a car's headlights. A brighter sky adds noise and gradients that the other
subs do not have. The limit is in σ of the session's sky levels. Lower is stricter.

<!-- id: settings.solver -->
## Plate solving

- **Solve automatically** after the analysis when the files carry no solution.
- **ASTAP program** and **Star database folder**: leave empty to detect automatically, or
  browse to them. Pointing at the ASTAP folder is enough.
- **Search radius**: how far from the header position ASTAP searches (degrees).
- **Time limit**: how long ASTAP may take.
- The box below shows what was found; *Check again* repeats the search, *Get ASTAP* opens
  its website.

<!-- id: settings.software -->
## Your software

Tick the **programs you use** (PixInsight, Siril, GraXpert, StarNet) and the **paid add-ons
you own** (BlurXTerminator, NoiseXTerminator, StarXTerminator). The workflow and Rate my pic's
improvement plan are written for them.

<!-- id: settings.style -->
## Style

- **Colour style**: natural colour, HOO (Hα red, OIII teal) or SHO (Hubble palette).
- **Detail level**: *Beginner* and *Intermediate* show menu paths and reasons for every step;
  *Advanced* shows a compact list. It also sets how strict
  [Rate my pic's verdict](help:rate.verdict) is.

<!-- id: settings.compare -->
## Compare

Settings for Rate my pic's checks against the sky and comparisons with other photographers.

- **Run sky checks automatically** after rating: plate solving, Gaia depth and colour.
- **Compare with a sky survey image** (DSS2, Pan-STARRS).
- **AstroBin API key** and **secret**: optional. With them, the most liked AstroBin images of
  the object appear inside AdvAstro. Request a free key with the link on the page. The key is
  stored in your settings file.
- **Without an AstroBin key, open search pages in the browser**. With no key and this
  option off, no comparison is made.

<!-- id: settings.files -->
## Settings files for advanced use

Settings are plain TOML text files, applied in layers (last wins):

1. built-in defaults,
2. your settings file (above),
3. `advastro.toml` in the session folder (settings for one session),
4. files given with `--config` on the command line,
5. `--set section.key=value` on the command line.

Unknown keys or wrong value types produce a warning naming the file, and are ignored.
`advastro config` shows the merged settings and where each value came from.
