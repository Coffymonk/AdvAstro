<!-- id: settings -->
# Inställningar

Öppna med **Inställningar** i verktygsfältet (Ctrl+,). Ändringarna sparas i din
inställningsfil när du klickar *Spara* och gäller direkt; delbilderna mäts inte om.
Inställningsfilen finns här:

- Windows: `%APPDATA%\AdvAstro\config.toml`
- macOS: `~/Library/Application Support/AdvAstro/config.toml`
- Linux: `~/.config/advastro/config.toml`

<!-- id: settings.general -->
## Allmänt

- **Språk**: English eller Svenska. Gäller när du startar om programmet.
- **Parallella arbetare**: hur många delbilder som mäts samtidigt. Välj i listan:
  *Automatiskt* använder alla processorkärnor (antalet visas); ett lägre antal håller datorn
  lättanvänd under långa analyser.

<!-- id: settings.equipment -->
## Utrustning

**Brännvidd** och **pixelstorlek** används bara när filernas headers saknar dem. De flesta
inspelningsprogram (NINA, ASIAIR, SharpCap) skriver båda. Med dem visar AdvAstro
stjärnstorlekar i bågsekunder, bedömer samplingen och plattlöser snabbare.

<!-- id: settings.selection -->
## Bildurval

Hur mycket en delbild får sticka ut från resten av sessionen innan den föreslås bli
bortvald.

| Strikthet | Stjärnstorlek | Max utdragning | Minst stjärnor | Himmelsljus |
| --- | --- | --- | --- | --- |
| Mild | 4 σ | 0,7 | 45 % | 5 σ |
| Normal | 3 σ | 0,6 | 60 % | 4 σ |
| Sträng | 2 σ | 0,5 | 75 % | 3 σ |

σ är sessionens robusta spridning; antal stjärnor är en andel av sessionens median. Ange
värdena själv för *Anpassad*. **Kontrollera även bias, darks, flats och flat darks** slår på
eller av [kalibreringskontrollerna](help:calibration).

*?* bredvid varje värde öppnar dess förklaring nedan.

<!-- id: settings.selection.fwhm -->
### Gräns för stjärnstorlek (σ över median)

Väljer bort delbilder vars stjärnor är mycket större än sessionens typiska storlek. Stora
stjärnor betyder en oskarp delbild: fokusdrift när temperaturen sjunker, dålig seeing, vind
eller ett guidningshack. Gränsen anges i σ, sessionens egen spridning: med 3 σ flaggas en
delbild när stjärnstorleken ligger tre spridningar över medianen, så att både en stabil och
en ojämn session bedöms rättvist. Lägre är striktare.

<!-- id: settings.selection.ecc -->
### Största utdragning

Väljer bort delbilder med utdragna stjärnor. Värdet är excentriciteten: 0 är helt runt, 0,5
är ungefär 15 % längre än brett (syns precis), 0,6 ungefär 25 % längre (tydligt ovalt) och
0,8 ungefär 70 % längre. Orsaker: vind, guidningsfel,
balans, periodiskt fel, eller en kabel som drar. Till skillnad från de andra gränserna är den
här absolut, inte relativ till sessionen: en session där alla delbilder har utdragna
stjärnor flaggas ändå. Lägre är striktare.

<!-- id: settings.selection.stars -->
### Minst antal stjärnor (andel av median)

Väljer bort delbilder med för få stjärnor jämfört med sessionens typiska antal. Stjärnor
försvinner bakom moln, dis, dagg på optiken, eller när delbilden är kraftigt ur fokus. Med
0,6 flaggas en delbild med färre än 60 % av det vanliga antalet stjärnor. Högre är striktare.

<!-- id: settings.selection.sky -->
### Gräns för himmelsljus (σ över median)

Väljer bort delbilder med mycket ljusare himmel än resten: månen som går upp, moln som lyses
upp av stadsljus, gryning, eller en bils strålkastare. En ljusare himmel ger brus och
gradienter som de andra delbilderna inte har. Gränsen anges i σ av sessionens himmelsnivåer.
Lägre är striktare.

<!-- id: settings.solver -->
## Plattlösning

- **Lös automatiskt** efter analysen när filerna saknar lösning.
- **ASTAP-program** och **Mapp för stjärndatabas**: lämna tomma för att hitta dem
  automatiskt, eller bläddra fram dem. Det räcker att peka på ASTAP-mappen.
- **Sökradie**: hur långt från headerns position ASTAP söker (grader).
- **Tidsgräns**: hur lång tid ASTAP får ta.
- Rutan nedanför visar vad som hittades; *Kontrollera igen* söker på nytt, *Hämta ASTAP*
  öppnar dess webbplats.

<!-- id: settings.software -->
## Din programvara

Kryssa för **programmen du använder** (PixInsight, Siril, GraXpert, StarNet) och **betalda
tillägg du äger** (BlurXTerminator, NoiseXTerminator, StarXTerminator). Arbetsflödet och
förbättringsplanen i Betygsätt min bild skrivs för dem.

<!-- id: settings.style -->
## Stil

- **Färgstil**: naturliga färger, HOO (Hα röd, OIII turkos) eller SHO (Hubble-paletten).
- **Detaljnivå**: *Nybörjare* och *Medel* visar menyvägar och skäl för varje steg;
  *Avancerad* visar en kompakt lista. Den styr också hur strikt
  [omdömet i Betygsätt min bild](help:rate.verdict) är.

<!-- id: settings.compare -->
## Jämför

Inställningar för Betygsätt min bilds kontroller mot himlen och jämförelser med andra
fotografer.

- **Kör himmelskontroller automatiskt** efter betygsättningen: plattlösning, Gaia-djup och
  färg.
- **Jämför med en bild från en himmelskartläggning** (DSS2, Pan-STARRS).
- **AstroBin API-nyckel** och **API-hemlighet**: valfria. Med dem visas de mest gillade
  AstroBin-bilderna av objektet i AdvAstro. Begär en gratis nyckel via länken på sidan.
  Nyckeln sparas i din inställningsfil.
- **Utan AstroBin-nyckel: öppna söksidor i webbläsaren**. Utan nyckel och med det här
  avstängt görs ingen jämförelse.

<!-- id: settings.files -->
## Inställningsfiler för avancerad användning

Inställningarna är vanliga TOML-textfiler som läggs i lager (sista vinner):

1. inbyggda standardvärden,
2. din inställningsfil (ovan),
3. `advastro.toml` i sessionsmappen (inställningar för en session),
4. filer som anges med `--config` på kommandoraden,
5. `--set sektion.nyckel=värde` på kommandoraden.

Okända nycklar eller fel typ av värde ger en varning som nämner filen, och ignoreras.
`advastro config` visar de sammanslagna inställningarna och varifrån varje värde kommer.
