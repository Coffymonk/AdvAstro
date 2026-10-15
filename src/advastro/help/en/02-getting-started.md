<!-- id: start -->
# Getting started

<!-- id: start.install -->
## Installing

Download the package for your system from <https://miklosoft.se/main> or the GitHub
releases page, unpack it and start **Advanced Astrophoto Analyzer**.

The packages are not code-signed yet:

- **Windows**: if SmartScreen warns, click *More info › Run anyway*.
- **macOS**: if macOS refuses to open the app, open *System Settings › Privacy & Security*
  and choose *Open Anyway*.

<!-- id: start.astap -->
## Setting up plate solving (optional)

Many capture programs (ASIAIR, NINA, SharpCap with solving on) already write a plate
solution into each file; AdvAstro uses it directly and needs nothing else.

For other files, install the free **ASTAP** plate solver and one star database:

1. Download ASTAP from <https://www.hnsky.org/astap.htm> and install it.
2. Install a star database: **D50** suits most setups; **D20** or **D05** is enough for
   small sensors and long focal lengths. The Windows installer puts it in a `Database`
   folder inside the ASTAP folder.
3. Open *Settings › Plate solving*. AdvAstro looks in the usual places (on Windows
   `C:\Program Files\astap`) and shows what it found. If it did not find ASTAP, click
   *Browse…* and point at the ASTAP program or just its folder.

AdvAstro solves a temporary copy; it never writes into your images.

<!-- id: start.folders -->
## How to organise a session folder

AdvAstro works best with the folder layout most capture programs create:

```
Session-2026-10-14_NGC7000/
  LIGHT/         your lights (subs)
  DARK/          darks
  FLAT/          flats
  BIAS/          bias frames
  FLAT DARK/     flat darks (also "DARKFLAT", "Dark Flats" ...)
  session.mksession   (optional, from the Miklosoft session logger)
```

- Open the session folder or the `LIGHT` folder; both work.
- Folder names are recognised in English in the usual spellings (singular or plural,
  with or without "frames"). Master files (`masterDark…`, `masterFlat…`) are found in the
  session folder or a `Master` folder.
- You can also open a calibration folder on its own (for example `DARK`) to check just those
  frames.

<!-- id: start.first -->
## Your first analysis

1. Start AdvAstro and drop the session folder on the window, or click *Choose folder…*.
2. Subs appear in the table while they are measured. Each takes a fraction of a second; all
   processor cores are used.
3. When the subs are done, AdvAstro identifies the target, checks the calibration frames and
   writes the workflow.
4. Look at the **Session** tab for anything that needs attention, review the flagged subs
   (hover the warning sign to see why), then export the list of kept or rejected files, or
   follow the **Workflow** tab.

<!-- id: start.files -->
## Supported files

| Use | Formats |
| --- | --- |
| Subs and calibration frames | FITS (`.fits`, `.fit`, `.fts`), XISF (`.xisf`, any compression) |
| Rate my pic | FITS, XISF, TIFF (8, 16 and 32-bit, compressed or not), PNG, JPEG, WebP, BMP |
| Session information | Miklosoft `.mksession` and `.mktargets` files |

Colour (one-shot-colour) subs are measured without debayering, on 2×2 superpixels, so no
interpolation affects the numbers.
