<!-- id: cli -->
# Kommandoraden

Kommandot `advastro` gör samma analys utan fönster, för batchkörningar och skript. Kör
`advastro --help` eller `advastro <kommando> --help` för alla alternativ.

<!-- id: cli.analyze -->
## advastro analyze

```
advastro analyze MAPP [alternativ]
```

| Alternativ | Betydelse |
| --- | --- |
| `-f table / json / csv` | Utdataformat (standard: en tabell) |
| `-o FIL` | Skriv rapporten till en fil |
| `-r` | Ta med undermappar |
| `-j N` | Parallella arbetare |
| `--advise` | Identifiera objektet och skriv ut ett bearbetningsflöde |
| `--tool pixinsight / siril` | Program för arbetsflödet |
| `--workflow FIL` | Spara även arbetsflödet som Markdown |
| `--solve` / `--no-solve` | Kör alltid / aldrig ASTAP när filerna saknar lösning |
| `--no-calibration` | Hoppa över kalibreringsbilderna |
| `--session FIL` | En `.mksession`-fil (hittas annars automatiskt) |
| `-q` | Ingen förloppsutskrift |

Exempel:

```
advastro analyze D:\Astro\2026-10-14\LIGHT
advastro analyze ./lights -f csv -o subs.csv
advastro analyze ./lights --advise --tool siril --workflow siril.md
advastro analyze ./session/DARK
```

<!-- id: cli.rate -->
## advastro rate

```
advastro rate BILD [alternativ]
```

| Alternativ | Betydelse |
| --- | --- |
| `-f table / markdown / json` | Utdataformat |
| `-o FIL` | Skriv rapporten till en fil |
| `--pdf FIL` | Skriv även en PDF-rapport (bara i skrivbordspaketet) |
| `--sky` | Plattlös, mät djupet mot Gaia och kontrollera stjärnfärgerna |
| `--object NAMN` | Objektets namn, hjälper plattlösningen |
| `--tool pixinsight / siril` | Visa bara steg för ett program |
| `--skill beginner / intermediate / advanced` | Bedöm på den här nivån |

```
advastro rate final.tif
advastro rate final.jpg --sky --object "NGC 7000" --pdf betyg.pdf
advastro rate final.xisf -f markdown --tool siril -o foruminlagg.md
```

<!-- id: cli.other -->
## Andra kommandon

| Kommando | Gör |
| --- | --- |
| `advastro solve FIL` | Plattlös en bild och namnge vad den visar |
| `advastro astap` | Visa var ASTAP och dess stjärndatabaser hittades |
| `advastro config [MAPP]` | Visa de sammanslagna inställningarna och deras källor |

Alternativ för alla kommandon: `--config FIL`, `--set sektion.nyckel=värde`,
`--no-user-config` och `--lang en/sv`.
