<!-- id: workflow -->
# The processing workflow

The **Workflow** tab is a complete processing recipe for your session, for **PixInsight** or
**Siril** (switch with the buttons at the top). **Copy** puts it on the clipboard as text;
*Export › Workflow as Markdown* saves it.

<!-- id: workflow.read -->
## How to read it

- **Insights** at the top: the most important things about this session, such as "more
  integration time will help most", "check your calibration frames" or "star-rich Milky Way
  field".
- **Steps**, grouped into stages: *Prepare*, *Calibrate*, *Stack*, *Linear processing*,
  *Stretch*, *Non-linear processing* and *Finish*.
- Each step names the **process** (PixInsight) or tool (Siril), **where to find it** in the
  menus, the **settings** with your numbers, and **why**.
- The coloured dot shows how sure AdvAstro is: *high*, *medium* or *low* confidence.

<!-- id: workflow.adapts -->
## What it adapts to

- **The target**: galaxies, emission nebulae, planetary nebulae, star clusters and
  globular clusters each get their own steps (for example HDR for bright galaxy cores, no
  star removal for clusters).
- **Your data**: sampling (drizzle or not), dithering, number of subs (rejection method),
  colour or mono camera, dual-band filters (Hα/OIII extraction), gradients, calibration.
- **Your software and add-ons** (*Settings › Your software*): BlurXTerminator,
  NoiseXTerminator, StarXTerminator, GraXpert and StarNet are used when you have them.
- **Your skill level** (*Settings › Style*): *Beginner* and *Intermediate* show menu paths
  and reasons; *Advanced* gives a compact list.
- **Your colour style**: natural colour, HOO or SHO.

AdvAstro gives advice; your eyes have the final word. Treat the settings as a well-founded
starting point.
