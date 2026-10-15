<!-- id: calibration -->
# Calibration frames

AdvAstro checks bias, dark, flat and flat-dark frames found next to your lights, on their
own and against the lights. Turn this off in
[Settings › Sub selection](help:settings.selection) if you want.

Each type gets its own tab above the table, and the Session tab lists every check. Click a
flagged file in the list to select it in the table. Odd frames are unticked in the
suggested selection, just like subs.

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

A ★ in front of a name marks a master frame.

<!-- id: calibration.checks -->
## What is checked

**Darks, bias and flat darks**

- **Level through the series**: darks should be equally dark. A level that rises through
  the series means light reached the sensor: a light leak, or darks taken in daylight.
- **Amp glow**: a bright edge or corner; darks remove it only when they match the lights.
- **Banding**: row or column patterns; more frames make a smoother master.
- **Hot pixels**: how many there are at this exposure and temperature.

**Flats**

- **Brightness**: aim for 25–75 % of full scale. Under 15 % is too dim (noisy flats); over
  75 % risks clipping. The dimmest colour channel should stay above about 10 %.
- **Clipping**, **vignetting** and **dust shadows**.
- **Same night**: flats from another night no longer match dust and camera rotation.

**Against each other**

- **Darks vs lights**: exposure, gain, offset, binning and temperature (within 2 °C) must
  match. Darks older than about six months are noted; a library is fine, but refresh it
  about once a year.
- **Flat darks vs flats**: same exposure and gain.
- **Bias**: should be the shortest possible exposure.
- **Frame counts**: at least 15 darks, 15 flats, 20 bias frames and 15 flat darks; 30 or more
  (50 for bias) give a master with less noise.
- **Labels**: when a header says one thing and the folder another (for example flat darks
  labelled "Flat"), AdvAstro trusts the folder and says so.

The results feed the [workflow](help:workflow): for example how to calibrate the flats, and
whether to optimise the darks.
