<!-- id: rate -->
# Betygsätt min bild

**Betygsätt min bild** bedömer en *färdig* bild, så som en erfaren astrofotograf eller en
tävlingsdomare skulle göra, och talar om exakt hur den kan bli bättre. Det är den tredje
fliken under verktygsfältet (Ctrl+3, eller Ctrl+R). När du växlar mellan Session,
Kalibrering och Betygsätt min bild ligger det som laddats i var och en kvar.

Öppna eller släpp en bild: FITS, XISF, TIFF (8, 16 eller 32 bitar), PNG, JPEG, WebP eller BMP.
JPEG-, PNG- och TIFF-filer som släpps var som helst i fönstret går direkt till Betygsätt min
bild. En fil som fortfarande är linjär (osträckt) känns igen och bedöms på en automatisk
sträckning.

<!-- id: rate.window -->
## Sidan

- **Verktygsfältet** (i det här läget): *Öppna bild*, *Analysera igen*, *Himmelskontroller*,
  ett fält för **Objekt** och *Exportera*. Skriv objektets namn (till exempel *M31* eller
  *NGC 7000*) för att hjälpa plattlösning och jämförelser; det fylls i av sig självt när bilden
  identifierats.
- **Ovanför bilden**: vilken sorts bild det är, **Objekt** och **Stjärnor**
  ([objekttyp och stjärnlösa bilder](help:rate.kind)), och en rad som säger vad den bedömts
  som.
- **Vänster**: bilden, med knappar för överlägg som visar fynden i den.
- **Höger**: flikarna *Omdöme*, *Fynd*, *Förbättra*, *Arbetsflöde*, *Jämför* och *Detaljer*.

<!-- id: rate.kind -->
## Objekttyp och stjärnlösa bilder

En galax, en nebulosa som fyller bilden, en stjärnhop och ett Vintergatsfält ska inte bedömas
på samma sätt. Betygsätt min bild tar reda på vad bilden visar och anpassar omdömet, fynden,
planen och arbetsflödet.

**Objekt** känns igen, i den här ordningen, från plattlösningen (himmelskontroller), namnet
i fältet Objekt, eller objektnamnet i filen. Välj själv i listan när det blir fel eller inte
hittas; bilden bedöms då om direkt, utan att mätas igen.

| Objekttyp | Vad som ändras |
| --- | --- |
| Galax | Bakgrund, brus och detaljer väger tyngre. Färgerna får vara dämpade (dämpat först under 8 %). Kontrastkontrollen över hela bilden hoppas över: en liten galax säger den lite om |
| Emissions-, reflektions-, mörk nebulosa | En nebulosa som fyller bilden (enligt dess storlek, eller att det mesta av bilden är ljust) gör "gradient" och "låg kontrast" mildare: en del av det som ser ut som en gradient är nebulosan. Emissionsnebulosor får vara mer mättade |
| Planetarisk nebulosa | Litet objekt: kontrastkontrollen över hela bilden hoppas över |
| Öppen eller klotformig stjärnhop | Stjärnorna är motivet: stjärnorna väger mest, färglösa stjärnor kan vara ett stort fynd, och kontrollerna "stjärnorna tränger undan objektet", kontrast, mättnad och detaljer hoppas över |
| Vintergatan / vidfält | Många stjärnor är väntat ("stjärnorna tränger undan objektet" hoppas över); ljusstyrkeändringar över fältet blir en notering, eftersom Vintergatan själv är en sådan |

**Stjärnor** anger om bilden är **stjärnlös** (gjord med StarNet eller StarXTerminator).
*Automatiskt* känner igen det: riktiga stjärnfält har tiotals till hundratals små, runda,
ljusa stjärnor per megapixel, medan det som stjärnborttagning lämnar är stort eller svagt.
En stjärnlös bild hoppar över alla stjärnkontroller och Gaia-kontrollerna, och kategorin
*Stjärnor* räknas inte in i poängen. Bakgrund, färg, tonalitet och detaljer bedöms som
vanligt.

<!-- id: rate.verdict -->
## Omdömet

Överst: det samlade **omdömet**, **poäng av 100** och en rad förklaring.

| Omdöme | Betydelse |
| --- | --- |
| **Utmärkt** | Redo för AstroBin, tävlingar och utskrift |
| **Redo att visas** | En gedigen bild med bara små saker att putsa på |
| **Bra, med åtgärdbara brister** | Några riktade ändringar lyfter den en nivå |
| **Behöver arbete** | Bristerna syns för de flesta betraktare |

Hur strikt omdömet är beror på din nivå under [Inställningar › Stil](help:settings.style):

| Nivå | Utmärkt från | Redo från | Åtgärdbar från |
| --- | --- | --- | --- |
| Nybörjare | 86 | 68 | 52 |
| Medel | 90 | 77 | 60 |
| Avancerad | 93 | 84 | 70 |

Vissa saker begränsar omdömet oavsett poäng: ett **stort** fynd (något de flesta betraktare
lägger märke till) håller det på högst *Bra, med åtgärdbara brister*; tre stora fynd, eller
ett kritiskt som en osträckt bild, betyder *Behöver arbete*; fyra eller fler små fynd håller
det på högst *Redo att visas*.

<!-- id: rate.categories -->
## Kategorier

Varje kategori börjar på 100 och tappar poäng per fynd (stort 18, litet 8, kritiskt 45).

| Kategori | Vad den omfattar |
| --- | --- |
| **Stjärnor** | Storlek, rundhet över fältet, ringar, kärnor och färgkanter |
| **Bakgrund** | Himmelsnivå, gradienter, brus, fläckighet och heta pixlar |
| **Färg** | Bakgrundens neutralitet, mättnad och stjärnfärger |
| **Detaljer** | Fin struktur, överdriven utjämning och komprimering |
| **Tonalitet** | Sträckning, kontrast, klippning och bandning |
| **Presentation** | Kanter, storlek och komposition |
| **Djup** | Hur svagt bilden når, mätt mot Gaia (efter himmelskontroller) |

Totalpoängen är ett viktat medelvärde (stjärnor 22 %, bakgrund 20 %, färg 15 %, tonalitet
15 %, detaljer 14 %, presentation 8 %, djup 6 %; vikterna ändras med
[objekttypen](help:rate.kind), till exempel väger stjärnorna 36 % för en öppen stjärnhop och
detaljerna 19 % för en galax), minus 4 poäng per stort och 1 per litet
fynd, eftersom problem som en betraktare ser påverkar hela bilden. Orden: *Utmärkt* från 90,
*Bra* från 75, *Godkänt* från 55, annars *Svagt*.

<!-- id: rate.overlays -->
## Överlägg

Knapparna ovanför bilden ritar mätningarna i den:

- **Stjärnor**: ett kort streck på varje uppmätt stjärna visar utdragning och riktning
  (längre betyder mer utdragen; grönt är litet, rött är stort). Bilden delas i nio områden,
  vart och ett märkt med stjärnstorlek och utdragning, så att koma, lutning och följningsfel
  syns direkt.
- **Bakgrund**: den jämna bakgrundsmodellen. Blått är mörkast, rött ljusast. En ensidig ramp
  är en gradient; fläckar som följer objektet är verklig nebulosa.
- **Brus**: brus per område, blått renast, rött brusigast.
- **Färg**: bakgrundens färg, kraftigt förstärkt; grått betyder neutral.
- **Klippning**: rött där pixlar klippts till vitt, blått där de klippts till svart.
- **Problem**: mörka ringar runt stjärnor (gula ringar), heta pixlar (röda ringar) och
  obeskurna kanter (röda band).

Länken *Visa* på ett fynd byter till det överlägg som visar det.

<!-- id: rate.findings -->
## Fynd

Fliken *Fynd* listar alla fynd, viktigast först, med allvarlighetsgrad (*Kritiskt*, *Stort*,
*Litet* eller *Notering*), kategori och vad som mättes. Under dem listar *Det här fungerar* det
som redan är bra. **?** på ett fynd öppnar förklaringen i
[fyndreferensen](help:rate.reference).

<!-- id: rate.improve -->
## Så förbättrar du bilden

Fliken *Förbättra* gör om fynden till en plan, ordnad efter betydelse: **Åtgärda först**
(stora problem), **Sedan** (små) och **Finputs** (noteringar). Varje steg förklarar varför,
med värden uppmätta i din bild, och ger konkreta steg för PixInsight eller Siril (växla
överst).

När du äger BlurXTerminator, NoiseXTerminator eller StarXTerminator
([Inställningar › Din programvara](help:settings.software)) använder stegen dem. **Nästa gång
vid teleskopet** samlar det du kan ändra vid fotograferingen. *Kopiera* lägger planen i
urklipp.

Många steg görs **genom en mask**, så att en effekt bara når en del av bilden. Under ett
sådant steg öppnar **Så gör du masken** ett recept steg för steg för ditt program:

| Mask | Verkar på | Typisk användning |
| --- | --- | --- |
| Luminans | De ljusa delarna | Skärpning, mättnad, kontrast på objektet |
| Inverterad luminans | De mörka delarna | Brusreducering i himlen |
| Stjärnor | Stjärnorna | Krympa eller färga om stjärnor |
| Intervall (range) | Objektet, med mjuk kant | Lokal kontrast, mättnad på en galax |
| Hörn | Ett hörn | Laga stjärnor eller en gradient i ett hörn |

Siril använder sina verktyg på hela bilden, så recepten där gör ändringen på en kopia och
blandar tillbaka den med PixelMath, med bildens egen ljusstyrka som vikt.

<!-- id: rate.workflow -->
## Arbetsflöde för ditt objekt

Fliken *Arbetsflöde* är en komplett väg för bildbehandlingen för objekttypen, från den
staplade, linjära mastern till den färdiga bilden, för PixInsight eller Siril (växla överst):
beskärning, bakgrundsextraktion, färgkalibrering, dekonvolution, brusreducering,
stjärnseparation, sträckning, lokal kontrast, färg, stjärnor och export.

Varje steg förklarar med enkla ord vad det gör och varför, ger stegen, och lägger till vad du
ska tänka på med den här sortens objekt (till exempel: inga bakgrundspunkter nära en galax
halo; sträck en stjärnhops stjärnor med ArcsinhStretch). Steg märkta **Din bild** åtgärdar
något som Betygsätt min bild hittade i din bild. Steg som inte gäller utelämnas: en stjärnhop
behåller sina stjärnor; en stjärnlös bild har inga stjärnsteg. *Kopiera* lägger arbetsflödet
på urklipp, och *Exportera › Arbetsflöde som Markdown* sparar det.

<!-- id: rate.sky -->
## Himmelskontroller

Efter betygsättningen plattlöser AdvAstro bilden: med lösningen som sparats i filen
(PixInsight och Siril sparar en efter sin egen lösning) eller med ASTAP. Utan ledtråd söker
ASTAP över hela himlen med automatisk fältstorlek, vilket kan ta en minut; skriver du
objektets namn går det mycket fortare. Sedan:

- **Identifieras objektet** och kompositionen bedöms.
- **Mäts djupet**: varje stjärna i bilden matchas mot katalogen Gaia DR3.
  *Gränsmagnituden* är den ljusstyrka där hälften av katalogens stjärnor syns i din bild.
  Ett diagram visar andelen som hittats per magnitud.
- **Kontrolleras stjärnfärgerna**: varje stjärnas färg i din bild jämförs med dess verkliga
  Gaia-färg (BP−RP). En korrelation nära 1 betyder korrekt färgkalibrering; låga värden är
  väntade för smalbands- och dual-band-bilder.
- **Hämtas en kartbild**: samma fält från Pan-STARRS (små fält), DSS2 (de flesta fält) eller
  Mellingers helhimmelskarta (vida fält), i samma pixelrutnät som din bild.

Himmelskontrollerna körs automatiskt (stäng av under
[Inställningar › Jämför](help:settings.compare)) eller med *Himmelskontroller* i
verktygsfältet. De kräver internetanslutning; Gaia-resultat sparas på datorn, så en ny
kontroll av samma fält går snabbt.

<!-- id: rate.compare -->
## Jämföra

Fliken *Jämför* har två delar.

**Kartbild.** Dra reglaget för att tona mellan din bild och kartbilden, eller *Blinka* för att
växla fram och tillbaka. Saknad svag struktur, artefakter och detaljer som inte finns på
riktigt (till exempel från hård AI-skärpning) syns direkt. Kartbilden är en referens, inte en
skönhetstävling: professionella kartläggningar är djupa men ofta grova.

**Andra fotografer.** För att se hur andra fångat samma objekt:

- Med en **AstroBin API-nyckel** ([Inställningar › Jämför](help:settings.compare)): *Hämta från
  AstroBin* visar de mest gillade AstroBin-bilderna av objektet, med fotografens namn. Klicka
  på en för att öppna den på AstroBin. Begär en gratis nyckel på
  <https://www.astrobin.com/api/request-key/>.
- Utan nyckel, med **Öppna söksidor i webbläsaren** påslaget: knappar öppnar sökningar efter
  objektet på AstroBin, Wikimedia Commons och APOD.
- Med inget av dem görs ingen jämförelse.

Jämförelser kräver objektets namn: från himmelskontrollerna, filen eller fältet Objekt.

<!-- id: rate.details -->
## Detaljer och rapporter

*Detaljer* listar alla mätvärden. **Exportera** sparar hela rapporten som **PDF** (med bilden
och kartbilden), **Markdown** (redo att klistra in i ett foruminlägg) eller **JSON**.

<!-- id: rate.limits -->
## Bra att veta

- Mätningarna görs på det du ser: den sträckta bilden, i ljusstyrka från 0 till 100 %.
  Mycket stora bilder (över ungefär 6200 pixlar) mäts i halv storlek.
- AdvAstro är strikt med tekniska fel, som går att mäta, och mild med smak: "kraftig
  mättnad" är en anmärkning, inte en regel.
- Texterna för fynd och råd är än så länge på engelska; fönstret följer ditt språk.

<!-- id: rate.reference -->
## Fyndreferens

Alla fynd som Betygsätt min bild kan rapportera, vad de betyder och gränserna som används.
Värden är andelar av full ljusstyrka (0–100 %).

### Tonalitet

<!-- id: finding.linear -->
#### Bilden har inte sträckts än
Data är fortfarande linjära: den svaga signalen finns men syns inte. Kritiskt. Allt annat
bedöms på en automatisk sträckning. Sträck bilden (GeneralizedHyperbolicStretch eller
HistogramTransformation) efter bakgrundsextraktion och färgkalibrering.

<!-- id: finding.shadow_clip -->
#### Klippta skuggor
Mer än 1 % av pixlarna (stort över 5 %) har en färgkanal på noll. Svartpunkten är för hög,
eller så neutraliserades inte en kanal före sträckningen.

<!-- id: finding.clipped_highlights -->
#### Utbrända högdagrar
Stora ytor utanför stjärnkärnorna är helt vita (litet över 0,02 % av bilden, stort över
0,15 %). Typiskt för ljusa galaxkärnor och M42; sträck med högdagerskydd eller använd
HDRMultiscaleTransform.

<!-- id: finding.low_contrast -->
#### Låg kontrast / objektet kunde vara ljusare
De ljusaste delarna av objektet når mindre än 13 % över bakgrunden (stort under 7 %). Det
finns utrymme för ytterligare en försiktig sträckning och lokal kontrast.

<!-- id: finding.banding -->
#### Luckor i histogrammet (bandning)
Mer än 20 % av nivåerna i det använda området är tomma (stort över 45 %): bilden sträcktes
igen efter att ha sparats med 8 bitar per kanal. Jämna övergångar blir trappsteg. Bearbeta i
32 bitar och exportera till 8 bitar först i sista steget.

<!-- id: finding.banding_risk -->
#### Risk för synlig bandning
I en 8-bitarsfil består mer än 40 % av himlen av platta fläckar med en enda nivå: så jämnt
att konturlinjer kan synas på vissa skärmar. Exportera i 16 bitar, eller behåll lite fint
brus.

### Bakgrund

<!-- id: finding.crushed_black -->
#### Klippt svart bakgrund
Himlen ligger under 2,5 % ljusstyrka och mer än 2 % av pixlarna är klippta till svart. Svaga
stjärnor och svag nebulosa skärs bort.

<!-- id: finding.dark_background -->
#### Mörk / mycket mörk bakgrund
Himlen ligger under 6 % (notering) eller under 4 % (litet). Dramatiskt på en ljus skärm, men
svaga detaljer försvinner. AdvAstros bekväma område är 6–20 %; många erfarna fotografer
siktar på ungefär 8–12 %.

<!-- id: finding.bright_background -->
#### Lite ljus / urblekt bakgrund
Himlen ligger över 20 % (litet) eller 28 % (stort). Den ser grå och disig ut, och kontrasten
blir lidande.

<!-- id: finding.gradient -->
#### Ojämn bakgrund (gradient)
Den jämna bakgrundsmodellen ändras med mer än 5 % över bilden, eller en ensidig ramp med mer
än 3 % (notering eller litet); över 9 %, eller 6 % ensidigt, flaggas det tydligare. I bilder
fulla av nebulosa sänks allvaret, eftersom verklig struktur ser ut som en gradient.
Kontrollera med överlägget *Bakgrund*.

<!-- id: finding.color_gradient -->
#### Färggradient
Himlen ändrar färg över bilden med mer än 4 % mellan kanalerna (stort över 7 %):
ljusförorening eller månljus som inte är neutralt.

<!-- id: finding.noise -->
#### Synligt brus / brusig bakgrund
Bruset mellan pixlar i den mörkaste himlen är över 0,65 % (litet) eller 1,2 % (stort).

<!-- id: finding.color_noise -->
#### Färgbrus
Bruset är färgat (färgbrus över 0,8 % och minst 80 % av ljusstyrkebruset; stort över 1,6 %).
Det brus som är lättast att ta bort utan att förlora detaljer.

<!-- id: finding.mottle -->
#### Fläckig bakgrund
Fläckar några pixlar stora, över 0,26 % i amplitud (stort över 0,45 %) och kraftiga jämfört
med det fina bruset. Fläckighet är brus i större skala än kornet: brusreducering av det fina
kornet (även NoiseXTerminator) lämnar det kvar, och hård utjämning gör det värre. Orsaker:
för kort integrationstid, för lite dithring, och bakgrundsextraktion med för många punkter.
Planen behandlar bara de större skalorna (MultiscaleLinearTransform lager 3–5, eller Sirils
wavelets) genom en inverterad luminansmask, och behåller det fina kornet.

<!-- id: finding.walking_noise -->
#### Möjligt vandrande brus
Bakgrundsbruset har en tydlig riktning (strimmor). Orsakas av långsam drift utan dithring.
Rapporteras som "möjligt" eftersom kraftig diagonal nebulosa kan se likadan ut.

<!-- id: finding.hot_pixels -->
#### Kvarvarande heta pixlar
Mer än 30 isolerade ljusa pixlar, och fler än 3 per megapixel (stort över 25 per megapixel).
En pixel räknas bara när den ligger långt över sin omgivning och grannarna inte lyfts alls:
även en mycket skarp stjärna sprider lite ljus till pixlarna runt sig. Klicka *Visa* för att
kontrollera de markerade pixlarna; är de små stjärnor snarare än enstaka prickar kan du
bortse från fyndet.

### Färg

<!-- id: finding.green_cast -->
#### Grön ton i himlen
Bakgrunden är grönare än neutral med mer än 0,5 % (eller 6 % av himmelsnivån). Ta bort med
SCNR.

<!-- id: finding.color_cast -->
#### Färgad bakgrund
En färg dominerar himlen med mer än 1,2 % av full skala eller 16 % av himmelsnivån (stort
över 2,5 % eller 32 %). Fyndet anger tonen.

<!-- id: finding.muted -->
#### Dämpade färger / nästan färglös
Objektets medianmättnad är under 22 % (litet) eller 12 % (stort). För en galax, vars färger
är subtila, under 8 % (litet) eller 5 % (stort). Kontrolleras inte för stjärnhopar.

<!-- id: finding.oversaturated -->
#### Kraftig mättnad / övermättade färger
Medianmättnad över 72 % eller mer än 10 % av objektet nära full mättnad (litet); över 85 %
eller 30 % (stort). En smaksak upp till en gräns; därefter försvinner de subtila
variationerna.

<!-- id: finding.channel_clip -->
#### Klippt färgkanal
Mer än 1 % av de ljusa ytorna har en kanal vid gränsen: färgdetaljer försvinner och nyansen
förskjuts.

<!-- id: finding.star_color -->
#### Färglösa stjärnor
Spridningen i stjärnfärg är mycket liten: verkliga stjärnor går från blåvita till orange.

<!-- id: finding.magenta_stars -->
#### Magentafärgade stjärnor
Mer än 60 % av stjärnorna är magenta: typiskt för smalbands- och dual-band-data.

<!-- id: finding.color_calibration -->
#### Stjärnfärger mot Gaia
Efter himmelskontroller: bildens stjärnfärger jämförs med deras Gaia-färger. En korrelation
på 0,6 eller mer är bra; 0,3–0,6 är ett litet fynd; lägre betyder att färgkalibreringen
behöver ses över (väntat för smalbands- och dual-band-data).

### Stjärnor

<!-- id: finding.trailed_stars -->
#### Utdragna stjärnor
Medianutdragning över 0,3 med stjärnor som pekar åt samma håll (stort över 0,4): följning,
guidning, balans, vind eller polinställning.

<!-- id: finding.corner_elongation -->
#### Utdragna stjärnor i ett hörn
Stjärnorna i ett hörn har utdragning över 0,3, minst 0,15 mer än i mitten och 0,1 mer än i
de andra hörnen (stort över 0,45). Orsaker: lutning, en fältutjämnare eller reducerare på fel
avstånd med den optiska axeln utanför mitten, kollimering, ett klämt eller förskjutet optiskt
element, eller roterade delbilder i stapeln. Planen förklarar hur du skiljer dem åt på en
enda delbild (AberrationInspector) och hur du lagar den här bilden.

<!-- id: finding.stars_soft -->
#### Ganska stora / stora, mjuka stjärnor
Typiska stjärnor är bredare än 4,6 pixlar vid halv ljusstyrka (stort över 6,5). Fokus,
seeing eller en kraftig sträckning. 3,6 pixlar eller mindre räknas som skarpt.

<!-- id: finding.big_stars -->
#### Ljusa stjärnor dominerar
De ljusaste stjärnornas kärnor är bredare än 1,2 % av bildens diagonal (stort över 2 %).

<!-- id: finding.star_dominance -->
#### Stjärnorna tränger undan objektet
Stjärnorna täcker mer än 22 % av ett tätt stjärnfält. Stjärnreducering låter objektet ta
plats.

<!-- id: finding.corner_stars -->
#### Mjukare stjärnor i hörnen
Hörnstjärnorna är mer än 20 % större än i mitten (stort över 40 %). Utdragna mot eller bort
från mitten betyder koma (bakfokus); längs cirklar betyder astigmatism eller fältkrökning.

<!-- id: finding.tilt -->
#### Ojämn skärpa mellan hörnen
Det skarpaste och det mjukaste hörnet skiljer sig med mer än 30 % (stort över 50 %).
Sensorlutning är bara en möjlig orsak. Andra: bakfokus lite fel med den optiska axeln utanför
mitten; kollimering; klämd eller förskjuten optik; böjning (flexure); och själva staplingen
(delbilder roterade efter en meridianvändning eller mellan nätter, eller en beskärning som
inte är centrerad). Kontrollera en enda delbild: är den jämn så orsakar staplingen eller
beskärningen det. Vrider du kameran 90° skiljer du orsaker på kamerasidan (de följer med) från
orsaker i teleskopet (de stannar kvar).

<!-- id: finding.star_rings -->
#### Mörka ringar runt stjärnor
Mer än 10 % av de ljusa stjärnorna (stort över 25 %) har en mörk ring: överdriven skärpning
eller för många iterationer i dekonvolutionen.

<!-- id: finding.white_cores -->
#### Vita stjärnkärnor
Mer än 60 % av de ljusa stjärnorna har klippta vita kärnor, så deras färg går förlorad.

<!-- id: finding.fringe -->
#### Färgade stjärnkanter
Stjärnorna är mer än 0,7 pixlar större i blått än i rött (eller tvärtom), eller rött och blått
är förskjutna mer än 1,2 pixlar mot kanterna: kromatisk aberration eller kanaler som inte är
i linje.

<!-- id: finding.few_stars -->
#### För få stjärnor att mäta
Färre än 15 stjärnor hittades, men bilden var inställd på *Med stjärnor*. Stjärnkontrollerna
hoppas över.

<!-- id: finding.starless -->
#### Bedömd som stjärnlös bild
Bilden är stjärnlös (upptäckt, eller vald under **Stjärnor**). Stjärnkontrollerna och
Gaia-kontrollerna hoppas över och kategorin *Stjärnor* räknas inte in i poängen; allt annat
bedöms som vanligt. Se [objekttyp och stjärnlösa bilder](help:rate.kind).

### Detaljer

<!-- id: finding.low_detail -->
#### Lite fina detaljer
Den fina strukturen i objektet når mindre än 1,6 gånger över bruset.

<!-- id: finding.plastic -->
#### Bakgrunden ser överutjämnad ut
Nästan inget brus alls (under 0,06 %) i en 16- eller 32-bitarsfil: brusreduceringen har gått
så långt att himlen kan se plastig ut, och svaga detaljer försvinner med bruset.

<!-- id: finding.jpeg -->
#### JPEG-komprimering
Uppskattad JPEG-kvalitet under 85 eller synliga kanter i 8×8-block (stort under 70).
Exportera med kvalitet 92–95 från en master i 16 eller 32 bitar.

### Presentation

<!-- id: finding.edges -->
#### Staplingskanter inte beskurna
Mörka, ljusa eller brusiga band längs en kant där inte alla delbilder överlappade. Stort.

<!-- id: finding.small_image -->
#### Liten bild
Under en megapixel. Dela minst 3000 pixlar på långsidan.

<!-- id: finding.eight_bit -->
#### 8-bitarsfil
Bra för delning; behåll en master i 16 eller 32 bitar för utskrift och ny bearbetning.

<!-- id: finding.off_centre -->
#### Motivet ligger utanför mitten
Det mesta av ljuset ligger åt ena sidan. En medveten placering kan fungera bra; detta är en
notering.

<!-- id: finding.framing -->
#### Komposition
Efter himmelskontroller: hur stor del av bilden det identifierade objektet fyller.

### Djup

<!-- id: finding.depth -->
#### Djup
Efter himmelskontroller: gränsmagnituden mot Gaia. För fält smalare än 3° räknas magnitud 18
eller djupare som djupt och 16–18 som typiskt; för vidare fält 15,5 och 13,5–15,5.
