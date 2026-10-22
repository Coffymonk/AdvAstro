<!-- id: intro -->
# Introduction

Advanced Astrophoto Analyzer (AdvAstro for short) is an analyzer and advisor for deep-sky
astrophotography. It looks at your data and tells you, with your own numbers, what is good,
what is not, and what to do about it.

It **never changes your files** and **never stacks or processes images**. Your own software
(PixInsight, Siril and others) does that; AdvAstro tells you how.

<!-- id: intro.what -->
## What it does

1. **Measures every sub** in a session: star size (FWHM), elongation, star count, sky
   brightness, noise, signal-to-noise, gradient, dithering and drift. Subs that stand out
   from the rest of the session are flagged, with the reason, and left out of the suggested
   selection.
2. **Checks your calibration frames**: bias, darks, flats and flat darks, on their own and
   against the lights (light leaks, amp glow, banding, flat brightness, vignetting, dust,
   matching exposure, gain and temperature).
3. **Finds out what you imaged** from the plate solution in your files, from ASTAP, from the
   telescope pointing or from the object name, and shows how the target fits your field.
4. **Recommends a processing workflow** for PixInsight or Siril, step by step, with concrete
   settings and the reason for each step. A galaxy gets a different workflow from a nebula
   or a star cluster.
5. **Rates finished pictures** (*Rate my pic*): a verdict, scores per category, every finding
   shown on the image, a tailored improvement plan, checks against the Gaia star catalogue
   and a sky survey, and comparisons with other photographers' images.

<!-- id: intro.tour -->
## A quick tour

- **Three modes**, as tabs under the toolbar. Each keeps what it has loaded, and the
  toolbar shows that mode's tools:
    - **Session** (Ctrl+1): open a session folder. The table lists every sub. On the right are
      a preview and three tabs: **Session** (summary and anything that needs attention),
      **Target** (what you imaged) and **Workflow** (how to process it).
    - **Calibration** (Ctrl+2): the bias, darks, flats and flat darks found next to the
      lights, with every check. Double-click a frame for its full analysis.
    - **Rate my pic** (Ctrl+3 or Ctrl+R): judge a finished picture, with a plan to improve
      it and a workflow for the object.
- **Settings** (Ctrl+,): your equipment, how strict sub selection is, plate solving, the
  programs you use, your style and comparisons.
- **Help** (F1): this manual. F1 opens the section about what you are looking at.

<!-- id: intro.requirements -->
## Requirements

- Windows 10 or 11, macOS on Apple Silicon, or Linux (64-bit).
- Files: FITS and XISF subs and calibration frames; for Rate my pic also TIFF, PNG, JPEG
  and WebP. Camera raw files (CR2, CR3, NEF, ARW) are planned.
- Optional: [ASTAP](https://www.hnsky.org/astap.htm) (free) for plate solving files that are
  not solved already.
- Optional: an internet connection for the Gaia, sky survey and AstroBin features of
  Rate my pic. Everything else works offline.

<!-- id: intro.licence -->
## Licence and website

Advanced Astrophoto Analyzer is free software under the GNU General Public License version 3 (GPL-3.0):
free to use, study, change and share. Source code and downloads are on GitHub and at
<https://miklosoft.se/main>.
