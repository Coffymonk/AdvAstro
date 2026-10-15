# Reference sessions (local only)

Put reference sessions here, one folder per session, for example:

```
Samples/
  Session-20261015_NGC7000/
    LIGHT/ DARK/ FLAT/ FLAT DARK/ BIAS/
    WBPP/          your PixInsight run, for comparison
    session.mksession
    notes.md       what you did by hand and what you concluded
```

Everything in this folder except this README is ignored by Git, so large files never reach GitHub.

`notes.md` matters: it records your manual judgement (which subs you rejected and why, the settings you used in PixInsight and Siril). The validation tests compare AdvAstro's output against it.
