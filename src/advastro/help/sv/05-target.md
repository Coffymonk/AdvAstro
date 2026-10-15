<!-- id: target -->
# Objekt och plattlösning

Fliken **Objekt** visar vad du fotograferat: namn och typ, en skiss av hur det passar i
fältet, synfält, bildskala, centrum, rotation, galaktisk latitud och andra katalogiserade
objekt i bilden.

<!-- id: target.sources -->
## Var positionen kommer ifrån

AdvAstro använder den bästa källan som finns, i den här ordningen:

| Källa | Vad du får |
| --- | --- |
| Plattlösning i filerna (ASIAIR, NINA, PixInsight …) | Exakt objekt, komposition, objekt i fältet |
| Plattlösning med ASTAP | Samma sak, efter några sekunder |
| Teleskopets pekriktning i headern | Troligt objekt och ungefärlig komposition |
| Objektets namn (header, filnamn, sessionsfil) | Objektet, ingen komposition |
| Ingenting | Ett allmänt arbetsflöde, och hur du får ett bättre |

Objektkatalogen är OpenNGC: omkring 12 000 galaxer, nebulosor och stjärnhopar, med
Messiernummer och vardagsnamn.

<!-- id: target.solve -->
## Plattlösning med ASTAP

När filerna saknar lösning och ASTAP är installerat löser AdvAstro den bästa delbilden
automatiskt (stäng av under [Inställningar › Plattlösning](help:settings.solver)), eller när
du klickar **Lös**. Se [Ställa in plattlösning](help:start.astap) för hur du installerar ASTAP.

Om lösningen misslyckas: kontrollera att en stjärndatabas är installerad, att brännvidd och
pixelstorlek stämmer ([Inställningar › Utrustning](help:settings.equipment)), och prova en
större sökradie eller en längre tidsgräns.

<!-- id: target.framing -->
## Komposition

Skissen visar ditt fält som en rektangel och objektets katalogiserade kontur. Texten säger
om objektet fyller bilden, är större än fältet (en mosaik skulle visa hela) eller är litet
(längre brännvidd eller en beskärning skulle visa det bättre). Arbetsflödet använder detta,
till exempel för att välja mellan automatisk och manuell bakgrundsextraktion.
