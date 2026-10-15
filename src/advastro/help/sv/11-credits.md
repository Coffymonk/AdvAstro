<!-- id: credits -->
# Tack och licenser

Copyright © 2026 Miklosoft. Released under the GNU General Public License v3.0.
See [LICENSE](https://github.com/Coffymonk/AdvAstro/blob/main/LICENSE) in the AdvAstro repository on GitHub.

Programmet bygger på arbete av många personer och organisationer; tack allihop.
Licenstexterna för allt som följer med finns i mappen `licenses` bredvid programmet.

<!-- id: credits.libraries -->
## Programbibliotek

| Bibliotek | Används till | Licens |
| --- | --- | --- |
| Qt och Qt for Python (PySide6), The Qt Company | Gränssnittet, PDF-rapporter | LGPL-3.0 |
| NumPy | Numeriska matriser | BSD-3-Clause |
| SciPy | Filtrering, anpassning, statistik | BSD-3-Clause |
| Astropy, The Astropy Collaboration | FITS-filer, koordinater, WCS | BSD-3-Clause |
| PyERFA och ERFA | Astronomiska beräkningar | BSD-3-Clause |
| photutils | Hitta och mäta stjärnor | BSD-3-Clause |
| Pillow | JPEG-, PNG- och WebP-bilder | MIT-CMU |
| tifffile och imagecodecs, Christoph Gohlke | TIFF-bilder och komprimering | BSD-3-Clause |
| python-lz4, python-zstandard | Komprimerade XISF-filer | BSD-3-Clause |
| PyYAML, packaging | Används av Astropy | MIT; Apache-2.0 eller BSD-2-Clause |

Qt används under GNU Lesser General Public License 3.0. Dess bibliotek är separata filer i
programmappen och kan bytas ut; Qts källkod finns på
<https://www.qt.io/download-open-source>. Programmet paketeras med PyInstaller.

<!-- id: credits.data -->
## Data

**Djuprymdskatalog**: OpenNGC av Mattia Verga (<https://github.com/mattiaverga/OpenNGC>),
licensierad under CC BY-SA 4.0. AdvAstro levereras med en bantad kopia under samma licens.

<!-- id: credits.services -->
## Onlinetjänster

Används bara av himmelskontrollerna och jämförelserna i Betygsätt min bild.

- **Gaia**: detta arbete använder data från Europeiska rymdorganisationens (ESA) uppdrag Gaia
  (<https://www.cosmos.esa.int/gaia>), bearbetade av Gaia Data Processing and Analysis
  Consortium (DPAC). DPAC finansieras av nationella institutioner, särskilt de som deltar i
  Gaia Multilateral Agreement.
- **VizieR**: katalogverktyget VizieR, CDS, Strasbourg, Frankrike (DOI 10.26093/cds/vizier).
- **hips2fits och HiPS**: en tjänst från CDS, Strasbourg, Frankrike.
- **Digitized Sky Survey (DSS2)**: framtagen vid Space Telescope Science Institute med
  amerikanska statens anslag NAG W-2166, baserad på fotografiska data från Oschin
  Schmidt-teleskopet på Palomar Mountain och UK Schmidt-teleskopet.
- **Pan-STARRS1 Surveys (PS1)**: Institute for Astronomy, University of Hawaii, Pan-STARRS
  Project Office och partnerinstitutioner.
- **Mellingers helhimmelspanorama**: © Axel Mellinger (PASP 121, 1180, 2009).
- **AstroBin**: via dess öppna API med din egen nyckel. Bilderna tillhör sina fotografer och
  länkas bara, de sparas aldrig.

<!-- id: credits.programs -->
## Program som AdvAstro samarbetar med

- **ASTAP** av Han Kleijn (<https://www.hnsky.org/astap.htm>) sköter plattlösningen. Det är
  ett separat program som du installerar själv.
- Den automatiska visningssträckningen följer metoden i PixInsights ScreenTransferFunction.
- Råden hänvisar till PixInsight (Pleiades Astrophoto), Siril (Free-Astro-teamet), GraXpert,
  StarNet och RC Astros BlurXTerminator, NoiseXTerminator och StarXTerminator. AdvAstro läser
  filer från NINA, ASIAIR, SharpCap, KStars/Ekos, Sequence Generator Pro, APT med flera.

Alla produktnamn och varumärken tillhör sina ägare. AdvAstro är ett fristående projekt och
har ingen koppling till, eller stöd från, någon av dem.

<!-- id: credits.development -->
## Utveckling

Skrivet av Miklosoft, med hjälp av Claude, en AI-assistent från Anthropic. Programikonen är
en egen design gjord för det här projektet.
