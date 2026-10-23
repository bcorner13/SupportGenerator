# Plan — SupportGenerator (rev 3, AWAITING APPROVAL)

> Execution is FORBIDDEN until Bradley approves this plan (PROJECT_BOOTSTRAP Step 3).
>
> **Source:** Claude could not watch the video (YouTube serves no transcript to a fetch). Technique
> details come from **Bradley's summary** and **three video screenshots** (2026-10-23).
> Anything else is Claude's design, marked *(proposal)*.
>
> **Rev 2 (2026-10-23):** delivered as a **FreeCAD workbench** instead of a macro (Bradley:
> "can be a workbench as well"). Adds a **wedge-sizing computation** section, because the wedge
> must be sized relative to the part.
>
> **Rev 3 (2026-10-23):** gap = 0.25 × **layer height**. Contacts are **disks on the support** that
> touch the part (zero gap, zero overlap) while staying in the separate support object.

---

## Architecture

The tool is an addon workbench. It's developed in this repo under `workbench/SupportGenerator/` and
symlinked to `~/Library/Application Support/FreeCAD/v1-1/Mod/SupportGenerator`.

| File | Role |
|---|---|
| `InitGui.py` | **Stub loader** only: execs `_workbench.py` in an explicit namespace. FreeCAD's `RunInitGuiPy` loses module globals otherwise (known issue from the FreeCADMCPAgent addon) |
| `_workbench.py` | `SupportGeneratorWorkbench` + command registration, toolbar and menu |
| `support_feature.py` | `SupportFeature` (Part::FeaturePython proxy) + `ViewProviderSupport`. Builds the geometry in `execute()` |
| `wedge_math.py` | **Pure-Python sizing math, no FreeCAD imports** (see *Wedge sizing*). Unit-tested with plain `python3` |
| `params_schema.py` | The one table of Support* Param names, types, groups and tool defaults |
| `tests/test_wedge_math.py` | Unit tests for the sizing math (run outside FreeCAD) |
| `Resources/icons/*.svg` | Command icons |

**Commands**

1. **Ensure Support Params**: adds any missing `Support*` variables to the active project's
   `Params` VarSet, using `params_schema.py` defaults. Variables that already exist are left
   alone (idempotent). This follows the global rule "if the needed variable doesn't exist, add it
   to the project's VarSet first".
2. **Add Supports**: for the selected Body, creates a `Supports` FeaturePython object (`Source` →
   Body) and binds every input property to `<<Params>>#VarSet.Support*`. It runs command 1 first
   if anything is missing.
3. **Export Part + Supports (3MF)**: exports the Body and its `Supports` as two separate objects in
   one 3MF.

**Why a workbench:** the module is guaranteed to be on `sys.path` (FreeCAD adds every `Mod/` dir).
That resolves rev 1's biggest risk, a FeaturePython proxy failing to reload on reopen. It also
gives the tool real commands and icons and makes it usable from any project, not just this one.
**Cost:** the proxy class path (`support_feature.SupportFeature`) is saved inside every `.FCStd`
that uses it, so module and class names are a frozen API from the first saved file.

**Where the settings live:** each project that uses the tool keeps its own `Support*` values in its
own `Params.FCStd`, so supports tuned for ASA in one project don't change PLA prints in another.
The workbench owns only the *defaults* in `params_schema.py`, and those are tool defaults, not model
literals. This project's `Params.FCStd` holds the same Support* set plus the Fixture* set.

Project `macros/` still drive this project's own model changes (`00-bootstrap_params`,
`01-build_fixture`) per the workflow conventions. The workbench is the product, and the macros
build the test bench.

---

## PARAMETERS

### Generator (group `Support`, created by *Ensure Support Params*)

| Name | Type | Default | Meaning |
|---|---|---|---|
| `OverhangAngle` | App::PropertyAngle | 45° | A face needs support when it leans past this angle from vertical (normal.z < −sin(angle)) |
| `LayerHeight` | App::PropertyLength | 0.20 mm | Slicer layer height. The gap is scaled from this |
| `LineWidth` | App::PropertyLength | 0.42 mm | Slicer extrusion line width (0.4 nozzle). Sets the minimum wedge thickness |
| `SupportGapRatio` | App::PropertyFloat | 0.25 | Gap as a fraction of `LayerHeight` (video: "0.25 the layer width" = layer height, confirmed 2026-10-23) |
| `SupportGap` | App::PropertyLength | `=LayerHeight * SupportGapRatio` → 0.05 mm | Derived: air gap between the part and the wedge body (disks bridge it) |
| `SupportWallThick` | App::PropertyLength | `=2 * LineWidth` → 0.84 mm | *Minimum* wedge plate thickness (video: supports "don't need to be real thick") |
| `SupportMaxSlenderness` | App::PropertyFloat | 30 | Max wedge height ÷ thickness. Taller wedges thicken automatically *(proposal)* |
| `SupportBaseRatio` | App::PropertyFloat | 0.5 | Min footprint length on the bed ÷ wedge height, for tip-over stability *(proposal)* |
| `SupportWedgePitch` | App::PropertyLength | 15 mm | Max spacing between wedges across a wide overhang *(proposal)* |
| `SupportDiskDia` | App::PropertyLength | `=2 * LineWidth` → 0.84 mm | Contact-disk diameter. Disks are on the **support**, never the part *(default is a proposal)* |
| `SupportDiskPitch` | App::PropertyLength | 10 mm | Spacing between contact disks along each wedge (estimated from screenshot) |
| `MinOverhangArea` | App::PropertyArea | 4 mm² | Ignore overhang faces smaller than this (slicer bridges them) |

**Contact model (Bradley, 2026-10-23):** the wedge body sits `SupportGap` (0.05 mm) clear of the
part everywhere. Small **disks on the support** bridge that gap and **touch** the part, which means zero
distance and zero overlap. The disks belong to the `Supports` object, a separate object from the part,
so the slicer slices them independently and never merges the two. The disks are the only contact.

**Gap concept:** one part-to-support gap, because it's one physical interface (the support contact).
If the test print shows the top and side gaps need different values, split it into
`SupportZGap` / `SupportXYGap`.

### Test fixture (group `Fixture`): this project only, a cantilever "Γ"

| Name | Type | Default | Meaning |
|---|---|---|---|
| `FixtureColumnW` | App::PropertyLength | 10 mm | Column width (X) |
| `FixtureDepth` | App::PropertyLength | 20 mm | Part depth (Y) |
| `FixtureHeight` | App::PropertyLength | 20 mm | Overall height (Z) |
| `FixtureLedgeLen` | App::PropertyLength | 25 mm | Cantilever length past the column (X) |
| `FixtureLedgeThick` | App::PropertyLength | 3 mm | Cantilever thickness; its underside is the 0° overhang under test |
| `FixtureSlopeAngle` | App::PropertyAngle | 45° | A second, sloped overhang on the opposite side. Exercises the angled-face case shown in the video |

---

## WEDGE SIZING (the computation) *(proposal)*

All of this lives in `wedge_math.py` as pure functions on plain tuples and floats, so it can be unit-tested
without FreeCAD. `support_feature.py` extracts the numbers from the B-rep, calls these functions,
and turns the results back into solids.

For each qualifying overhang face **F** (planar in v1):

1. **Frame.** `n` = F's outward normal. `d` = the horizontal "downhill" direction, `normalize(n.x, n.y)`
   (for a level face, `d` = the face's longest horizontal extent). `w` = horizontal, ⟂ `d`.
   Wedges stand in vertical planes spanned by `d` and Z.
2. **Wedge count and positions across the face.** `W` = F's extent along `w`, inset by
   `SupportGap + t/2` on each side. `n_wedges = max(1, ceil(W / SupportWedgePitch))`. They're
   evenly spaced, with one centered when `n_wedges = 1`.
3. **Contact line per wedge.** Cut F with the wedge's vertical plane to get segment `P_lo → P_hi`.
   Then offset it straight down by `SupportGap` (a vertical gap, so it prints as an exact air layer).
4. **Height.** `h(s) = z_contact(s) − bed_z` along the segment; `h_max = max(h)`.
5. **Thickness.** `t = max(SupportWallThick, h_max / SupportMaxSlenderness)`.
   Short wedges stay at the thin minimum, and tall ones get just enough stiffness not to wobble under the nozzle.
6. **Profile (in the d–Z plane).** The polygon bounded by the contact segment, the bed, and verticals
   down from the segment ends. A sloped face gives a triangle, which is the video's wedge. A level
   face gives a rectangle, which then gets the diagonal treatment in step 7.
7. **Stability / footprint.** Required footprint `B_min = h_max × SupportBaseRatio`. If the
   profile's bed length is under `B_min`, flare the foot outward along `d` (away from the part) to
   `B_min`. The outer edge becomes a sloped hypotenuse, so the profile stays a wedge. For a level face,
   the profile becomes a triangle with full contact along the top and a diagonal back edge.
   *Which side of the face the hypotenuse goes on needs checking against the video.*
8. **Contact disks.** Contact length `Lc = |P_hi − P_lo|`.
   `n_disks = max(2, floor(Lc / SupportDiskPitch) + 1)`, evenly spaced and inset `SupportDiskDia`
   from both ends. Each disk is a cylinder of diameter `SupportDiskDia`. Its axis is the overhang
   face's normal `n`. Its base sits on the wedge's contact edge, and its height exactly spans the gap,
   so its top face is **coplanar with the overhang face**: touching, not overlapping. The disks are
   fused into the support solid and never into the part. When `SupportDiskDia > t`, the disk
   overhangs the plate edge slightly, which is fine as a mushroom-cap contact.
9. **Clearance clip.** Extrude the profile ±t/2 along `w`, fuse all wedges, then cut with
   `part.makeOffsetShape(SupportGap)`. The disks are added *after* this cut, so the cut doesn't
   trim them. If the cut removes a wedge's bed contact (part material below), skip that wedge with a
   warning. Support-on-part is Phase 6.
10. **Edge cases.** For `h_max < 2 × LineWidth`, skip it (too short to print a wedge; the slicer
    bridges it). If F needs a wedge plane that hits the part before reaching the bed, step 9 catches it.

`tests/test_wedge_math.py` covers, before any FreeCAD work: a level ledge, a 45° slope, a
very tall slope (thickness grows), a short wedge (gets skipped), a wide face (multiple wedges), the disk
count at the boundaries, and the disk height == gap.

---

## FEATURE TREE

### `SupportGenerator.FCStd` (fixture + generated supports)

1. `Fixture` (PartDesign::Body)
   1. `XZ_Datum` (PartDesign::Plane on XZ_Plane, offset bound to `-FixtureDepth/2`)
   2. `ProfileSketch` on `XZ_Datum`: closed profile with column, level ledge on +X, and a sloped
      overhang at `FixtureSlopeAngle` on −X. Every dimension is bound to Fixture Params.
   3. `Pad` length `=FixtureDepth`, so the part is centered at (0,0,0) in XY per CAD_STANDARDS
2. `Supports` (Part::FeaturePython, created by the *Add Supports* command)
   - `Source` → `Fixture`
   - every input property → `<<Params>>#VarSet.*`

### Export

In the video, the part and supports were exported as STEP, imported into the slicer, and run through
"Split to objects". Here, the *Export* command writes the Body and `Supports` as **two objects in one
3MF** (`3mf/`), plus STLs (`stl/`). Slicer: slicer supports off.
**Verify in Phase 4:** does Creality Print import it as two objects? If it merges them, adapt the
CircleInlayRouterJig custom 3MF writer.

---

## CONSTRAINT STRATEGY

- **Fixture sketch:** fully constrained. Every dimension is bound to a Fixture Param, and the sketch
  sits on a datum plane, never a face.
- **Generator:** has no sketches. Every numeric input is a FeaturePython property bound with
  `setExpression` to `<<Params>>#VarSet.*`. *Add Supports* wipes and re-binds them on re-run.
- **Literals in workbench code:** only `params_schema.py` defaults and numeric tolerances
  (e.g. 1e-6), both documented inline.

---

## VALIDATION

0. **Every run starts with `require_laptop()`** from `scripts/test_env_guard.py`, with its
   `TEST ENVIRONMENT VERIFIED` banner quoted (PROJECT_BOOTSTRAP Step 8). Inside FreeCAD, run
   `importlib.reload(test_env_guard)` first. A result without the banner is invalid.
1. `python3 workbench/SupportGenerator/tests/test_wedge_math.py`: all pass (calls `require_laptop(need_freecad=False)`).
2. `python3 scripts/audit_parametric.py`: clean.
3. **Gap by distance, not volume:** `part.distToShape(wedges_without_disks)[0] ≥ SupportGap − 0.005`.
   **Disks:** each disk's `distToShape(part) ≤ 0.001` (touching), and
   `disk.common(part).Volume ≤ 1e-6` (not overlapping).
4. Per wedge: the vertical gap at the contact midpoint = `SupportGap` ± 0.005, `t` matches step 5,
   and the footprint is ≥ `B_min`.
5. `Supports.Shape.isValid()`, closed solids, and `Supports` ZMin == part ZMin.
6. **Flex test:** change `OverhangAngle`, `SupportGapRatio`, `SupportMaxSlenderness`,
   `FixtureHeight`, and `FixtureSlopeAngle`, recompute, and re-check 3–5. A binding that doesn't
   move the geometry counts as a failure.
7. Restart FreeCAD, reopen `SupportGenerator.FCStd`. `Supports` must recompute, which proves the proxy reloads.
8. **PLA test print**: record removal quality + overhang finish in CLAUDE.md's print profile, then tune.

---

## PHASES

0. **Environment + spikes:** MCP connection, GUI mode, `temp_work` document (Step 4). Spike
   `makeOffsetShape` on the fixture (step 9) and FeaturePython reload from `Mod/`.
1. `wedge_math.py` + tests, test-first. No FreeCAD needed.
2. `00-bootstrap_params` → `Params.FCStd`; `01-build_fixture` → fixture Body. Save only with approval.
3. Workbench skeleton (stub loader, commands, schema) → symlink into `Mod/` → restart FreeCAD.
4. `support_feature.py`, then *Add Supports* on the fixture; validation 1–7.
5. *Export*: two-object 3MF → Creality check → test print → tune → record profile.
6. (Later) Curved faces, support-on-part, mesh input, and an optional task panel to preview/override per face.

---

## Open questions (answer before approval)

Answered 2026-10-23: supports are thin; the gap is 0.25 × layer width; supports are a separate object;
3MF replaces STEP + split; the wedge is a triangular gusset with small spaced contact points; delivered as a workbench.

Answered 2026-10-23 (round 3): the gap is **0.25 × layer height** (0.05 mm). Contact points **touch** the
part but belong to the separate support object, so the slicer never merges them. Contacts are **small
disks on the support**, and the part is never modified.

Remaining (non-blocking; defaults stand until the test print):

1. **Disk diameter:** the default is 2 × line width (0.84 mm). Did the video use a specific size?
2. **Wedge sizing rules:** base ≥ 0.5 × height, slenderness ≤ 30, wedge pitch 15 mm, disk pitch 10 mm
   are all *(proposal)* values.
