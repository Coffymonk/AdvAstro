<!-- id: calibration -->
# Kalibreringsbilder

AdvAstro kontrollerar bias, darks, flats och flat darks som ligger bredvid ljusbilderna, var
för sig och mot ljusbilderna. Stäng av det under
[Inställningar › Bildurval](help:settings.selection) om du vill.

Varje typ får en egen flik ovanför tabellen, och fliken Session listar alla kontroller.
Klicka på en flaggad fil i listan för att markera den i tabellen. Avvikande bilder bockas
av i det föreslagna urvalet, precis som delbilder.

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

En ★ framför ett namn betyder en masterbild.

<!-- id: calibration.checks -->
## Vad som kontrolleras

**Darks, bias och flat darks**

- **Nivån genom serien**: darks ska vara lika mörka. En nivå som stiger genom serien betyder
  att ljus nått sensorn: ett ljusläckage, eller darks tagna i dagsljus.
- **Amp glow**: en ljus kant eller ett ljust hörn; darks tar bara bort det när de matchar
  ljusbilderna.
- **Rander**: rad- eller kolumnmönster; fler bilder ger en jämnare master.
- **Heta pixlar**: hur många de är vid den här exponeringen och temperaturen.

**Flats**

- **Ljusstyrka**: sikta på 25–75 % av full skala. Under 15 % är för mörkt (brusiga flats);
  över 75 % riskerar klippning. Den mörkaste färgkanalen bör ligga över ungefär 10 %.
- **Klippning**, **vinjettering** och **dammskuggor**.
- **Samma natt**: flats från en annan natt matchar inte längre damm och kamerans rotation.

**Mot varandra**

- **Darks mot ljusbilder**: exponering, gain, offset, binning och temperatur (inom 2 °C) ska
  stämma. Darks äldre än ungefär ett halvår noteras; ett bibliotek fungerar, men förnya det
  ungefär en gång om året.
- **Flat darks mot flats**: samma exponering och gain.
- **Bias**: ska vara kortast möjliga exponering.
- **Antal bilder**: minst 15 darks, 15 flats, 20 bias och 15 flat darks; 30 eller fler (50
  för bias) ger en master med mindre brus.
- **Etiketter**: när headern säger en sak och mappen en annan (till exempel flat darks
  märkta "Flat") litar AdvAstro på mappen och talar om det.

Resultaten används i [arbetsflödet](help:workflow): till exempel hur flats ska kalibreras och
om darks ska optimeras.
