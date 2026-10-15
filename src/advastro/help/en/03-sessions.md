<!-- id: session -->
# Analyzing a session

<!-- id: session.window -->
## The main window

- **Toolbar**: *Open*, *Analyze* (again), *Stop*, *Solve*, *Suggested*, *Export*, and on the
  right *Rate my pic*, *Settings*, *Night* and *Help*.
- **Frame tabs** above the table: *Lights* and, when found, *Darks*, *Flats*, *Flat darks*
  and *Bias*, each with a count and a warning sign when something is flagged.
- **Table**: one row per file. Click a row to preview it.
- **Filter** buttons above the table: *All*, *Flagged*, *Rejected*.
- **Preview**: the selected file with an automatic stretch. Mouse wheel zooms, drag pans,
  double-click switches between fit and 100 %.
- **Tabs** under the preview: *Session*, *Target* and *Workflow*.
- **Status bar**: progress and short messages.

<!-- id: session.columns -->
## What the columns mean

| Column | Meaning | Tells you about |
| --- | --- | --- |
| Keep | Check box: keep the sub for stacking | Your selection |
| ⚠ | The sub stands out; hover for the reason | Problems |
| File | File name (the common part of all names is shortened) | |
| FWHM px | Star size at half brightness, in pixels | Seeing, focus |
| FWHM ″ | The same in arcseconds (needs the image scale) | Seeing, focus |
| Ecc. | Star elongation (eccentricity): 0 is round | Tracking, guiding, wind |
| Stars | Number of stars detected | Clouds, haze, dew |
| Background | Sky brightness in ADU | Moon, dawn, light pollution |
| Noise | Background noise in ADU | Sky brightness, gain |
| SNR | Median star peak divided by noise | Overall quality |

Hover a column title for a short explanation.

<!-- id: session.flags -->
## How subs are judged

Subs are compared with the **rest of the same session**, not with fixed numbers, so the
judgement adapts to your equipment and sky. A sub is flagged when:

- its **stars are larger** than the session median by more than *3 σ* (robust spread), which
  points to seeing, focus drift or wind;
- its **stars are elongated**: eccentricity above *0.6*, which points to tracking, guiding
  or wind;
- it has **far fewer stars**: under *60 %* of the session median, which points to clouds,
  haze or dew;
- its **sky is brighter** than the median by more than *4 σ*, which points to the Moon,
  dawn, a light source or clouds lit from below.

The numbers in italics are the *Normal* strictness; change them in
[Settings › Sub selection](help:settings.selection). Flagged subs are unticked in the suggested
selection. Hover the warning sign for the exact values.

<!-- id: session.keep -->
## Keeping and rejecting subs

- Click a check box to keep or reject one sub.
- Select several rows and press **Space** (toggle), **K** (keep) or **R** (reject), or
  right-click for a menu.
- **Suggested** in the toolbar resets everything to AdvAstro's suggestion.
- Your choices update the Session statistics and the workflow immediately.

<!-- id: session.summary -->
## The Session tab

Shows the session at a glance: subs kept, median FWHM, eccentricity, star count, noise and
**sampling**:

- **Undersampled** (stars under 2 px): stars are blocky; drizzle helps.
- **Well sampled** (2–5 px): ideal.
- **Oversampled** (over 5 px): binning or a reducer gives the same detail with less noise.

Below that, **Needs attention** lists every flagged sub with the reason (click one to select
it in the table) and any file that could not be read. When you are on a calibration tab, the
Session tab shows the [calibration checks](help:calibration) instead.

<!-- id: session.dither -->
## Dithering and drift

AdvAstro measures how the stars move between subs. Random jumps of a few pixels mean you
**dithered**, which is good: hot pixels and walking noise are rejected during stacking.
A slow, steady creep in one direction means **drift** (polar alignment or no guiding). The
workflow uses this: drizzle is only recommended for dithered data, and undithered sessions
get a "Dither next time" step.

<!-- id: session.export -->
## Exporting

The **Export** menu saves, for the frame type you are looking at:

- **Rejected files list** or **Kept files list**: one full path per line; load it into
  PixInsight, Siril or a script.
- **Report as CSV** for a spreadsheet, or **JSON** for other programs.
- **Workflow as Markdown**: the Workflow tab as text.

<!-- id: session.night -->
## Night mode

**Night** (Ctrl+N) turns the whole window red, including the preview, so your eyes stay
dark-adapted at the telescope.
