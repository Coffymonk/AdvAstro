# Advanced Astrophoto Analyzer

**Know what your data is worth, and what to do with it.**

*Short version (for a product card or a link preview):*
Advanced Astrophoto Analyzer is a free analyzer and advisor for deep-sky astrophotography. It measures
every sub, checks your calibration frames, finds out what you imaged, writes a step-by-step
processing workflow for PixInsight or Siril, and rates your finished pictures with a clear
verdict and a plan to make them better. For Windows, macOS and Linux.

---

## What it is

Every astrophotographer knows the questions. Which subs should I throw away? Are my darks
and flats any good? Should I drizzle? Why does my background look blotchy? Is this picture
good enough to post?

AdvAstro answers them with measurements, not guesswork. It reads your files, measures
what matters and explains every finding in plain language with your own numbers, from the
night at the telescope to the finished picture.

It is an **analyzer and advisor**. It never changes your files, and it never stacks or
processes images: PixInsight, Siril and your other tools do that. AdvAstro tells you how.

## Before you stack: analyze the session

- **Every sub measured**: star size (FWHM), roundness, star count, sky brightness, noise,
  signal-to-noise, gradients, dithering and drift.
- **The bad subs found for you**: subs are compared with the rest of the same night, so the
  judgement fits your equipment and sky. Each flag says why: seeing, focus, tracking, clouds,
  the Moon.
- **Calibration frames checked**: light leaks in darks, amp glow, banding, flat brightness,
  vignetting, dust, and whether darks and flats really match your lights.
- **Your target identified** from the plate solution in your files, with the free ASTAP
  solver, from the telescope pointing or from the object name, with a sketch of how it fits
  your field.
- **A processing workflow written for your data**: every step for PixInsight or Siril, with
  concrete settings and the reason for each. A galaxy gets a different workflow from a nebula
  or a star cluster, and the advice changes with your sampling, dithering, filters and the
  tools you own (including BlurXTerminator, NoiseXTerminator, StarXTerminator, GraXpert and
  StarNet).

## After processing: Rate my pic

Drop a finished picture (FITS, XISF, TIFF, PNG or JPEG) and get an honest second opinion:

- **A verdict**: *Excellent*, *Ready to share*, *Good with fixable issues* or *Needs work*, with
  a score and a grade for stars, background, colour, detail, tonality and presentation. How
  strict it is follows your experience level.
- **Every finding shown on the picture**: star shape across the field, gradients, noise,
  colour casts, clipping, rings from over-sharpening, hot pixels, uncropped edges.
- **A tailored improvement plan**: what to fix first, with the exact steps in PixInsight or
  Siril, and what to change at the telescope next time.
- **Checked against the sky**: how deep your image goes, measured against the Gaia star
  catalogue; whether your star colours match their true colours; and the same field from a
  professional sky survey to blink against your picture.
- **Compared with others**: see the most liked AstroBin images of the same object, or open
  searches in your browser.
- **Reports** as PDF, Markdown for forum posts, or JSON.

## Made for real astrophotographers

- **Friendly for beginners, fast for experts**: explanations and menu paths when you want
  them, a compact list when you do not.
- **Night mode** keeps your eyes dark-adapted at the telescope.
- **Command line** for batch work and scripts.
- **Works with your files**: FITS and XISF from NINA, ASIAIR, SharpCap, Ekos, SGP, APT,
  PixInsight and Siril. Camera raw files are on the way.
- **English and Swedish**, with more languages to come.
- **Built-in manual**: press F1 anywhere for help about what you are looking at.

## Free and open source

Advanced Astrophoto Analyzer is free software under the GNU General Public License 3.0. Use it, study
it, change it and share it. The source code is on GitHub.

## System requirements

- Windows 10 or 11, macOS on Apple Silicon, or 64-bit Linux
- Optional: ASTAP (free) for plate solving files that are not already solved
- Optional: an internet connection for the sky checks and comparisons in Rate my pic

## Status

AdvAstro is in active development. Session analysis, calibration checks, target
identification, processing workflows and Rate my pic are working today; camera raw files,
more processing programs and multi-filter sessions are next. Feedback is very welcome.

**Download** · **Source code on GitHub** · **User manual**
