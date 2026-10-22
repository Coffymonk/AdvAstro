<!-- id: calibration -->
# Calibration frames

AdvAstro checks bias, dark, flat and flat-dark frames found next to your lights, on their
own and against the lights. Turn this off in
[Settings › Sub selection](help:settings.selection) if you want.

The calibration frames have their own mode: the **Calibration** tab under the toolbar
(Ctrl+2). Each type gets its own tab above the table, and the *Checks* tab on the right lists
every check. Click a flagged file in the list to select it in the table. Odd frames are
unticked in the suggested selection, just like subs. **Double-click a frame** to see
[everything about it](help:calibration.details).

New to calibration frames? Start with [why they are needed](help:calibration.why). Each
check below says what is measured, why it matters, when AdvAstro warns and what to do.

<!-- id: calibration.why -->
## Why calibration frames?

Every light frame contains more than the sky. The camera adds a fixed electronic level, heat
signal, hot pixels and glow, and the telescope adds uneven illumination and dust shadows.
Calibration frames record each of these on their own, so your stacking program can subtract
or divide them out of every light.

| Frame | What it records | What it removes from the lights | How to take it |
| --- | --- | --- | --- |
| Bias | The camera's fixed starting level and read pattern | The offset and fixed pattern | Shortest exposure, cap on, same gain and offset as the lights |
| Dark | Heat signal (dark current), hot pixels and amp glow | Hot pixels, glow and the heat signal | Same exposure, gain, offset and temperature as the lights, cap on |
| Flat | How evenly light reaches each pixel | Vignetting (dark corners) and dust shadows | An evenly lit target (panel or dawn sky), same focus and rotation as the lights |
| Flat dark | The bias and heat signal of a flat | The level that would otherwise skew the flats | Same exposure and gain as the flats, cap on |

You need either flat darks or bias frames to calibrate flats. Many cameras with low dark
current can use bias frames instead of flat darks; flat darks are always safe.

A **master** is a set of calibration frames averaged into one. Averaging lowers the
random noise, so a master made from many frames adds less noise to your lights.

<!-- id: calibration.columns -->
## Columns

| Column | Frames | Meaning |
| --- | --- | --- |
| Exp | all | Exposure time |
| Temp | all | Sensor temperature from the header |
| Level | darks, bias, flat darks | Median level in ADU |
| Noise | darks, bias, flat darks | Read noise plus dark-current noise |
| Hot px | darks, bias, flat darks | Pixels far above their surroundings |
| Glow | darks, bias, flat darks | Brightest edge or corner above the centre (amp glow) |
| Banding | darks, bias, flat darks | Row or column pattern strength |
| Level (%) | flats | Median brightness as a share of full scale |
| Vignetting | flats | How much darker the corners are than the centre |
| Dust | flats | Dust shadows ("donuts") found |

A ★ in front of a name marks a master frame. ADU and other terms are explained in the
[glossary](help:calibration.glossary).

<!-- id: calibration.checks -->
## Checks on each set

These checks look at one type of frame at a time. Frames in a set should be near copies of
each other; one that differs is usually a mistake and would spoil the master.

<!-- id: calibration.check.odd -->
### Odd frames in a set

**What is checked.** Every frame's exposure, gain, offset, binning, temperature and image
size is compared with the rest of its set, as are its level and noise.

**Why.** Your stacking program averages the set into a master. One frame with a different
setting mixes a different signal into it, and the master no longer matches your lights.

**AdvAstro flags a frame when** (sets of three or more frames):

- the exposure differs by more than 1 %, or gain, offset, binning or image size differ at
  all;
- the temperature differs by more than 1.5 °C from the rest;
- a flat is more than 15 % brighter or dimmer than the other flats (the panel or the sky
  changed);
- a dark-type frame is noisier than 1.3 times the rest.

**What to do.** Leave the flagged frames out; AdvAstro already unticks them.

<!-- id: calibration.check.leak -->
### Level through the series (light leaks)

**What is checked.** The median level of each dark, bias and flat dark, in the order they
were taken.

**Why.** With the cap on, no light should reach the sensor, so every frame in a set should
have the same level, give or take a little noise. A level that climbs through the series
means light is getting in: a leaky cap, a gap at a filter wheel or an off-axis guider, or
darks taken in daylight. Leaked light in a master dark is subtracted from every light and
leaves dark patches.

**AdvAstro warns when** the levels in a set spread by more than twice the noise, and says
if they rise through the series. A single frame well above the rest is flagged as a
possible light leak; one well below points to a different offset setting.

**What to do.** Cover the telescope and the camera (a dark cloth over everything works
well), take darks at night or indoors, and leave the brightest frames out.

<!-- id: calibration.check.glow -->
### Amp glow

**What is checked.** The level at the corners and edges compared with the centre of the
darks.

**Why.** Some sensors have circuits near one edge that warm up and glow during long
exposures. It looks like a bright haze in a corner. It is the same in every exposure, so a
matching dark removes it completely; a dark of a different length or temperature does not.

**AdvAstro notes it when** an edge or corner is more than three times the noise above the
centre, and says which one.

**What to do.** Nothing, as long as the darks match the lights. Do not use dark scaling or
"optimise darks" in your stacking program: they scale the glow wrongly.

<!-- id: calibration.check.banding -->
### Banding

**What is checked.** How much each row and each column differs from its neighbours, after
slow changes across the frame are removed.

**Why.** Many cameras add faint horizontal or vertical stripes during readout. Part of the
pattern changes from frame to frame and only averages out over many frames. A master from
too few frames carries the stripes into your lights.

**AdvAstro warns when** the stripes are stronger than 0.3 times the noise.

**What to do.** Take more frames for the master (30 or more). Strong banding in the final
image can also be reduced with banding tools in PixInsight or Siril.

<!-- id: calibration.check.hot -->
### Hot pixels

**What is checked.** Pixels that are far brighter than their own surroundings in the darks
(more than ten times the noise), counted as a number and a share of the sensor.

**Why.** Hot pixels are single pixels that collect heat signal much faster than the rest.
They show as coloured dots or, after dithering and stacking, as short trails. Darks remove
most of them; the rest are removed by cosmetic correction or by rejection when stacking.

**AdvAstro reports** the count at your exposure and temperature. It is information, not a
fault: the number grows with longer exposures and warmer sensors.

**What to do.** Use matching darks, dither while imaging, and use cosmetic correction for
what remains. A count that suddenly grows between seasons is a sign the sensor is ageing
or running warmer.

<!-- id: calibration.check.flatlevel -->
### Flat brightness

**What is checked.** The median brightness of the flats as a share of the camera's full
scale (100 % = the brightest value a pixel can hold), and the level of each colour channel
for colour cameras.

**Why.** A flat must be bright enough that its own noise is small, but not so bright that
the sensor stops responding evenly. Near full scale, pixels stop growing in step with the
light (non-linear) and the flat no longer divides out the vignetting correctly.

**AdvAstro says:**

| Flat brightness | Verdict |
| --- | --- |
| under 15 % | Too dim: noisy flats add noise to every light |
| 15–25 % | Usable, but not ideal |
| 25–75 % | Good; 30–60 % is the sweet spot |
| over 75 % | Too bright: may be non-linear or clipped |

For colour cameras it also notes when one channel is less than half as bright as the
brightest. That is normal for many light panels (often weak in red or blue), but keep the
dimmest channel above about 10 %.

**What to do.** Change the flat exposure time (or the panel brightness) until the level is
around 40–50 %. Many capture programs, like NINA and ASIAIR, have an automatic flat
wizard that does this for you.

<!-- id: calibration.check.clipping -->
### Clipping

**What is checked.** The share of pixels in each flat that reach the top of the scale
(98 % of full scale or more).

**Why.** A clipped pixel has lost its information: it no longer tells how much light it
received, so the flat cannot correct that spot.

**AdvAstro flags a flat when** more than 0.01 % of its pixels are clipped.

**What to do.** Shorten the flat exposure or dim the panel.

<!-- id: calibration.check.vignetting -->
### Vignetting

**What is checked.** How much less light the corners of the flat get than the centre.

**Why.** Almost every telescope lights the centre of the sensor more than the corners.
Vignetting is not a fault: the flats are there to correct it. But it tells you how much
the flats have to do, and strong vignetting (over about 40 %) means the corners of your
lights have less signal and more noise even after correction.

**AdvAstro reports** the percentage as information.

**What to do.** Nothing, if the flats are good. Very strong vignetting can come from a
filter or adapter that is too small, or a wrong back-focus distance with a flattener or
reducer.

<!-- id: calibration.check.dust -->
### Dust shadows

**What is checked.** Small round darker spots ("donuts") in the flats, at least 1.5 %
darker than their surroundings, and how deep the deepest is.

**Why.** Dust on a filter or the sensor window casts a soft round shadow. The flats correct
it only if the dust has not moved between the lights and the flats. If it moved, you get
dark or bright rings in the stacked image.

**AdvAstro reports** how many shadows it found and the deepest one.

**What to do.** Take flats without touching the camera, filters or focus after the lights.
If the same donuts are in every session, clean the filter or the sensor window.

<!-- id: calibration.check.night -->
### Flats from the same night

**What is checked.** The time between the flats and the lights.

**Why.** Flats are a snapshot of the whole optical train: dust positions, camera rotation
and focus. Rotating the camera, refocusing, changing a filter or cleaning something in
between makes the flats no longer match.

**AdvAstro warns when** the flats are more than one and a half days from the lights.

**What to do.** Take new flats each night, or at least each time you change anything in the
optical train. Flats from another night are fine only if nothing was touched in between.

<!-- id: calibration.matching -->
## Checks against each other

These checks compare one type of frame with another. A calibration frame only works when it
was taken the same way as the frames it calibrates.

<!-- id: calibration.match.darks -->
### Darks against the lights

**What is checked.** Exposure, gain, offset, binning and temperature of the darks compared
with the lights, and how old the darks are.

**Why.** Heat signal, hot pixels and amp glow all grow with exposure time and temperature,
and gain and offset change the level of everything. A dark only subtracts the right amount
when every one of these is the same. A dark that is too strong leaves black holes where
hot pixels were; a dark that is too weak leaves hot pixels and glow behind.

**AdvAstro marks it as a problem when** the exposure differs by more than 1 %, gain, offset
or binning differ at all, or the temperature differs by more than 2 °C. Darks more than
about six months older than the lights are noted.

**What to do.** Take darks with the same settings. With a cooled camera you can build a
dark library (darks for each exposure and temperature you use) and reuse it; refresh it
about once a year, because sensors change slowly. Without cooling, take darks the same
night, at the same outside temperature.

<!-- id: calibration.match.flatdarks -->
### Flat darks against the flats

**What is checked.** Exposure and gain of the flat darks compared with the flats, and
whether there is anything to calibrate the flats with at all.

**Why.** Flats need their own fixed level removed before they can correct the lights.
Otherwise the correction is too weak and part of the vignetting stays. Flat
darks remove that level exactly when they match the flats.

**AdvAstro marks it as a problem when** the exposure differs by more than 5 % or the gain
differs, and when neither flat darks nor bias frames are present.

**What to do.** Take flat darks right after the flats, with the cap on and the same
settings. If you have none, bias frames usually work in their place.

<!-- id: calibration.match.bias -->
### Bias frames

**What is checked.** The bias exposure time, and its gain and offset against the lights.

**Why.** A bias frame should hold only the camera's fixed level, so it uses the shortest
exposure the camera allows. Its gain and offset must match the frames it calibrates,
because both change the fixed level.

**AdvAstro notes** bias frames longer than 0.1 s (they act as short darks, which is fine
with flats of the same length) and **warns** when their gain or offset differ from the
lights.

**What to do.** Take bias frames at the camera's shortest exposure with the same gain and
offset as the lights.

<!-- id: calibration.match.binning -->
### Binning of the flats

**What is checked.** Whether the flats are binned like the lights (for example both 1×1).

**Why.** A binned flat has a different pixel grid and cannot be divided into unbinned
lights.

**AdvAstro marks it as a problem when** the binning differs.

<!-- id: calibration.match.counts -->
### Number of frames

**What is checked.** How many frames each set has, unless a master is already there.

**Why.** Every calibration frame carries random noise. Averaging N frames lowers that
noise to 1/√N of one frame: about 26 % with 15 frames, 18 % with 30 and 14 % with 50.
Whatever noise is left in a master is added to every light.

| Frames | Minimum | Better |
| --- | --- | --- |
| Darks | 15 | 30 or more |
| Flats | 15 | 30 or more |
| Bias | 20 | 50 or more |
| Flat darks | 15 | 30 or more |

**AdvAstro warns when** a set has fewer than the minimum and no master.

**What to do.** Take more frames. Bias frames and flat darks are quick, so taking 50 costs
little.

<!-- id: calibration.match.labels -->
### Labels in the headers

**What is checked.** Whether the frame type in each file's header agrees with the folder it
is in.

**Why.** Some capture programs write the wrong type (ASIAIR, for example, labels flat darks
"Flat"). A stacking program that trusts the header would then mix flat darks into the
flats.

**AdvAstro notes it when** they disagree. It trusts the folder and the data and says so.

**What to do.** Usually nothing. If your stacking program sorts by header, put the files in
by hand or fix the type in the header.

The results feed the [workflow](help:workflow): for example how to calibrate the flats, and
whether to optimise the darks.

<!-- id: calibration.details -->
## One frame in detail

Double-click a frame in the table to open its analysis in a window of its own:

- **The frame** with an automatic stretch, so faint patterns such as amp glow, banding and
  dust show. For darks, bias and flat darks, **Hot pixel map** shows every hot pixel as a
  dot (yellow just above the limit, red and larger when much brighter) and counts them in
  each ninth of the sensor.
- **Why it was flagged**, if it was, in plain words.
- **Settings**: exposure, gain, offset, temperature, binning and size.
- **Measured**: every value next to the median of its set, with what it means.
- **Hot pixels** (darks, bias, flat darks): how many there are and how strong (above 10
  times the noise, very strong above 50 times, and *warm* pixels between 5 and 10 times),
  whether they spread evenly or cluster towards a warm part of the sensor, how this frame
  compares with the rest of the set, and what to do about them.

<!-- id: calibration.glossary -->
## Glossary

| Term | Meaning |
| --- | --- |
| ADU | Analog-to-digital unit: the raw number a pixel gets. A 16-bit camera goes from 0 to 65,535 |
| Full scale | The highest value a pixel can hold; flat brightness is given as a share of it |
| Gain | How much the camera amplifies the signal before it is turned into numbers |
| Offset | A fixed amount added to every pixel so no value falls below zero |
| Read noise | Noise added each time the sensor is read out, the same for every exposure length |
| Dark current | Signal that builds up from heat, growing with exposure time and temperature |
| Noise | The random scatter of pixel values around their average, given in ADU |
| Master | Many calibration frames of one type averaged into one cleaner frame |
| Binning | Combining 2×2 (or more) pixels into one, in the camera |
| Dithering | Moving the telescope slightly between lights so defects land on different pixels |
| Cosmetic correction | Replacing known hot and cold pixels with the value of their neighbours |
