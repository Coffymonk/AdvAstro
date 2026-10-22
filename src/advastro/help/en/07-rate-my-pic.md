<!-- id: rate -->
# Rate my pic

**Rate my pic** judges a *finished* picture, the way an experienced astrophotographer or a
competition judge would, and tells you exactly how to make it better. It is the third tab
under the toolbar (Ctrl+3, or Ctrl+R). Switching between Session, Calibration and Rate my
pic keeps what each has loaded.

Open or drop a picture: FITS, XISF, TIFF (8, 16 or 32-bit), PNG, JPEG, WebP or BMP. JPEG, PNG
and TIFF files dropped anywhere in the window go straight to Rate my pic. A file that is still
linear (not stretched) is recognised and judged on an automatic stretch.

<!-- id: rate.window -->
## The page

- **Toolbar** (in this mode): *Open picture*, *Analyze again*, *Sky checks*, an **Object**
  field and *Export*. Type the object's name (for example *M31* or *NGC 7000*) to help plate
  solving and comparisons; it fills in by itself when the picture is identified.
- **Above the picture**: what kind of picture it is, **Object** and **Stars**
  ([object type and starless pictures](help:rate.kind)), and a line saying what it was
  judged as.
- **Left**: the picture, with overlay buttons that show the findings on it.
- **Right**: the tabs *Verdict*, *Findings*, *Improve*, *Workflow*, *Compare* and *Details*.

<!-- id: rate.kind -->
## Object type and starless pictures

A galaxy, a nebula that fills the frame, a star cluster and a Milky Way field should not be
judged the same way. Rate my pic works out what the picture shows and adapts the verdict,
the findings, the plan and the workflow.

**Object** is detected, in this order, from the plate solve (sky checks), the name in the
Object field, or the object name in the file. Choose it yourself in the list when it is
wrong or not found; the picture is then judged again at once, without measuring again.

| Object type | What changes |
| --- | --- |
| Galaxy | Background, noise and detail weigh more. Colours may be subtle (muted only below 8 %). The frame-wide contrast check is skipped: a small galaxy says little about it |
| Emission, reflection, dark nebula | A nebula that fills the frame (from its size, or most of the frame being bright) makes "gradient" and "low contrast" milder: part of what looks like a gradient is the nebula. Emission nebulae may be more saturated |
| Planetary nebula | Small object: the frame-wide contrast check is skipped |
| Open or globular cluster | The stars are the subject: stars weigh most, colourless stars can be a major finding, and "stars crowd the object", contrast, saturation and detail checks are skipped |
| Milky Way / wide field | Lots of stars is expected ("stars crowd the object" is skipped); brightness changes across the field are a note, since the Milky Way itself is one |

**Stars** tells whether the picture is **starless** (made with StarNet or StarXTerminator).
*Automatic* recognises it: real star fields have dozens to hundreds of small, round, bright
stars per megapixel, while what star removal leaves is large or faint. A starless picture
skips every star check and the Gaia checks, and the *Stars* category is left out of the
score. Background, colour, tonality and detail are judged as usual.

<!-- id: rate.verdict -->
## The verdict

At the top: the overall **verdict**, a **score out of 100**, and one line of explanation.

| Verdict | Meaning |
| --- | --- |
| **Excellent** | Ready for AstroBin, competitions and print |
| **Ready to share** | A solid image with only small things to polish |
| **Good, with fixable issues** | A few targeted changes will lift it a level |
| **Needs work** | The issues are visible to most viewers |

How strict the verdict is depends on your level in [Settings › Style](help:settings.style):

| Level | Excellent from | Ready from | Fixable from |
| --- | --- | --- | --- |
| Beginner | 86 | 68 | 52 |
| Intermediate | 90 | 77 | 60 |
| Advanced | 93 | 84 | 70 |

Some things cap the verdict whatever the score: any **major** finding (something most
viewers notice) keeps it at *Good, with fixable issues* at best; three major findings, or
a critical one such as an unstretched image, mean *Needs work*; four or more minor findings
keep it at *Ready to share* at best.

<!-- id: rate.categories -->
## Categories

Each category starts at 100 and loses points per finding (major 18, minor 8, critical 45).

| Category | What it covers |
| --- | --- |
| **Stars** | Size, roundness across the field, rings, cores and fringes |
| **Background** | Sky level, gradients, noise, mottle and hot pixels |
| **Colour** | Background neutrality, saturation and star colours |
| **Detail** | Fine structure, over-smoothing and compression |
| **Tonality** | Stretch, contrast, clipping and banding |
| **Presentation** | Edges, size and framing |
| **Depth** | How faint the image goes, measured against Gaia (after sky checks) |

The overall score is a weighted average (stars 22 %, background 20 %, colour 15 %, tonality
15 %, detail 14 %, presentation 8 %, depth 6 %; the weights shift with the
[object type](help:rate.kind), for example stars weigh 36 % for an open cluster and detail
19 % for a galaxy), minus 4 points per major and 1 per minor
finding, because problems a viewer notices affect the whole picture. Words: *Excellent*
from 90, *Good* from 75, *Fair* from 55, otherwise *Weak*.

<!-- id: rate.overlays -->
## Overlays

The buttons above the picture draw the measurements on it:

- **Stars**: a short line on each measured star shows its elongation and direction (longer
  means more elongated; green is small, red is large). The picture is divided into nine
  regions, each labelled with its star size and elongation, so coma, tilt and trailing are
  easy to see.
- **Background**: the smooth background model. Blue is darkest, red brightest. A one-sided
  ramp is a gradient; patches that follow the object are real nebulosity.
- **Noise**: noise per region, blue cleanest, red noisiest.
- **Colour**: the background's colour, strongly exaggerated; grey means neutral.
- **Clipping**: red where pixels are clipped to white, blue where clipped to black.
- **Problems**: dark rings around stars (yellow circles), hot pixels (red circles) and
  uncropped edges (red bands).

The *Show* link on a finding switches to the overlay that shows it.

<!-- id: rate.findings -->
## Findings

The *Findings* tab lists every finding, most important first, with its severity (*Critical*,
*Major*, *Minor* or *Note*), its category and what was measured. Below them, *What works*
lists what is already good. The **?** on a finding opens its explanation in the
[finding reference](help:rate.reference).

<!-- id: rate.improve -->
## How to improve the image

The *Improve* tab turns the findings into a plan, ordered by impact: **Fix first** (major
problems), **Then** (minor ones) and **Polish** (notes). Each step says why, using the values
measured in your picture, and gives concrete steps for PixInsight or Siril (switch at the top).

When you own BlurXTerminator, NoiseXTerminator or StarXTerminator
([Settings › Your software](help:settings.software)), the steps use them. **Next time at the
telescope** collects what to change during capture. *Copy* puts the plan on the clipboard.

Many steps work **through a mask**, so that an effect reaches only part of the picture. Under
such a step, **How to make the mask** opens a step-by-step recipe for your program:

| Mask | Effect on | Typical use |
| --- | --- | --- |
| Luminance | The bright parts | Sharpening, saturation, contrast on the object |
| Inverted luminance | The dark parts | Noise reduction in the sky |
| Star | The stars | Shrinking or recolouring stars |
| Range | The object, with a soft edge | Local contrast, saturation on a galaxy |
| Corner | One corner | Repairing stars or a gradient in one corner |

Siril applies its tools to the whole image, so its recipes make the change on a copy and
blend it back with PixelMath, using the picture's own brightness as the weight.

<!-- id: rate.workflow -->
## Workflow for your target

The *Workflow* tab is a complete processing route for the object type, from the stacked,
linear master to the finished picture, for PixInsight or Siril (switch at the top):
cropping, background extraction, colour calibration, deconvolution, noise reduction, star
separation, stretching, local contrast, colour, stars and export.

Every stage explains in plain words what it does and why, gives the steps, and adds what to
watch for with this kind of object (for example: no background samples near a galaxy's
halo; stretch a cluster's stars with ArcsinhStretch). Stages marked **Your image** address
something Rate my pic found in your picture. Stages that do not apply are left out: a
cluster keeps its stars; a starless picture has no star stages. *Copy* puts the workflow on
the clipboard, and *Export › Workflow as Markdown* saves it.

<!-- id: rate.sky -->
## Sky checks

After the rating, AdvAstro plate solves the picture: from the solution saved in the file
(PixInsight and Siril save one after their own solving) or with ASTAP. Without a hint ASTAP
searches the whole sky with an automatic field size, which can take a minute; typing the
object's name speeds it up a lot. Then it:

- **Identifies the target** and judges the framing.
- **Measures the depth**: every star in the picture is matched with the Gaia DR3 catalogue.
  The *limiting magnitude* is the brightness at which half of the catalogue stars are
  visible in your picture. A chart shows the share detected per magnitude.
- **Checks star colours**: each star's colour in your picture is compared with its true Gaia
  colour (BP−RP). A correlation near 1 means correct colour calibration; low values are
  expected for narrowband or dual-band images.
- **Fetches a survey image**: the same field from Pan-STARRS (small fields), DSS2 (most
  fields) or the Mellinger all-sky survey (wide fields), on the same pixel grid as your
  picture.

Sky checks run automatically (turn off in [Settings › Compare](help:settings.compare)) or with
*Sky checks* in the toolbar. They need an internet connection; Gaia results are kept on your
computer, so a second check of the same field is fast.

<!-- id: rate.compare -->
## Comparing

The *Compare* tab has two parts.

**Survey image.** Use the slider to fade between your picture and the survey, or *Blink* to
switch back and forth. Missing faint structure, artefacts, and detail that is not really
there (for example from aggressive AI sharpening) stand out at once. The survey is a
reference, not a beauty contest: professional surveys are deep but often coarse.

**Other photographers.** To see how others captured the same object:

- With an **AstroBin API key** ([Settings › Compare](help:settings.compare)): *Load from
  AstroBin* shows the most liked AstroBin images of the object, with the photographer's name.
  Click one to open it on AstroBin. Request a free key at
  <https://www.astrobin.com/api/request-key/>.
- Without a key, with **Open search pages in the browser** on: buttons open AstroBin,
  Wikimedia Commons and APOD searches for the object.
- With neither, no comparison is made.

Comparisons need the object's name: from sky checks, the file, or the Object field.

<!-- id: rate.details -->
## Details and reports

*Details* lists every measurement. **Export** saves the full report as **PDF** (with the
picture and the survey image), **Markdown** (ready to paste in a forum post) or **JSON**.

<!-- id: rate.limits -->
## Good to know

- Measurements are made on what you see: the stretched picture, in brightness from 0 to
  100 %. Very large pictures (over about 6200 pixels) are measured at half size.
- AdvAstro is strict on technical faults, which can be measured, and gentle on taste:
  "strong saturation" is a remark, not a rule.
- All texts, including findings, tips and workflows, follow your language (English or Swedish).

<!-- id: rate.reference -->
## Finding reference

Every finding Rate my pic can report, what it means and the limits used. Values are
fractions of full brightness (0–100 %).

### Tonality

<!-- id: finding.linear -->
#### The image has not been stretched yet
The data is still linear: faint signal is there but not visible. Critical. Everything else is
judged on an automatic stretch. Stretch it (GeneralizedHyperbolicStretch, or
HistogramTransformation) after background extraction and colour calibration.

<!-- id: finding.shadow_clip -->
#### Clipped shadows
More than 1 % of the pixels (major above 5 %) have a colour channel at zero. The black point
is too high, or one channel was not neutralised before stretching.

<!-- id: finding.clipped_highlights -->
#### Burned-out highlights
Large areas outside star cores are pure white (minor above 0.02 % of the frame, major above
0.15 %). Typical for bright galaxy cores and M42; stretch with highlight protection or use
HDRMultiscaleTransform.

<!-- id: finding.low_contrast -->
#### Low contrast / object could be brighter
The brightest parts of the object rise less than 13 % above the background (major below
7 %). There is room for a further gentle stretch and local contrast.

<!-- id: finding.banding -->
#### Histogram gaps (banding)
More than 20 % of the levels in the used range are empty (major above 45 %): the image was
stretched again after being saved with 8 bits per channel. Smooth gradients turn into steps.
Process in 32-bit and export to 8-bit only at the end.

<!-- id: finding.banding_risk -->
#### Risk of visible banding
In an 8-bit file, more than 40 % of the sky consists of flat single-level patches: so smooth
that contour lines may show on some screens. Export 16-bit, or keep a little fine grain.

### Background

<!-- id: finding.crushed_black -->
#### Crushed black background
The sky is under 2.5 % brightness with more than 2 % of the pixels clipped to black. Faint
stars and faint nebulosity are cut away.

<!-- id: finding.dark_background -->
#### Dark / very dark background
The sky sits under 6 % (a note) or under 4 % (minor). Dramatic on a bright screen, but faint
detail disappears. AdvAstro's comfortable range is 6–20 %; many experienced imagers aim for
about 8–12 %.

<!-- id: finding.bright_background -->
#### Background a bit bright / washed out
The sky is above 20 % (minor) or 28 % (major). It looks grey and hazy, and contrast suffers.

<!-- id: finding.gradient -->
#### Uneven background (gradient)
The smooth background model changes by more than 5 % across the frame, or a one-sided ramp
of more than 3 % (a note or minor); above 9 %, or 6 % one-sided, it is flagged more
strongly. In frames full of nebulosity the severity is lowered, because real structure
looks like a gradient. Check with the *Background* overlay.

<!-- id: finding.color_gradient -->
#### Colour gradient
The sky changes colour across the frame by more than 4 % between channels (major above
7 %): light pollution or moonlight that is not neutral.

<!-- id: finding.noise -->
#### Visible grain / grainy background
Pixel-to-pixel noise in the darkest sky is above 0.65 % (minor) or 1.2 % (major).

<!-- id: finding.color_noise -->
#### Colour noise
The grain is coloured (chroma noise above 0.8 %, and at least 80 % of the brightness noise;
major above 1.6 %). The easiest noise to remove without losing detail.

<!-- id: finding.mottle -->
#### Blotchy background (mottle)
Blotches a few pixels across, above 0.26 % amplitude (major above 0.45 %) and strong
compared with the fine grain. Mottle is noise at a larger scale than the grain: fine-grain
noise reduction (NoiseXTerminator included) leaves it, and strong smoothing makes it worse.
Causes: too little integration time, too little dithering, and background extraction with
too many samples. The plan treats the larger scales only (MultiscaleLinearTransform layers
3–5, or Siril's wavelets) through an inverted luminance mask, and keeps the fine grain.

<!-- id: finding.walking_noise -->
#### Possible walking noise
The background noise has a clear direction (streaks). Caused by slow drift without
dithering. Reported as "possible" because strong diagonal nebulosity can look similar.

<!-- id: finding.hot_pixels -->
#### Hot pixels left
More than 30 isolated bright pixels, and more than 3 per megapixel (major above 25 per
megapixel). A pixel counts only when it is far above its surroundings and its neighbours
are not lifted at all: even a very sharp star spreads some light into the pixels around it.
Click *Show* to check the marked pixels; if they are tiny stars rather than single dots,
ignore the finding.

### Colour

<!-- id: finding.green_cast -->
#### Green tint in the sky
The background is greener than neutral by more than 0.5 % (or 6 % of the sky level).
Remove with SCNR.

<!-- id: finding.color_cast -->
#### Tinted background
One colour dominates the sky by more than 1.2 % of full scale or 16 % of the sky level
(major above 2.5 % or 32 %). The finding names the tint.

<!-- id: finding.muted -->
#### Muted / almost colourless
Median saturation of the object is under 22 % (minor) or 12 % (major). For a galaxy, whose
colours are subtle, under 8 % (minor) or 5 % (major). Not checked for star clusters.

<!-- id: finding.oversaturated -->
#### Strong / oversaturated colours
Median saturation above 72 % or more than 10 % of the object near full saturation (minor);
above 85 % or 30 % (major). A matter of taste up to a point; beyond it, subtle variations
are lost.

<!-- id: finding.channel_clip -->
#### Clipped colour channel
More than 1 % of the bright areas have one channel at its limit: colour detail is lost and
the hue shifts.

<!-- id: finding.star_color -->
#### Colourless stars
The spread of star colours is very small: real stars range from blue-white to orange.

<!-- id: finding.magenta_stars -->
#### Magenta stars
More than 60 % of the stars are magenta: typical of narrowband and dual-band data.

<!-- id: finding.color_calibration -->
#### Star colours against Gaia
After sky checks: picture star colours compared with their Gaia colours. A correlation of
0.6 or more is good; 0.3–0.6 is a minor finding; lower means the colour calibration needs
another look (expected with narrowband or dual-band data).

### Stars

<!-- id: finding.trailed_stars -->
#### Elongated stars
Median elongation above 0.3 with stars pointing the same way (major above 0.4): tracking,
guiding, balance, wind or polar alignment.

<!-- id: finding.corner_elongation -->
#### Stretched stars in one corner
One corner's stars are elongated above 0.3, at least 0.15 more than the centre and 0.1 more
than the other corners (major above 0.45). Causes: tilt, a flattener or reducer at the wrong
distance with the optical axis off-centre, collimation, a pinched or shifted optical element,
or rotated subs in the stack. The plan explains how to tell them apart on a single sub
(AberrationInspector) and how to repair this picture.

<!-- id: finding.stars_soft -->
#### Stars on the large side / large, soft stars
Typical stars are wider than 4.6 pixels at half brightness (major above 6.5). Focus,
seeing, or a strong stretch. 3.6 pixels or less counts as tight.

<!-- id: finding.big_stars -->
#### Bright stars dominate
The brightest stars' cores are wider than 1.2 % of the picture diagonal (major above 2 %).

<!-- id: finding.star_dominance -->
#### Stars crowd the object
Stars cover more than 22 % of a dense star field. Star reduction lets the object lead.

<!-- id: finding.corner_stars -->
#### Softer stars in the corners
Corner stars are more than 20 % larger than in the centre (major above 40 %). Elongated
towards or away from the centre means coma (back focus); along circles means astigmatism
or field curvature.

<!-- id: finding.tilt -->
#### Uneven sharpness between the corners
The sharpest and softest corners differ by more than 30 % (major above 50 %). Sensor tilt is
only one possible cause. Others: back focus slightly off with the optical axis off-centre;
collimation; pinched or shifted optics; flexure; and the stack itself (subs rotated after a
meridian flip or between nights, or an off-centre crop). Check one single sub: if it is even,
the stack or the crop causes it. Rotating the camera 90° tells camera-side causes (they move
with it) from telescope-side ones (they stay).

<!-- id: finding.star_rings -->
#### Dark rings around stars
More than 10 % of the bright stars (major above 25 %) have a dark ring: over-sharpening or
too many deconvolution iterations.

<!-- id: finding.white_cores -->
#### White star cores
More than 60 % of the bright stars have clipped white cores, so their colour is lost.

<!-- id: finding.fringe -->
#### Coloured star rims
Stars are more than 0.7 pixels larger in blue than red (or the reverse), or red and blue
are offset by more than 1.2 pixels towards the edges: chromatic aberration or channel
misalignment.

<!-- id: finding.few_stars -->
#### Few stars to measure
Fewer than 15 stars were found, but the picture was set to *With stars*. Star checks are
skipped.

<!-- id: finding.starless -->
#### Judged as a starless image
The picture is starless (detected, or chosen under **Stars**). Star checks and the Gaia
checks are skipped and the *Stars* category is left out of the score; everything else is
judged as usual. See [object type and starless pictures](help:rate.kind).

### Detail

<!-- id: finding.low_detail -->
#### Little fine detail
Fine structure in the object rises less than 1.6 times above the noise.

<!-- id: finding.plastic -->
#### Background looks over-smoothed
Almost no grain at all (under 0.06 %) in a 16- or 32-bit file: noise reduction has gone so
far that the sky can look plastic, and faint detail goes with the noise.

<!-- id: finding.jpeg -->
#### JPEG compression
Estimated JPEG quality under 85 or visible 8×8 block edges (major under 70). Export with
quality 92–95 from a 16- or 32-bit master.

### Presentation

<!-- id: finding.edges -->
#### Stacking edges not cropped
Dark, bright or noisy strips along an edge where not all subs overlapped. Major.

<!-- id: finding.small_image -->
#### Small image
Under one megapixel. Share at least 3000 pixels on the long side.

<!-- id: finding.eight_bit -->
#### 8-bit file
Fine for sharing; keep a 16- or 32-bit master for printing and reprocessing.

<!-- id: finding.off_centre -->
#### Subject sits off-centre
Most of the light is towards one side. Deliberate placement can work well; this is a note.

<!-- id: finding.framing -->
#### Framing
After sky checks: how much of the frame the identified object fills.

### Depth

<!-- id: finding.depth -->
#### Depth
After sky checks: the limiting magnitude against Gaia. For fields narrower than 3°, magnitude
18 or deeper counts as deep and 16–18 as typical; for wider fields 15.5 and 13.5–15.5.
