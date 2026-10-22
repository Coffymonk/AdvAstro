<!-- id: start -->
# Kom igång

<!-- id: start.install -->
## Installation

Ladda ner installationsprogrammet för ditt system från <https://miklosoft.se/main> eller
GitHubs release-sida:

- **Windows 10/11**: kör `AdvancedAstrophotoAnalyzer-…-windows-x64-setup.exe`. Det
  installerar programmet under *Program Files* (eller bara för dig, om du väljer det),
  lägger det i Start-menyn, skapar en genväg på skrivbordet (bocka ur om du inte vill ha
  den) och kan lägga
  kommandoradsverktyget `advastro` i PATH. Avinstallera under *Inställningar › Appar*.
- **macOS (Apple Silicon)**: öppna `AdvancedAstrophotoAnalyzer-…-macos-arm64.dmg` och dra
  **Advanced Astrophoto Analyzer** till mappen *Program*. Vill du hellre ha en
  installationsguide? Använd `.pkg`-filen; den lägger appen i *Program* åt dig.
- **Linux**: packa upp `.tar.gz`-filen och starta **Advanced Astrophoto Analyzer** i mappen.

Det finns också zip-filer med appen om du hellre vill slippa installera något.

Installationsprogrammen är ännu inte kodsignerade:

- **Windows**: om SmartScreen varnar, klicka *Mer information › Kör ändå*.
- **macOS**: om macOS vägrar öppna appen eller `.pkg`-filen, öppna *Systeminställningar ›
  Integritet och säkerhet* och välj *Öppna ändå* (eller högerklicka på filen och välj
  *Öppna*).

<!-- id: start.astap -->
## Ställa in plattlösning (valfritt)

Många inspelningsprogram (ASIAIR, NINA, SharpCap med lösning påslagen) skriver redan en
plattlösning i varje fil; AdvAstro använder den direkt och behöver inget mer.

För andra filer, installera den kostnadsfria plattlösaren **ASTAP** och en stjärndatabas:

1. Ladda ner ASTAP från <https://www.hnsky.org/astap.htm> och installera det.
2. Installera en stjärndatabas: **D50** passar de flesta uppställningar; **D20** eller
   **D05** räcker för små sensorer och långa brännvidder. Windows-installationen lägger den i
   en mapp `Database` inuti ASTAP-mappen.
3. Öppna *Inställningar › Plattlösning*. AdvAstro letar på de vanliga ställena (i Windows
   `C:\Program Files\astap`) och visar vad det hittade. Om ASTAP inte hittades, klicka
   *Bläddra…* och peka på ASTAP-programmet eller bara dess mapp.

AdvAstro löser en tillfällig kopia; det skriver aldrig i dina bilder.

<!-- id: start.folders -->
## Så organiserar du en sessionsmapp

AdvAstro fungerar bäst med den mappstruktur de flesta inspelningsprogram skapar:

```
Session-2026-10-14_NGC7000/
  LIGHT/         ljusbilder (delbilder)
  DARK/          darks
  FLAT/          flats
  BIAS/          bias
  FLAT DARK/     flat darks (även "DARKFLAT", "Dark Flats" …)
  session.mksession   (valfri, från Miklosofts sessionslogg)
```

- Öppna sessionsmappen eller `LIGHT`-mappen; båda fungerar.
- Mappnamn känns igen på engelska i de vanliga stavningarna (singular eller plural, med
  eller utan "frames"). Masterfiler (`masterDark…`, `masterFlat…`) hittas i sessionsmappen
  eller i en `Master`-mapp.
- Du kan också öppna en kalibreringsmapp för sig (till exempel `DARK`) för att bara
  kontrollera de bilderna.

<!-- id: start.first -->
## Din första analys

1. Starta AdvAstro och släpp sessionsmappen på fönstret, eller klicka *Välj mapp…*.
2. Delbilderna visas i tabellen medan de mäts. Varje tar en bråkdel av en sekund; alla
   processorkärnor används.
3. När delbilderna är klara identifierar AdvAstro målet, kontrollerar kalibreringsbilderna
   och skriver arbetsflödet.
4. Titta i fliken **Session** efter sådant som behöver uppmärksamhet, gå igenom de flaggade
   delbilderna (håll muspekaren över varningstecknet för att se varför), och exportera sedan
   listan över behållna eller bortvalda filer, eller följ fliken **Arbetsflöde**.

<!-- id: start.files -->
## Filformat som stöds

| Användning | Format |
| --- | --- |
| Delbilder och kalibreringsbilder | FITS (`.fits`, `.fit`, `.fts`), XISF (`.xisf`, all komprimering) |
| Betygsätt min bild | FITS, XISF, TIFF (8, 16 och 32 bitar, komprimerad eller inte), PNG, JPEG, WebP, BMP |
| Sessionsinformation | Miklosofts `.mksession`- och `.mktargets`-filer |

Färgbilder (one-shot-colour) mäts utan debayering, på 2×2-superpixlar, så att ingen
interpolering påverkar siffrorna.
