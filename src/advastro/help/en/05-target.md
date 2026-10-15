<!-- id: target -->
# Target and plate solving

The **Target** tab shows what you imaged: its name and type, a sketch of how it fits your
field, the field of view, image scale, centre, rotation, galactic latitude and other
catalogued objects in the frame.

<!-- id: target.sources -->
## Where the position comes from

AdvAstro uses the best source available, in this order:

| Source | What you get |
| --- | --- |
| Plate solution in the files (ASIAIR, NINA, PixInsight, …) | Exact target, framing, objects in the field |
| ASTAP plate solve | The same, after a few seconds |
| Telescope pointing in the headers | Likely target and approximate framing |
| Object name (header, file name, session file) | The object, no framing |
| Nothing | A general workflow, and how to get a better one |

The object catalogue is OpenNGC: about 12,000 galaxies, nebulae and clusters, with Messier
numbers and common names.

<!-- id: target.solve -->
## Plate solving with ASTAP

When the files carry no solution and ASTAP is installed, AdvAstro solves the best sub
automatically (turn this off in [Settings › Plate solving](help:settings.solver)), or when you
click **Solve**. See [Setting up plate solving](help:start.astap) to install ASTAP.

If solving fails: check that a star database is installed, that the focal length and pixel
size are right ([Settings › Equipment](help:settings.equipment)), and try a larger search
radius or a longer time limit.

<!-- id: target.framing -->
## Framing

The sketch shows your field as a rectangle and the target's catalogued outline. The text says
whether the object fills the frame, is larger than the field (a mosaic would show all of it)
or is small (a longer focal length or a crop would show it better). The workflow uses this,
for example to choose between automatic and manual background extraction.
