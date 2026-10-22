<!-- id: intro -->
# Introduktion

Advanced Astrophoto Analyzer (förkortat AdvAstro) analyserar och ger råd för
djuprymdsfotografering. Programmet tittar på dina data och berättar, med dina egna siffror,
vad som är bra, vad som inte är det och vad du kan göra åt det.

Det **ändrar aldrig dina filer** och **staplar eller bearbetar aldrig bilder**. Det gör ditt
eget program (PixInsight, Siril med flera); AdvAstro talar om hur.

<!-- id: intro.what -->
## Vad programmet gör

1. **Mäter varje delbild** i en session: stjärnstorlek (FWHM), utdragning, antal stjärnor,
   himmelsljusstyrka, brus, signal-brusförhållande, gradient, dithring och drift. Delbilder
   som sticker ut från resten av sessionen flaggas, med orsak, och lämnas utanför det
   föreslagna urvalet.
2. **Kontrollerar kalibreringsbilderna**: bias, darks, flats och flat darks, var för sig och
   mot ljusbilderna (ljusläckage, amp glow, rander, flatnivå, vinjettering, damm, matchande
   exponering, gain och temperatur).
3. **Tar reda på vad du fotograferat** utifrån plattlösningen i filerna, med ASTAP, utifrån
   teleskopets pekriktning eller objektets namn, och visar hur objektet passar i fältet.
4. **Föreslår ett bearbetningsflöde** för PixInsight eller Siril, steg för steg, med konkreta
   inställningar och skälet till varje steg. En galax får ett annat flöde än en nebulosa
   eller en stjärnhop.
5. **Betygsätter färdiga bilder** (*Betygsätt min bild*): ett omdöme, poäng per kategori,
   varje fynd visat i bilden, en skräddarsydd förbättringsplan, kontroller mot
   stjärnkatalogen Gaia och en himmelskartläggning, och jämförelser med andra fotografers
   bilder.

<!-- id: intro.tour -->
## En snabb rundtur

- **Tre lägen**, som flikar under verktygsfältet. Vart och ett behåller det som laddats, och
  verktygsfältet visar det lägets verktyg:
    - **Session** (Ctrl+1): öppna en sessionsmapp. Tabellen visar varje delbild. Till höger
      finns en förhandsvisning och tre flikar: **Session** (sammanfattning och det som behöver
      uppmärksamhet), **Objekt** (vad du fotograferat) och **Arbetsflöde** (hur du bearbetar
      det).
    - **Kalibrering** (Ctrl+2): bias, darks, flats och flat darks som hittats bredvid
      ljusbilderna, med alla kontroller. Dubbelklicka på en bild för hela analysen.
    - **Betygsätt min bild** (Ctrl+3 eller Ctrl+R): bedöm en färdig bild, med en plan för att
      förbättra den och ett arbetsflöde för objektet.
- **Inställningar** (Ctrl+,): din utrustning, hur strikt urvalet är, plattlösning, dina
  program, din stil och jämförelser.
- **Hjälp** (F1): den här manualen. F1 öppnar avsnittet om det du tittar på.

<!-- id: intro.requirements -->
## Krav

- Windows 10 eller 11, macOS på Apple Silicon eller Linux (64-bitars).
- Filer: FITS och XISF för delbilder och kalibreringsbilder; för Betygsätt min bild även
  TIFF, PNG, JPEG och WebP. Råfiler från kameror (CR2, CR3, NEF, ARW) är planerade.
- Valfritt: [ASTAP](https://www.hnsky.org/astap.htm) (gratis) för att plattlösa filer som
  inte redan är lösta.
- Valfritt: en internetanslutning för Gaia-, kartbilds- och AstroBin-funktionerna i
  Betygsätt min bild. Allt annat fungerar utan nät.

<!-- id: intro.licence -->
## Licens och webbplats

Advanced Astrophoto Analyzer är fri programvara under GNU General Public License version 3 (GPL-3.0):
fri att använda, studera, ändra och dela. Källkod och nedladdningar finns på GitHub och på
<https://miklosoft.se/main>.
