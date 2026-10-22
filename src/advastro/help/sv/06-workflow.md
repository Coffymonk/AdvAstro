<!-- id: workflow -->
# Bearbetningsflödet

Fliken **Arbetsflöde** är ett komplett bearbetningsrecept för din session, för **PixInsight**
eller **Siril** (växla med knapparna överst). **Kopiera** lägger det i urklipp som text;
*Exportera › Arbetsflöde som Markdown* sparar det.

<!-- id: workflow.read -->
## Så läser du det

- **Insikter** överst: det viktigaste om sessionen, till exempel "mer integrationstid hjälper
  mest", "kontrollera kalibreringsbilderna" eller "stjärnrikt Vintergatsfält".
- **Steg**, grupperade i faser: *Förbered*, *Kalibrera*, *Stapla*, *Linjär bearbetning*,
  *Sträckning*, *Icke-linjär bearbetning* och *Slutför*.
- Varje steg anger **processen** (PixInsight) eller verktyget (Siril), **var den finns** i
  menyerna, **inställningarna** med dina siffror, och **varför**.
- Den färgade pricken visar hur säker AdvAstro är: *säker*, *trolig* eller *osäker*.

<!-- id: workflow.adapts -->
## Vad det anpassar sig efter

- **Objektet**: galaxer, emissionsnebulosor, planetariska nebulosor, öppna hopar och klotformiga
  hopar får egna steg (till exempel HDR för ljusa galaxkärnor, ingen stjärnborttagning för
  hopar).
- **Dina data**: sampling (drizzle eller inte), dithring, antal delbilder (rejektionsmetod),
  färg- eller monokamera, dual-band-filter (separering av Hα/OIII), gradienter, kalibrering.
- **Dina program och tillägg** (*Inställningar › Din programvara*): BlurXTerminator,
  NoiseXTerminator, StarXTerminator, GraXpert och StarNet används när du har dem.
- **Din nivå** (*Inställningar › Stil*): *Nybörjare* och *Medel* visar menyvägar och skäl;
  *Avancerad* ger en kompakt lista.
- **Din färgstil**: naturliga färger, HOO eller SHO.

AdvAstro ger råd; dina ögon har sista ordet. Se inställningarna som en välgrundad
utgångspunkt.
