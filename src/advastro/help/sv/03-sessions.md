<!-- id: session -->
# Analysera en session

<!-- id: session.window -->
## Huvudfönstret

- **Lägesflikar** under verktygsfältet: *Session* (det här kapitlet), *Kalibrering*
  ([kalibreringsbilderna](help:calibration)) och *Betygsätt min bild*
  ([färdiga bilder](help:rate)). Var och en behåller det som laddats; fliken visar ett antal
  och ett varningstecken när något flaggats. Ctrl+1, Ctrl+2 och Ctrl+3 växlar mellan dem.
- **Verktygsfältet**: *Öppna*, *Analysera* (igen), *Stoppa*, *Lös*, *Förslag*, *Exportera*,
  och till höger *Inställningar*, *Natt* och *Hjälp*. Verktygen ändras med läget.
- **Tabellen**: en rad per fil. Klicka på en rad för att förhandsvisa den.
- **Filterknappar** ovanför tabellen: *Alla*, *Flaggade*, *Borttagna*.
- **Förhandsvisningen**: den valda filen med automatisk sträckning. Mushjulet zoomar, dra för
  att panorera, dubbelklicka för att växla mellan anpassad och 100 %.
- **Flikarna** under förhandsvisningen: *Session*, *Objekt* och *Arbetsflöde*.
- **Statusraden**: förlopp och korta meddelanden.

<!-- id: session.columns -->
## Vad kolumnerna betyder

| Kolumn | Betydelse | Säger något om |
| --- | --- | --- |
| Behåll | Kryssruta: behåll delbilden för stapling | Ditt urval |
| ⚠ | Delbilden sticker ut; håll pekaren över för orsaken | Problem |
| Fil | Filnamn (den gemensamma delen av alla namn förkortas) | |
| FWHM px | Stjärnstorlek vid halva ljusstyrkan, i pixlar | Seeing, fokus |
| FWHM ″ | Samma i bågsekunder (kräver bildskalan) | Seeing, fokus |
| Exc. | Stjärnornas utdragning (excentricitet): 0 är rund | Följning, guidning, vind |
| Stjärnor | Antal hittade stjärnor | Moln, dis, dagg |
| Bakgrund | Himmelns ljusstyrka i ADU | Måne, gryning, ljusförorening |
| Brus | Bakgrundsbrus i ADU | Himmelsljus, gain |
| SNR | Stjärnornas mediantopp delat med bruset | Helhetskvalitet |

Håll pekaren över en kolumnrubrik för en kort förklaring.

<!-- id: session.flags -->
## Så bedöms delbilderna

Delbilderna jämförs med **resten av samma session**, inte med fasta tal, så bedömningen
anpassar sig efter din utrustning och din himmel. En delbild flaggas när:

- **stjärnorna är större** än sessionens median med mer än *3 σ* (robust spridning), vilket
  tyder på seeing, fokusdrift eller vind;
- **stjärnorna är utdragna**: excentricitet över *0,6*, vilket tyder på följning, guidning
  eller vind;
- den har **betydligt färre stjärnor**: under *60 %* av sessionens median, vilket tyder på
  moln, dis eller dagg;
- **himlen är ljusare** än medianen med mer än *4 σ*, vilket tyder på månen, gryning, en
  ljuskälla eller moln som lyses upp underifrån.

Siffrorna i kursiv är strikthet *Normal*; ändra dem under
[Inställningar › Bildurval](help:settings.selection). Flaggade delbilder är
avbockade i det föreslagna urvalet. Håll pekaren över varningstecknet för de exakta värdena.

<!-- id: session.keep -->
## Behålla och välja bort delbilder

- Klicka i en kryssruta för att behålla eller välja bort en delbild.
- Markera flera rader och tryck **Mellanslag** (växla), **K** (behåll) eller **R** (välj
  bort), eller högerklicka för en meny.
- **Förslag** i verktygsfältet återställer allt till AdvAstros förslag.
- Dina val uppdaterar sessionsstatistiken och arbetsflödet direkt.

<!-- id: session.summary -->
## Fliken Session

Visar sessionen i korthet: behållna delbilder, median-FWHM, excentricitet, antal stjärnor,
brus och **sampling**:

- **Undersamplad** (stjärnor under 2 px): stjärnorna blir kantiga; drizzle hjälper.
- **Välsamplad** (2–5 px): idealiskt.
- **Översamplad** (över 5 px): binning eller en reducerare ger samma detaljer med mindre brus.

Under det listar **Behöver uppmärksamhet** varje flaggad delbild med orsak (klicka på en för
att markera den i tabellen) och filer som inte kunde läsas. När du står på en
kalibreringsflik visar fliken Session i stället
[kalibreringskontrollerna](help:calibration).

<!-- id: session.dither -->
## Dithring och drift

AdvAstro mäter hur stjärnorna flyttar sig mellan delbilderna. Slumpmässiga hopp på några
pixlar betyder att du **dithrat**, vilket är bra: heta pixlar och vandrande brus rensas bort
vid staplingen. En långsam, jämn krypning åt ett håll betyder **drift** (polinställning eller
ingen guidning). Arbetsflödet använder detta: drizzle föreslås bara för dithrade data, och
sessioner utan dithring får steget "Dithra nästa gång".

<!-- id: session.export -->
## Exportera

Menyn **Exportera** sparar, för den bildtyp du tittar på:

- **Lista över borttagna** eller **behållna filer**: en fullständig sökväg per rad; läs in den
  i PixInsight, Siril eller ett skript.
- **Rapport som CSV** för ett kalkylblad, eller **JSON** för andra program.
- **Arbetsflöde som Markdown**: fliken Arbetsflöde som text.

<!-- id: session.night -->
## Nattläge

**Natt** (Ctrl+N) gör hela fönstret rött, även förhandsvisningen, så att ögonen behåller sitt
mörkerseende vid teleskopet.
