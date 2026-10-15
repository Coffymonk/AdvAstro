# Credits and acknowledgements

Advanced Astrophoto Analyzer stands on the work of many people and organisations. This file
lists everything the application is built with, the data and services it uses, and the
programs it gives advice for. The same list is in the app under **Help › Credits and
licences**.

Copyright © 2026 Miklosoft. Released under the GNU General Public License v3.0.
See [LICENSE](https://github.com/Coffymonk/AdvAstro/blob/main/LICENSE) in the AdvAstro repository on GitHub.

## Software libraries

These are bundled with the desktop app and the command-line tool. Their licence texts are
copied into the `licenses` folder of every build.

| Library | Used for | Licence |
| --- | --- | --- |
| [Qt](https://www.qt.io) and [Qt for Python (PySide6)](https://www.qt.io/qt-for-python), The Qt Company | The desktop interface, PDF reports | LGPL-3.0 |
| [NumPy](https://numpy.org) | Numerical arrays | BSD-3-Clause |
| [SciPy](https://scipy.org) | Filtering, fitting, statistics | BSD-3-Clause |
| [Astropy](https://www.astropy.org), The Astropy Collaboration | FITS files, coordinates, WCS | BSD-3-Clause |
| [PyERFA](https://github.com/liberfa/pyerfa) and ERFA | Astronomical calculations (via Astropy) | BSD-3-Clause |
| [photutils](https://photutils.readthedocs.io), Astropy project | Star detection and measurement | BSD-3-Clause |
| [Pillow](https://python-pillow.org) | JPEG, PNG and WebP pictures | MIT-CMU |
| [tifffile](https://github.com/cgohlke/tifffile) and [imagecodecs](https://github.com/cgohlke/imagecodecs), Christoph Gohlke | TIFF pictures and their compression | BSD-3-Clause (imagecodecs bundles codec libraries under their own permissive licences, included in its licence files) |
| [python-lz4](https://github.com/python-lz4/python-lz4) | LZ4-compressed XISF files | BSD-3-Clause |
| [python-zstandard](https://github.com/indygreg/python-zstandard) | Zstandard-compressed XISF files | BSD-3-Clause |
| [PyYAML](https://pyyaml.org), [packaging](https://github.com/pypa/packaging) | Used by Astropy | MIT; Apache-2.0 or BSD-2-Clause |

**About Qt (LGPL-3.0).** Qt is used as a library under the GNU Lesser General Public License
version 3. The app is distributed as a folder in which the Qt libraries are separate files,
so you can replace them with your own build of Qt. The LGPL text is in the `licenses` folder;
Qt's source code is available from <https://www.qt.io/download-open-source>.

Build tools (not distributed): [PyInstaller](https://pyinstaller.org) (GPL-2.0-or-later with
the bootloader exception, which allows bundling applications under any licence),
[pytest](https://pytest.org) and [Ruff](https://docs.astral.sh/ruff/).

## Data

- **Deep-sky catalogue**: [OpenNGC](https://github.com/mattiaverga/OpenNGC) by Mattia Verga,
  licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). AdvAstro
  ships a reduced copy (`src/advastro/data/openngc.csv`) under the same licence; the changes
  are described in [`src/advastro/data/OPENNGC.md`](src/advastro/data/OPENNGC.md).

## Online services (used by Rate my pic's sky checks)

These are used only when you run sky checks or comparisons, and only over the internet.

- **Gaia.** This work has made use of data from the European Space Agency (ESA) mission
  *Gaia* (<https://www.cosmos.esa.int/gaia>), processed by the *Gaia* Data Processing and
  Analysis Consortium (DPAC, <https://www.cosmos.esa.int/web/gaia/dpac/consortium>). Funding
  for the DPAC has been provided by national institutions, in particular the institutions
  participating in the *Gaia* Multilateral Agreement. AdvAstro uses Gaia Data Release 3.
- **VizieR.** This research has made use of the VizieR catalogue access tool, CDS,
  Strasbourg, France (DOI: [10.26093/cds/vizier](https://doi.org/10.26093/cds/vizier)).
- **hips2fits and HiPS.** This research has made use of hips2fits, a service provided by
  CDS, Strasbourg, France, and of the HiPS surveys it serves.
- **Digitized Sky Survey (DSS2).** The Digitized Sky Surveys were produced at the Space
  Telescope Science Institute under U.S. Government grant NAG W-2166. The images of these
  surveys are based on photographic data obtained using the Oschin Schmidt Telescope on
  Palomar Mountain and the UK Schmidt Telescope.
- **Pan-STARRS.** The Pan-STARRS1 Surveys (PS1) and the PS1 public science archive were made
  possible by the Institute for Astronomy, University of Hawaii, the Pan-STARRS Project
  Office and their partner institutions; see the
  [full acknowledgement](https://panstarrs.stsci.edu/).
- **Mellinger all-sky panorama**, © Axel Mellinger (Mellinger, A. 2009, PASP 121, 1180),
  used for very wide fields.
- **AstroBin** (<https://www.astrobin.com>), through its public API with the user's own key.
  The images shown belong to their photographers and are only linked, never stored.

## Programs AdvAstro works with

- **ASTAP** by Han Kleijn (<https://www.hnsky.org/astap.htm>) does the plate solving. It is
  a separate program that you install yourself; AdvAstro runs it and reads its result.
- The automatic display stretch follows the method of PixInsight's ScreenTransferFunction
  (Pleiades Astrophoto).
- The workflow advice refers to **PixInsight** (Pleiades Astrophoto), **Siril**
  (Free-Astro team), **GraXpert**, **StarNet** and the RC Astro tools **BlurXTerminator**,
  **NoiseXTerminator** and **StarXTerminator**. Capture programs whose files AdvAstro reads
  include NINA, ASIAIR (ZWO), SharpCap, KStars/Ekos, Sequence Generator Pro and APT.

All product names and trademarks belong to their owners. AdvAstro is an independent project
and is not affiliated with, or endorsed by, any of them.

## Development

Written by Miklosoft, with the help of Claude, an AI assistant made by
[Anthropic](https://www.anthropic.com). The application icon is an original design made for
this project.
