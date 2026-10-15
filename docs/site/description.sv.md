# Advanced Astrophoto Analyzer

**Vet vad dina data är värda, och vad du ska göra med dem.**

*Kort version (för ett produktkort eller en länkförhandsvisning):*
Advanced Astrophoto Analyzer är ett kostnadsfritt analys- och rådgivningsverktyg för
djuprymdsfotografering. Det mäter varje delbild, kontrollerar kalibreringsbilderna, tar reda
på vad du fotograferat, skriver ett bearbetningsflöde steg för steg för PixInsight eller
Siril, och betygsätter dina färdiga bilder med ett tydligt omdöme och en plan för att göra
dem bättre. För Windows, macOS och Linux.

---

## Vad det är

Varje astrofotograf känner igen frågorna. Vilka delbilder ska jag slänga? Duger mina darks
och flats? Ska jag använda drizzle? Varför ser bakgrunden fläckig ut? Är bilden bra nog att
visa upp?

AdvAstro svarar med mätningar, inte gissningar. Det läser dina filer, mäter det som
spelar roll och förklarar varje fynd på vanlig svenska med dina egna siffror, från natten
vid teleskopet till den färdiga bilden.

Det är ett **analys- och rådgivningsverktyg**. Det ändrar aldrig dina filer och staplar eller
bearbetar aldrig bilder: det gör PixInsight, Siril och dina andra program. AdvAstro talar om
hur.

## Innan du staplar: analysera sessionen

- **Varje delbild mäts**: stjärnstorlek (FWHM), rundhet, antal stjärnor, himmelsljus, brus,
  signal-brusförhållande, gradienter, dithring och drift.
- **De dåliga delbilderna hittas åt dig**: delbilderna jämförs med resten av samma natt, så
  bedömningen passar din utrustning och din himmel. Varje flagga säger varför: seeing, fokus,
  följning, moln, månen.
- **Kalibreringsbilderna kontrolleras**: ljusläckage i darks, amp glow, rander, flatnivå,
  vinjettering, damm, och om darks och flats verkligen matchar dina ljusbilder.
- **Ditt objekt identifieras** utifrån plattlösningen i filerna, med den kostnadsfria
  plattlösaren ASTAP, utifrån teleskopets pekriktning eller objektets namn, med en skiss av
  hur det passar i fältet.
- **Ett bearbetningsflöde skrivet för dina data**: varje steg för PixInsight eller Siril, med
  konkreta inställningar och skälet till varje. En galax får ett annat flöde än en nebulosa
  eller en stjärnhop, och råden anpassas efter sampling, dithring, filter och de verktyg du
  äger (bland annat BlurXTerminator, NoiseXTerminator, StarXTerminator, GraXpert och StarNet).

## Efter bearbetningen: Betygsätt min bild

Släpp en färdig bild (FITS, XISF, TIFF, PNG eller JPEG) och få ett ärligt andra utlåtande:

- **Ett omdöme**: *Utmärkt*, *Redo att visas*, *Bra, med åtgärdbara brister* eller *Behöver
  arbete*, med poäng och betyg för stjärnor, bakgrund, färg, detaljer, tonalitet och
  presentation. Hur strikt det är följer din erfarenhetsnivå.
- **Varje fynd visas i bilden**: stjärnornas form över fältet, gradienter, brus, färgtoner,
  klippning, ringar från överdriven skärpning, heta pixlar, obeskurna kanter.
- **En skräddarsydd förbättringsplan**: vad du ska åtgärda först, med exakta steg i
  PixInsight eller Siril, och vad du kan ändra vid teleskopet nästa gång.
- **Kontrollerad mot himlen**: hur djupt bilden når, mätt mot stjärnkatalogen Gaia; om
  stjärnfärgerna stämmer med deras verkliga färger; och samma fält från en professionell
  himmelskartläggning att blinka mot din bild.
- **Jämförd med andras**: se de mest gillade AstroBin-bilderna av samma objekt, eller öppna
  sökningar i webbläsaren.
- **Rapporter** som PDF, Markdown för foruminlägg, eller JSON.

## Gjort för riktiga astrofotografer

- **Vänligt för nybörjare, snabbt för experter**: förklaringar och menyvägar när du vill ha
  dem, en kompakt lista när du inte vill.
- **Nattläge** som bevarar mörkerseendet vid teleskopet.
- **Kommandorad** för batchkörningar och skript.
- **Fungerar med dina filer**: FITS och XISF från NINA, ASIAIR, SharpCap, Ekos, SGP, APT,
  PixInsight och Siril. Kamerornas råfiler är på väg.
- **Engelska och svenska**, med fler språk på gång.
- **Inbyggd manual**: tryck F1 var som helst för hjälp om det du tittar på.

## Fritt och öppen källkod

Advanced Astrophoto Analyzer är fri programvara under GNU General Public License 3.0. Använd det,
studera det, ändra det och dela det. Källkoden finns på GitHub.

## Systemkrav

- Windows 10 eller 11, macOS på Apple Silicon, eller 64-bitars Linux
- Valfritt: ASTAP (gratis) för att plattlösa filer som inte redan är lösta
- Valfritt: internetanslutning för himmelskontroller och jämförelser i Betygsätt min bild

## Status

AdvAstro utvecklas aktivt. Sessionsanalys, kalibreringskontroller, identifiering av
objekt, bearbetningsflöden och Betygsätt min bild fungerar redan i dag; kamerornas råfiler,
fler bearbetningsprogram och sessioner med flera filter är nästa steg. Synpunkter är
mycket välkomna.

**Ladda ner** · **Källkod på GitHub** · **Användarmanual**
