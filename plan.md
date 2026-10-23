# Plan — SupportGenerator (rev 1, AWAITING APPROVAL)

> Execution is FORBIDDEN until Bradley approves this plan (PROJECT_BOOTSTRAP Step 3).
>
> **Source:** Claude could not watch the video (YouTube serves no transcript to a fetch). The
> technique details below come from **Bradley's summary** (2026-10-23): thin supports, wedge
> gap = 0.25 × layer width, supports as a separate object, split into objects in the slicer.
> Everything else is Claude's design and is marked as such.

---

## Architecture

| Piece | Where | Role |
|---|---|---|
| `support_generator.py` | `macros/` → symlinked into FreeCAD Macro dir as `SG-support_generator.py` | Library module: `SupportFeature` FeaturePython proxy + geometry algorithm |
| `SupportGenerator.FCMacro` | `macros/` → `SG-SupportGenerator.FCMacro` | User command: take the selected Body, create a `Supports` object, bind its properties to Params |
| `00-bootstrap_params.FCMacro` | `macros/` → `SG-00-bootstrap_params.FCMacro` | Creates `Params.FCStd` + VarSet (idempotent) |
| `01-build_fixture.FCMacro` | `macros/` → `SG-01-build_fixture.FCMacro` | Builds the parametric test-fixture Body in `SupportGenerator.FCStd` |

**Why a FeaturePython object instead of a one-shot macro:** a one-shot macro produces a dead
`Part::Feature` that goes stale the moment the Body or a Param changes. That violates the intent.md
rule that supports update on recompute. A `Part::FeaturePython` with a `Source` link and
expression-bound gap properties recomputes like any other feature.

**Known risk (verify in Phase 0):** a FeaturePython proxy's module must be importable when the
document is reopened. The plan assumes FreeCAD's user Macro dir is on `sys.path`, which is unverified.
If it isn't, the module goes in a minimal `Mod/SupportGenerator/` addon folder instead.

---

## PARAMETERS

`Params.FCStd` → `VarSet`. Generator settings are what any user Body's supports bind to. Fixture
settings drive the test part only.

### Generator (group `Support`)

| Name | Type | Default | Meaning |
|---|---|---|---|
| `OverhangAngle` | App::PropertyAngle | 45° | A face needs support when it leans past this angle from vertical (normal.z < −sin(angle)) |
| `LineWidth` | App::PropertyLength | 0.42 mm | Slicer extrusion line width (0.4 nozzle). The gap is scaled from this |
| `SupportGapRatio` | App::PropertyFloat | 0.25 | Gap as a fraction of `LineWidth` (from the video: "0.25 the layer width") |
| `SupportGap` | App::PropertyLength | `=LineWidth * SupportGapRatio` → 0.105 mm | Derived: air gap between part and wedge |
| `SupportWallThick` | App::PropertyLength | `=2 * LineWidth` → 0.84 mm | Wedge plate thickness. Kept thin on purpose (video: supports "don't need to be real thick") |
| `SupportSpacing` | App::PropertyLength | 5 mm | Center-to-center spacing of wedge plates under an overhang |
| `MinOverhangArea` | App::PropertyArea | 4 mm² | Ignore overhang faces smaller than this (slicer bridges them) |

**Interpretation to confirm:** I read "layer width" as the extrusion **line width**, not the
layer height. With 0.42 mm lines, the gap is 0.105 mm. If you meant layer height (0.2 mm), the gap is
0.05 mm. That's a one-Param swap either way.

**Gap concept:** the video uses a single part-to-wedge gap, so `SupportGap` serves both the
vertical gap (wedge tip under the overhang) and the lateral gap (wedge beside a wall). Both are the
same physical interface, the support contact, so one Param doesn't break rule 4. If the test print
shows they need different values, it gets split into `SupportZGap` / `SupportXYGap`.

### Test fixture (group `Fixture`): a cantilever "Γ" shape

| Name | Type | Default | Meaning |
|---|---|---|---|
| `FixtureColumnW` | App::PropertyLength | 10 mm | Column width (X) |
| `FixtureDepth` | App::PropertyLength | 20 mm | Part depth (Y) |
| `FixtureHeight` | App::PropertyLength | 20 mm | Overall height (Z) |
| `FixtureLedgeLen` | App::PropertyLength | 25 mm | Cantilever length past the column (X) |
| `FixtureLedgeThick` | App::PropertyLength | 3 mm | Cantilever thickness; its underside is the 0° overhang under test |

The default SupportXYGap and fixture values are first guesses, to be tuned after the test print.

---

## FEATURE TREE

### `SupportGenerator.FCStd` (fixture + generated supports)

1. `Fixture` (PartDesign::Body)
   1. `XZ_Datum` (PartDesign::Plane on XZ_Plane, offset bound to `-FixtureDepth/2`)
   2. `ProfileSketch` on `XZ_Datum`: closed Γ profile (column + ledge), every dimension bound to Fixture Params, symmetric about origin X
   3. `Pad` length `=FixtureDepth`, so the part is centered at (0,0,0) in XY per CAD_STANDARDS
2. `Supports` (Part::FeaturePython, created by `SupportGenerator.FCMacro`)
   - `Source` → `Fixture`
   - `OverhangAngle`, `Gap`, `WallThick`, `Spacing`, `MinArea` → expressions `<<Params>>#VarSet.*`

### Support algorithm (`SupportFeature.execute`)

1. `part = Source.Shape`; `bed_z = part.BoundBox.ZMin`.
2. Overhang faces: every face whose outward normal has `z < −sin(OverhangAngle)`, whose
   `ZMin > bed_z + SupportGap` (not on the bed), and whose `Area ≥ MinArea`.
   **v1 handles planar faces only**; curved faces are skipped with a console warning.
3. For each face: lay out thin **wedge plates** (`SupportWallThick` thick) across the face's
   footprint at `SupportSpacing`. Each plate is a vertical fin whose top edge follows the overhang
   and whose base sits on `bed_z`. "Wedge" means the fin tapers toward the part, so the contact
   is a narrow edge and the base is wide and stable. **The exact wedge profile needs confirming
   from the video** (see Open questions).
4. Gap: lower each fin's top by `SupportGap`, and cut the fused fins with
   `part.makeOffsetShape(SupportGap)`. That holds a uniform `SupportGap` from the part on every
   side. Because there's a single gap concept, the earlier XY-vs-Z cut conflict goes away.
5. `obj.Shape = result` (an empty compound when nothing needs support).

### Export

In the video, the part and supports were exported as STEP, imported into the slicer, and run through
"Split to objects". Here, the Body and `Supports` are exported as **two separate objects in one 3MF**
(`3mf/`), so the split happens at export and no slicer step is needed. STLs also go to `stl/`.
Slicer: slicer supports off, both objects on one plate.

**Verify in Phase 4, not assumed:** Creality Print has to import FreeCAD's 3MF as two objects
rather than one merged mesh. If it merges them, fall back to a custom 3MF writer (the
CircleInlayRouterJig export macro already writes Creality project 3MFs) or to STEP + split.

---

## CONSTRAINT STRATEGY

- **Fixture sketch:** fully constrained. Every Distance/DistanceX/DistanceY is bound to a Fixture
  Param, and symmetry about the V axis keeps it centered. The sketch attaches to a datum plane,
  never a face (hard rule 3).
- **Generator:** has no sketches. Its numeric inputs are FeaturePython properties, each bound with
  `setExpression` to `<<Params>>#VarSet.*`. The macro wipes and re-binds them on re-run (idempotent).
- Literals in `support_generator.py` are limited to numeric tolerances (e.g. 1e-6 comparisons),
  documented inline.

---

## VALIDATION

1. `python3 scripts/audit_parametric.py`: clean.
2. **Gap check by distance, not volume** (per the print-in-place lesson):
   `part.distToShape(supports)[0] ≥ SupportGap − 0.005`. A touching support has 0
   interference volume but still fuses.
3. Per overhang face: measured vertical gap at the face centroid = `SupportGap` ± 0.005.
4. `Supports.Shape.isValid()`, all solids closed; `Supports` ZMin == part ZMin (sits on bed).
5. **Flex test:** change `OverhangAngle`, `SupportGapRatio`, `SupportWallThick`, and
   `FixtureLedgeLen` in Params, recompute, and re-run checks 2–4. A binding that doesn't move the
   geometry counts as a failure.
6. Close and reopen `SupportGenerator.FCStd`. `Supports` must recompute, which proves the proxy module loads.
7. **PLA test print** of fixture + supports at `LayerHeight`. Record removal quality and the overhang
   surface finish in CLAUDE.md's print profile. Tune `SupportXYGap` / `SupportZGapLayers`.

---

## PHASES

0. **Environment + spikes:** MCP connection, GUI mode, `temp_work` document (Step 4). Spike the
   FeaturePython reload question (sys.path) and the uniform-gap cut (algorithm step 4).
1. `00-bootstrap_params` → `Params.FCStd` (save only with approval).
2. `01-build_fixture` → `SupportGenerator.FCStd` fixture Body.
3. `support_generator.py` + `SupportGenerator.FCMacro`; run on the fixture; validation 1–6.
4. Export a two-object 3MF + STLs → confirm Creality Print sees two objects → test print → tune → record profile.
5. (Later) Curved faces, support-on-part refinements, and mesh input.

---

## Open questions (answer before approval)

Answered 2026-10-23: supports are thin, the gap is 0.25 × layer width, supports are a separate object,
and 3MF export replaces STEP + split.

1. **"Layer width":** line width (0.105 mm gap) or layer height (0.05 mm)?
2. **Wedge shape:** is a wedge a vertical fin that tapers to a knife edge at the part (what this plan
   assumes)? Or a triangular gusset between a wall and the overhang (a 45° brace off the part's own side)?
3. Any slicer-side settings from the video (wall count on the supports, a seam/contact setting) that
   belong in the print profile?
