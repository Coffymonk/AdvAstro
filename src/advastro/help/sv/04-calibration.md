<!-- id: calibration -->
# Kalibreringsbilder

AdvAstro kontrollerar bias, darks, flats och flat darks som ligger bredvid ljusbilderna, var
för sig och mot ljusbilderna. Stäng av det under
[Inställningar › Bildurval](help:settings.selection) om du vill.

Varje typ får en egen flik ovanför tabellen, och fliken Session listar alla kontroller.
Klicka på en flaggad fil i listan för att markera den i tabellen. Avvikande bilder bockas
av i det föreslagna urvalet, precis som delbilder.

Ny på kalibreringsbilder? Börja med [varför de behövs](help:calibration.why). Varje
kontroll nedan berättar vad som mäts, varför det spelar roll, när AdvAstro varnar och vad du
kan göra.

<!-- id: calibration.why -->
## Varför kalibreringsbilder?

Varje ljusbild innehåller mer än himlen. Kameran lägger till en fast elektronisk nivå,
värmesignal, heta pixlar och glöd, och teleskopet lägger till ojämn belysning och
dammskuggor. Kalibreringsbilderna fångar var och en av dessa för sig, så att ditt
staplingsprogram kan dra ifrån eller dividera bort dem ur varje ljusbild.

| Bild | Vad den fångar | Vad den tar bort ur ljusbilderna | Så tar du den |
| --- | --- | --- | --- |
| Bias | Kamerans fasta grundnivå och utläsningsmönster | Offset och fast mönster | Kortast möjliga exponering, lock på, samma gain och offset som ljusbilderna |
| Dark | Värmesignal (mörkerström), heta pixlar och amp glow | Heta pixlar, glöd och värmesignal | Samma exponering, gain, offset och temperatur som ljusbilderna, lock på |
| Flat | Hur jämnt ljuset når varje pixel | Vinjettering (mörka hörn) och dammskuggor | Ett jämnt belyst mål (ljuspanel eller gryningshimmel), samma fokus och rotation som ljusbilderna |
| Flat dark | En flats grundnivå och värmesignal | Nivån som annars skulle snedvrida flats | Samma exponering och gain som flats, lock på |

Du behöver antingen flat darks eller biasbilder för att kalibrera flats. Många kameror med
låg mörkerström klarar sig med bias i stället för flat darks; flat darks fungerar alltid.

En **master** är en uppsättning kalibreringsbilder som medelvärdesbildats till en enda.
Medelvärdet sänker det slumpmässiga bruset, så en master av många bilder lägger mindre brus
på dina ljusbilder.

<!-- id: calibration.columns -->
## Kolumner

| Kolumn | Bilder | Betydelse |
| --- | --- | --- |
| Exp | alla | Exponeringstid |
| Temp | alla | Sensortemperatur enligt headern |
| Nivå | darks, bias, flat darks | Mediannivå i ADU |
| Brus | darks, bias, flat darks | Utläsningsbrus plus brus från mörkerström |
| Heta px | darks, bias, flat darks | Pixlar långt över sin omgivning |
| Glöd | darks, bias, flat darks | Ljusaste kant eller hörn över mitten (amp glow) |
| Rander | darks, bias, flat darks | Styrka på rad- eller kolumnmönster |
| Nivå (%) | flats | Medianljusstyrka som andel av full skala |
| Vinjettering | flats | Hur mycket mörkare hörnen är än mitten |
| Damm | flats | Hittade dammskuggor ("munkar") |

En ★ framför ett namn betyder en masterbild. ADU och andra begrepp förklaras i
[ordlistan](help:calibration.glossary).

<!-- id: calibration.checks -->
## Kontroller av varje uppsättning

De här kontrollerna tittar på en typ av bild i taget. Bilderna i en uppsättning ska vara
nästan kopior av varandra; en som avviker är oftast ett misstag och skulle förstöra mastern.

<!-- id: calibration.check.odd -->
### Avvikande bilder i en uppsättning

**Vad som kontrolleras.** Varje bilds exponering, gain, offset, binning, temperatur och
bildstorlek jämförs med resten av uppsättningen, liksom nivå och brus.

**Varför.** Staplingsprogrammet medelvärdesbildar uppsättningen till en master. En bild med
en annan inställning blandar in en annan signal, och mastern stämmer inte längre med dina
ljusbilder.

**AdvAstro flaggar en bild när** (i uppsättningar med tre bilder eller fler):

- exponeringen skiljer mer än 1 %, eller gain, offset, binning eller bildstorlek skiljer
  över huvud taget;
- temperaturen skiljer mer än 1,5 °C från resten;
- en flat är mer än 15 % ljusare eller mörkare än de andra flats (panelen eller himlen
  ändrades);
- en bild av dark-typ har mer än 1,3 gånger så mycket brus som resten.

**Vad du gör.** Lämna bort de flaggade bilderna; AdvAstro har redan bockat av dem.

<!-- id: calibration.check.leak -->
### Nivån genom serien (ljusläckage)

**Vad som kontrolleras.** Mediannivån för varje dark, bias och flat dark, i den ordning de
togs.

**Varför.** Med locket på ska inget ljus nå sensorn, så alla bilder i en uppsättning ska ha
samma nivå, plus minus lite brus. En nivå som stiger genom serien betyder att ljus kommer
in: ett otätt lock, en glipa vid filterhjul eller off-axis guider, eller darks tagna i
dagsljus. Läckt ljus i en masterdark dras från varje ljusbild och lämnar mörka fläckar.

**AdvAstro varnar när** nivåerna i en uppsättning sprider sig mer än två gånger bruset, och
säger om de stiger genom serien. En enskild bild långt över resten flaggas som möjligt
ljusläckage; en långt under tyder på en annan offset-inställning.

**Vad du gör.** Täck teleskopet och kameran (ett mörkt tyg över allt fungerar bra), ta darks
på natten eller inomhus, och lämna bort de ljusaste bilderna.

<!-- id: calibration.check.glow -->
### Amp glow

**Vad som kontrolleras.** Nivån i hörn och kanter jämfört med mitten av dina darks.

**Varför.** Vissa sensorer har kretsar nära en kant som blir varma och glöder under långa
exponeringar. Det ser ut som ett ljust dis i ett hörn. Glöden är densamma i varje
exponering, så en matchande dark tar bort den helt; en dark med annan längd eller
temperatur gör det inte.

**AdvAstro noterar det när** en kant eller ett hörn ligger mer än tre gånger bruset över
mitten, och säger vilket.

**Vad du gör.** Ingenting, så länge dina darks matchar ljusbilderna. Använd inte
dark-skalning eller "optimera darks" i staplingsprogrammet: de skalar glöden fel.

<!-- id: calibration.check.banding -->
### Rander

**Vad som kontrolleras.** Hur mycket varje rad och varje kolumn skiljer sig från sina
grannar, efter att långsamma förändringar över bilden tagits bort.

**Varför.** Många kameror lägger till svaga vågräta eller lodräta ränder vid utläsningen.
En del av mönstret ändras från bild till bild och jämnas bara ut över många bilder. En
master av för få bilder för med sig ränderna in i ljusbilderna.

**AdvAstro varnar när** ränderna är starkare än 0,3 gånger bruset.

**Vad du gör.** Ta fler bilder till mastern (30 eller fler). Kraftiga rander i den färdiga
bilden kan också minskas med randverktyg i PixInsight eller Siril.

<!-- id: calibration.check.hot -->
### Heta pixlar

**Vad som kontrolleras.** Pixlar som är mycket ljusare än sin egen omgivning i dina darks
(mer än tio gånger bruset), räknade som antal och som andel av sensorn.

**Varför.** Heta pixlar är enskilda pixlar som samlar värmesignal mycket snabbare än resten.
De syns som färgade prickar eller, efter dithering och stapling, som korta streck. Darks tar
bort de flesta; resten tas bort med kosmetisk korrigering eller med avvisning vid
staplingen.

**AdvAstro redovisar** antalet vid din exponering och temperatur. Det är information, inte
ett fel: antalet växer med längre exponering och varmare sensor.

**Vad du gör.** Använd matchande darks, dithra när du fotograferar och använd kosmetisk
korrigering för det som blir kvar. Ett antal som plötsligt växer mellan säsonger tyder på
att sensorn åldras eller går varmare.

<!-- id: calibration.check.flatlevel -->
### Ljusstyrka i flats

**Vad som kontrolleras.** Medianljusstyrkan i dina flats som andel av kamerans fulla skala
(100 % = det högsta värde en pixel kan hålla), och nivån i varje färgkanal för färgkameror.

**Varför.** En flat måste vara ljus nog för att dess eget brus ska bli litet, men inte så
ljus att sensorn slutar svara jämnt. Nära full skala växer pixlarna inte längre i takt med
ljuset (olinjärt), och då dividerar flatten inte längre bort vinjetteringen korrekt.

**AdvAstro säger:**

| Ljusstyrka | Bedömning |
| --- | --- |
| under 15 % | För mörk: brusiga flats lägger brus på varje ljusbild |
| 15–25 % | Användbar, men inte idealisk |
| 25–75 % | Bra; 30–60 % är det bästa läget |
| över 75 % | För ljus: kan vara olinjär eller klippt |

För färgkameror noteras också när en kanal är mindre än hälften så ljus som den ljusaste.
Det är normalt för många ljuspaneler (ofta svaga i rött eller blått), men håll den mörkaste
kanalen över ungefär 10 %.

**Vad du gör.** Ändra exponeringstiden för dina flats (eller panelens ljusstyrka) tills
nivån ligger runt 40–50 %. Många inspelningsprogram, som NINA och ASIAIR, har en automatisk
flat-guide som gör det åt dig.

<!-- id: calibration.check.clipping -->
### Klippning

**Vad som kontrolleras.** Andelen pixlar i varje flat som når toppen av skalan (98 % av full
skala eller mer).

**Varför.** En klippt pixel har förlorat sin information: den visar inte längre hur mycket
ljus den fick, så flatten kan inte korrigera den punkten.

**AdvAstro flaggar en flat när** mer än 0,01 % av pixlarna är klippta.

**Vad du gör.** Korta exponeringen för dina flats eller dämpa panelen.

<!-- id: calibration.check.vignetting -->
### Vinjettering

**Vad som kontrolleras.** Hur mycket mindre ljus hörnen i flatten får än mitten.

**Varför.** Nästan alla teleskop belyser mitten av sensorn mer än hörnen. Vinjettering är
inget fel: dina flats finns till för att rätta den. Men den visar hur mycket dina flats
måste göra, och kraftig vinjettering (över ungefär 40 %) betyder att hörnen i ljusbilderna
har mindre signal och mer brus även efter korrigeringen.

**AdvAstro redovisar** procentsatsen som information.

**Vad du gör.** Ingenting, om dina flats är bra. Mycket kraftig vinjettering kan bero på ett
för litet filter eller en för liten adapter, eller fel bakfokusavstånd med en
fältutjämnare eller reducerare.

<!-- id: calibration.check.dust -->
### Dammskuggor

**Vad som kontrolleras.** Små runda mörkare fläckar ("munkar") i dina flats, minst 1,5 %
mörkare än omgivningen, och hur djup den djupaste är.

**Varför.** Damm på ett filter eller på sensorns fönster kastar en mjuk rund skugga. Dina
flats rättar den bara om dammet inte flyttat sig mellan ljusbilderna och dina flats. Har
det flyttat sig får du mörka eller ljusa ringar i den staplade bilden.

**AdvAstro redovisar** hur många skuggor det hittade och den djupaste.

**Vad du gör.** Ta dina flats utan att röra kamera, filter eller fokus efter ljusbilderna.
Finns samma munkar i varje session, rengör filtret eller sensorns fönster.

<!-- id: calibration.check.night -->
### Flats från samma natt

**Vad som kontrolleras.** Tiden mellan dina flats och ljusbilderna.

**Varför.** Flats är en ögonblicksbild av hela den optiska kedjan: dammets lägen, kamerans
rotation och fokus. Vrider du kameran, fokuserar om, byter filter eller rengör något
däremellan stämmer dina flats inte längre.

**AdvAstro varnar när** dina flats ligger mer än ett och ett halvt dygn från ljusbilderna.

**Vad du gör.** Ta nya flats varje natt, eller åtminstone varje gång du ändrar något i den
optiska kedjan. Flats från en annan natt fungerar bara om inget rörts däremellan.

<!-- id: calibration.matching -->
## Kontroller mot varandra

De här kontrollerna jämför en typ av bild med en annan. En kalibreringsbild fungerar bara
när den togs på samma sätt som bilderna den ska kalibrera.

<!-- id: calibration.match.darks -->
### Darks mot ljusbilderna

**Vad som kontrolleras.** Exponering, gain, offset, binning och temperatur för dina darks
jämfört med ljusbilderna, och hur gamla dina darks är.

**Varför.** Värmesignal, heta pixlar och amp glow växer alla med exponeringstid och
temperatur, och gain och offset ändrar nivån på allt. En dark drar bara ifrån rätt mängd
när alla dessa är lika. En för stark dark lämnar svarta hål där heta pixlar satt; en för
svag dark lämnar heta pixlar och glöd kvar.

**AdvAstro markerar ett problem när** exponeringen skiljer mer än 1 %, gain, offset eller
binning skiljer över huvud taget, eller temperaturen skiljer mer än 2 °C. Darks som är mer
än ungefär ett halvår äldre än ljusbilderna noteras.

**Vad du gör.** Ta darks med samma inställningar. Med en kyld kamera kan du bygga ett
dark-bibliotek (darks för varje exponering och temperatur du använder) och återanvända det;
förnya det ungefär en gång om året, eftersom sensorer ändras långsamt. Utan kylning, ta
darks samma natt vid samma utetemperatur.

<!-- id: calibration.match.flatdarks -->
### Flat darks mot flats

**Vad som kontrolleras.** Exponering och gain för dina flat darks jämfört med dina flats,
och om det över huvud taget finns något att kalibrera dina flats med.

**Varför.** Flats behöver få sin egen fasta nivå borttagen innan de kan rätta ljusbilderna.
Annars blir korrigeringen för svag och en del av vinjetteringen blir kvar. Flat darks tar
bort den nivån exakt när de matchar dina flats.

**AdvAstro markerar ett problem när** exponeringen skiljer mer än 5 % eller gain skiljer, och
när varken flat darks eller biasbilder finns.

**Vad du gör.** Ta flat darks direkt efter dina flats, med locket på och samma
inställningar. Har du inga fungerar biasbilder oftast i stället.

<!-- id: calibration.match.bias -->
### Biasbilder

**Vad som kontrolleras.** Exponeringstiden för dina biasbilder, och deras gain och offset
mot ljusbilderna.

**Varför.** En biasbild ska bara innehålla kamerans fasta nivå, så den tas med den kortaste
exponering kameran klarar. Gain och offset måste stämma med bilderna den kalibrerar,
eftersom båda ändrar den fasta nivån.

**AdvAstro noterar** biasbilder längre än 0,1 s (de fungerar då som korta darks, vilket går
bra med flats av samma längd) och **varnar** när gain eller offset skiljer från
ljusbilderna.

**Vad du gör.** Ta biasbilder med kamerans kortaste exponering och samma gain och offset som
ljusbilderna.

<!-- id: calibration.match.binning -->
### Binning för flats

**Vad som kontrolleras.** Om dina flats har samma binning som ljusbilderna (till exempel
båda 1×1).

**Varför.** En binnad flat har ett annat pixelrutnät och kan inte divideras in i obinnade
ljusbilder.

**AdvAstro markerar ett problem när** binningen skiljer.

<!-- id: calibration.match.counts -->
### Antal bilder

**Vad som kontrolleras.** Hur många bilder varje uppsättning har, om det inte redan finns en
master.

**Varför.** Varje kalibreringsbild bär på slumpmässigt brus. Medelvärdet av N bilder sänker
bruset till 1/√N av en bild: ungefär 26 % med 15 bilder, 18 % med 30 och 14 % med 50. Det
brus som finns kvar i en master läggs på varje ljusbild.

| Bilder | Minst | Bättre |
| --- | --- | --- |
| Darks | 15 | 30 eller fler |
| Flats | 15 | 30 eller fler |
| Bias | 20 | 50 eller fler |
| Flat darks | 15 | 30 eller fler |

**AdvAstro varnar när** en uppsättning har färre än minimum och ingen master.

**Vad du gör.** Ta fler bilder. Biasbilder och flat darks går fort, så att ta 50 kostar lite.

<!-- id: calibration.match.labels -->
### Etiketter i headern

**Vad som kontrolleras.** Om bildtypen i varje fils header stämmer med mappen den ligger i.

**Varför.** Vissa inspelningsprogram skriver fel typ (ASIAIR märker till exempel flat darks
som "Flat"). Ett staplingsprogram som litar på headern skulle då blanda in flat darks bland
dina flats.

**AdvAstro noterar det när** de inte stämmer. Programmet litar på mappen och datan och säger
det.

**Vad du gör.** Oftast ingenting. Sorterar ditt staplingsprogram efter headern, lägg in
filerna för hand eller rätta typen i headern.

Resultaten används i [arbetsflödet](help:workflow): till exempel hur flats ska kalibreras och
om darks ska optimeras.

<!-- id: calibration.glossary -->
## Ordlista

| Begrepp | Betydelse |
| --- | --- |
| ADU | Analog-digital-enhet: det råa talet en pixel får. En 16-bitarskamera går från 0 till 65 535 |
| Full skala | Det högsta värde en pixel kan hålla; ljusstyrkan i flats anges som andel av den |
| Gain | Hur mycket kameran förstärker signalen innan den görs om till tal |
| Offset | Ett fast tillägg till varje pixel så att inget värde hamnar under noll |
| Utläsningsbrus | Brus som tillkommer varje gång sensorn läses ut, lika för alla exponeringstider |
| Mörkerström | Signal som byggs upp av värme och växer med exponeringstid och temperatur |
| Brus | Den slumpmässiga spridningen av pixelvärden kring sitt medelvärde, angiven i ADU |
| Master | Många kalibreringsbilder av en typ medelvärdesbildade till en renare bild |
| Binning | Att slå ihop 2×2 (eller fler) pixlar till en, i kameran |
| Dithering | Att flytta teleskopet en aning mellan ljusbilderna så att defekter hamnar på olika pixlar |
| Kosmetisk korrigering | Att ersätta kända heta och kalla pixlar med grannarnas värde |
