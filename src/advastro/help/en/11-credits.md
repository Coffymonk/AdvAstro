<!-- id: credits -->
# Credits and licences

Copyright © 2026 Miklosoft. Released under the GNU General Public License v3.0.
See [LICENSE](https://github.com/Coffymonk/AdvAstro/blob/main/LICENSE) in the AdvAstro repository on GitHub.

It stands on the work of many people and organisations; thank you all.
The licence texts of everything bundled are in the `licenses` folder next to the program.

<!-- id: credits.libraries -->
## Software libraries

| Library | Used for | Licence |
| --- | --- | --- |
| Qt and Qt for Python (PySide6), The Qt Company | The interface, PDF reports | LGPL-3.0 |
| NumPy | Numerical arrays | BSD-3-Clause |
| SciPy | Filtering, fitting, statistics | BSD-3-Clause |
| Astropy, The Astropy Collaboration | FITS files, coordinates, WCS | BSD-3-Clause |
| PyERFA and ERFA | Astronomical calculations | BSD-3-Clause |
| photutils | Star detection and measurement | BSD-3-Clause |
| Pillow | JPEG, PNG and WebP pictures | MIT-CMU |
| tifffile and imagecodecs, Christoph Gohlke | TIFF pictures and compression | BSD-3-Clause |
| python-lz4, python-zstandard | Compressed XISF files | BSD-3-Clause |
| PyYAML, packaging | Used by Astropy | MIT; Apache-2.0 or BSD-2-Clause |

Qt is used under the GNU Lesser General Public License 3.0. Its libraries are separate files in
the program folder, so they can be replaced; Qt's source code is available from
<https://www.qt.io/download-open-source>. The app is packaged with PyInstaller.

<!-- id: credits.data -->
## Data

**Deep-sky catalogue**: OpenNGC by Mattia Verga (<https://github.com/mattiaverga/OpenNGC>),
licensed under CC BY-SA 4.0. AdvAstro ships a reduced copy under the same licence.

<!-- id: credits.services -->
## Online services

Used only by Rate my pic's sky checks and comparisons.

- **Gaia**: this work has made use of data from the European Space Agency (ESA) mission Gaia
  (<https://www.cosmos.esa.int/gaia>), processed by the Gaia Data Processing and Analysis
  Consortium (DPAC). Funding for the DPAC has been provided by national institutions, in
  particular the institutions participating in the Gaia Multilateral Agreement.
- **VizieR**: the VizieR catalogue access tool, CDS, Strasbourg, France
  (DOI 10.26093/cds/vizier).
- **hips2fits and HiPS**: a service provided by CDS, Strasbourg, France.
- **Digitized Sky Survey (DSS2)**: produced at the Space Telescope Science Institute under
  U.S. Government grant NAG W-2166, based on photographic data from the Oschin Schmidt
  Telescope on Palomar Mountain and the UK Schmidt Telescope.
- **Pan-STARRS1 Surveys (PS1)**: Institute for Astronomy, University of Hawaii, the
  Pan-STARRS Project Office and partner institutions.
- **Mellinger all-sky panorama**: © Axel Mellinger (PASP 121, 1180, 2009).
- **AstroBin**: through its public API with your own key. Images belong to their
  photographers and are only linked, never stored.

<!-- id: credits.programs -->
## Programs AdvAstro works with

- **ASTAP** by Han Kleijn (<https://www.hnsky.org/astap.htm>) does the plate solving. It is a
  separate program you install yourself.
- The automatic display stretch follows the method of PixInsight's ScreenTransferFunction.
- The advice refers to PixInsight (Pleiades Astrophoto), Siril (Free-Astro team), GraXpert,
  StarNet and RC Astro's BlurXTerminator, NoiseXTerminator and StarXTerminator. AdvAstro reads
  files from NINA, ASIAIR, SharpCap, KStars/Ekos, Sequence Generator Pro, APT and others.

All product names and trademarks belong to their owners. AdvAstro is an independent project
and is not affiliated with, or endorsed by, any of them.

<!-- id: credits.development -->
## Development

Written by Miklosoft, with the help of Claude, an AI assistant made by Anthropic. The
application icon is an original design made for this project.
