<!-- id: reference -->
# Referens

<!-- id: reference.shortcuts -->
## Kortkommandon

| Tangenter | Funktion |
| --- | --- |
| Ctrl+O | Öppna en sessionsmapp (huvudfönstret) eller en bild (Betygsätt min bild) |
| F5 | Analysera igen |
| Esc | Stoppa en pågående analys |
| Mellanslag / K / R | Växla / behåll / ta bort markerade delbilder |
| Ctrl+R | Betygsätt min bild |
| Ctrl+, | Inställningar |
| Ctrl+N | Nattläge |
| F1 | Hjälp för det du tittar på |
| Mushjul, dra, dubbelklick | Zooma, panorera, anpassa / 100 % i förhandsvisningen |

<!-- id: reference.glossary -->
## Ordlista

**ADU**: kamerans råa pixelvärde. **Delbild**: en enskild exponering (ljusbild).
**FWHM**: stjärnans diameter vid halva toppljusstyrkan. **Excentricitet / utdragning**: 0 är
en rund stjärna; högre är mer utdragen. **σ (sigma)**: ett mått på spridning; AdvAstro
använder en robust variant som bortser från avvikare. **Linjär / sträckt**: data direkt från
staplingen är linjära och ser nästan svarta ut; sträckning gör de svaga delarna ljusare.
**Plattlösning**: att ta reda på exakt var på himlen en bild pekar genom att matcha dess
stjärnor mot en katalog. **Gränsmagnitud**: den svagaste stjärnljusstyrka en bild visar
(större tal är svagare). **Dithring**: att flytta teleskopet några pixlar mellan delbilderna.
**Drizzle**: en staplingsmetod som återvinner upplösning ur undersamplade, dithrade data.
**Gradient**: ojämn bakgrundsljusstyrka från ljusförorening, månljus eller ofullständiga
flats. **Fläckighet**: fläckigt bakgrundsbrus. **SCNR**: tar bort en färgton, oftast grön.
**OSC**: one-shot-colour-kamera (färgkamera). **Hα, OIII**: emissionslinjer från väte (rött)
och syre (turkos) som smalbands- och dual-band-filter släpper igenom.

<!-- id: reference.faq -->
## Felsökning och frågor

**AdvAstro hittar inte ASTAP.** Öppna *Inställningar › Plattlösning* och peka på
ASTAP-programmet eller dess mapp. Kontrollera att en stjärndatabas (D05, D20, D50 …) är
installerad.

**Plattlösningen misslyckas.** Kontrollera brännvidd och pixelstorlek, installera en databas
som passar ditt fält (D50 för de flesta), höj sökradien eller tidsgränsen. I Betygsätt min
bild: skriv objektets namn i fältet Objekt.

**Himmelskontroller eller jämförelser kan inte ansluta.** De kräver internet (Gaia och
kartbilder kommer från CDS i Strasbourg; AstroBin från astrobin.com). Kontrollera
anslutningen eller en brandvägg. Allt annat fungerar utan nät.

**AstroBin ger inga resultat.** Kontrollera nyckel och hemlighet under *Inställningar ›
Jämför*, och prova objektets katalognamn (till exempel *NGC 7000* hellre än ett smeknamn).

**Många bra delbilder flaggas.** Välj *Mild* under *Inställningar › Bildurval*. Tänk på att
flaggorna jämför delbilder inom sessionen: i en mycket jämn session sticker små skillnader
ut.

**Stjärnstorlekar visas bara i pixlar.** AdvAstro behöver brännvidd och pixelstorlek, från
headers, *Inställningar › Utrustning* eller en `.mksession`-fil.

**Windows eller macOS vägrar starta programmet.** Paketen är ännu inte kodsignerade; se
[Installation](help:start.install).

**Ändrar AdvAstro mina filer?** Nej. Det läser dem bara. Plattlösning görs på en tillfällig
kopia, och rapporter sparas bara där du väljer.

**Var finns mina inställningar?** Se [Inställningar](help:settings).

**Hur rapporterar jag ett problem eller kommer med förslag?** Via GitHub-sidan eller
<https://miklosoft.se/main>. Ange versionen (Hjälp › Om) och gärna JSON-rapporten.
