# Plan — SupportGenerator (rev 4, APPROVED 2026-10-23)

> Approved by Bradley 2026-10-23. Saves still need per-save approval (PROJECT_BOOTSTRAP Step 6).
>
> **Source:** Claude could not watch the video (YouTube serves no transcript to a fetch). Technique
> details come from **Bradley's summary** and **three video screenshots** (2026-10-23).
> Anything else is Claude's design, marked *(proposal)*.
>
> **Rev 2 (2026-10-23):** delivered as a **FreeCAD workbench** instead of a macro (Bradley:
> "can be a workbench as well"). Adds a **wedge-sizing computation** section, because the wedge
> must be sized relative to the part.
>
> **Rev 3 (2026-10-23):** contacts touch the part (zero gap, zero overlap) while staying in the
> separate support object.
>
> **Rev 4 (2026-10-23, from Bradley's reference images 4–5):** the gap is **0.25 mm absolute** (it was
> 0.25 × layer height = 0.05 mm, which is below slicer resolution). The wedge is a **45° right triangle**.
> Its contact edge is **heavily chamfered** to a narrow land. Contacts are **rectangular tabs** like the
> video's (disks are dropped). Tabs are **1–2 layers** tall and spaced **5–10 mm** apart (Bradley).

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
| `OverhangAngle` | App::PropertyAngle | 45° | A face needs support when it leans this far or more from vertical (normal.z ≤ −sin(angle) + 1e-6). A 45° face like the video's counts |
| `LineWidth` | App::PropertyLength | 0.42 mm | Slicer extrusion line width (0.4 nozzle). Sets the contact-land and tab minimums |
| `SupportGap` | App::PropertyLength | 0.25 mm | Air gap between the part and the wedge's contact land, measured **normal to the overhang face** (video sketch: dimension "0.25" between the parallel support-edge and part lines). Confirmed absolute mm, 2026-10-23 |
| `SupportWedgeAngle` | App::PropertyAngle | 45° | Angle of the wedge's free (non-contact) hypotenuse when the overhang is level. For a sloped overhang, the contact hypotenuse follows the face instead (video wedge: 45°) |
| `SupportPlateThick` | App::PropertyLength | 2.0 mm | Wedge body thickness: stiff, not "real thick" *(proposal; the video plate looks ~2–3 mm)* |
| `SupportMaxSlenderness` | App::PropertyFloat | 40 | Max wedge height ÷ plate thickness. Taller wedges thicken automatically *(proposal)* |
| `SupportContactLand` | App::PropertyLength | `=2 * LineWidth` → 0.84 mm | Width of the flat strip left at the contact edge after the chamfers *(proposal)* |
| `SupportChamferDepth` | App::PropertyLength | 3 mm | How far the double chamfer runs back from the contact edge into the plate ("heavily chamfered") *(proposal)* |
| `SupportWedgePitch` | App::PropertyLength | 15 mm | Max spacing between wedges across a wide overhang *(proposal)* |
| `LayerHeight` | App::PropertyLength | 0.20 mm | Slicer layer height. Used only to size tabs in layers |
| `SupportTabLayers` | App::PropertyInteger | 1 | Vertical extent of each tab where it meets the part, in print layers. Bradley: "1 or 2 layer tabs are sufficient". Valid 1–2 |
| `SupportTabPitch` | App::PropertyLength | 7.5 mm | Spacing between tabs along each wedge. Bradley: "spaced say 5–10 mm apart" |
| `MinOverhangArea` | App::PropertyArea | 4 mm² | Ignore overhang faces smaller than this (slicer bridges them) |

**Contact model (Bradley + video, 2026-10-23):** the wedge's chamfered contact land sits
`SupportGap` (0.25 mm) clear of the part. Small **rectangular tabs on the support** (like the video's
sketch) bridge that gap and **touch** the part: zero distance, zero overlap. The tabs belong to the
`Supports` object, a separate object from the part, so the slicer slices them independently and
never merges the two. The tabs are the only contact. Each tab is sized to be **1–2 print layers
tall** (`SupportTabLayers × LayerHeight`), is `SupportContactLand` across, and spans the `SupportGap`
(see sizing step 8).
*Inferred:* the video's tab "pairs" are the two side edges of one tab, so v1 places single tabs.

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
   `SupportGap + t/2` on each side. One centered wedge if `W ≤ SupportWedgePitch`, otherwise
   `ceil(W / SupportWedgePitch) + 1` wedges spanning W edge to edge, so the spacing is never more
   than the pitch. *(Corrected in Phase 1: the earlier `ceil(W/pitch)` formula could exceed the pitch.)*
3. **Contact line per wedge.** Cut F with the wedge's vertical plane to get segment `P_lo → P_hi`.
   Offset it by `SupportGap` along the **outward** normal `n` (away from the part, toward the support),
   **normal to the face** as dimensioned in the video sketch. Clip any part that drops below the bed.
   *(Corrected: rev 4 said `−n`, which would push the contact into the part.)*
4. **Height.** `h(s) = z_contact(s) − bed_z` along the segment; `h_max = max(h)`.
5. **Thickness.** `t = max(SupportPlateThick, h_max / SupportMaxSlenderness)`.
6. **Profile (in the d–Z plane): a right triangle**, like the video wedge (image 4).
   - **Sloped overhang** (the video case): the hypotenuse is the offset contact segment. One leg runs
     vertically down from `P_hi'` to the bed, and the other runs along the bed back to `P_lo'`'s foot. At 45°,
     the base equals the height, so the wedge is inherently stable and needs no separate footprint rule.
   - **Level overhang:** the top edge is the contact segment, with a vertical leg at the wall end (the
     clearance cut in step 9 holds it `SupportGap` off the wall). At the free end, the foot flares outward
     past the ledge's end by `h × cot(SupportWedgeAngle)`, so the free edge is a hypotenuse at
     `SupportWedgeAngle`. The result is a trapezoid with full contact along the top and base ≥ height
     at 45°. The FreeCAD side tells `wedge_math` which end is free (`flare_end`).
   - **Footprint check:** the base on the bed must be ≥ `h_max × cot(SupportWedgeAngle)` or the wedge
     gets flagged. At 45° that's base ≥ height.
7. **Chamfered contact edge** (image 4: "heavily chamfered"). Along the contact edge, bevel both faces of
   the plate symmetrically. The plate narrows from `t` to `SupportContactLand` over
   `SupportChamferDepth`, measured back from the edge. That gives a stiff plate with a knife-like land,
   so there's little contact area and a clean break. Built as a loft or a cut prism along the edge,
   not as a `Part.makeChamfer` on picked edges (no topological naming).
8. **Contact tabs.** Contact length `Lc = |P_hi − P_lo|`.
   `n_tabs = max(2, ceil(Lc / SupportTabPitch))`, evenly spaced at `Lc / n_tabs` (≤ pitch), with half a
   space in from each end. Each tab is a small box. It is `SupportContactLand` across and `SupportGap`
   along `n`. Its length along the edge is computed so its contact face spans exactly
   `SupportTabLayers` layers in Z:
   `L_tab = min(SupportTabLayers × LayerHeight / sin(θ), SupportTabLayers × LineWidth)`, where θ is the
   contact edge's slope from horizontal. For a 45° edge at 0.2 mm layers, that's 0.28 mm for 1 layer and
   0.57 mm for 2 layers. The cap keeps near-level contacts from growing long tabs (at 2° the uncapped
   formula gives 5.7 mm). A level contact (θ < 1°) gets the cap. *(Corrected: rev 4's
   `max(LineWidth, …)` would have forced every 1-layer 45° tab up to 0.42 mm, i.e. 1.5 layers.)* The tab sits on the land, and its top face is
   **coplanar with the overhang face**: touching, not overlapping. Tabs are fused into the support solid,
   never into the part.
9. **Clearance clip.** Extrude the profile ±t/2 along `w`, apply the chamfer, fuse all wedges, then cut
   with `part.makeOffsetShape(SupportGap)`. The tabs are added *after* this cut, so the cut doesn't
   trim them. If the cut removes a wedge's bed contact (part material below), skip that wedge with a
   warning. Support-on-part is Phase 6.
10. **Edge cases.** If `h_max < SupportChamferDepth + SupportContactLand`, the wedge is too short for
    its chamfer: shrink the chamfer depth to fit, or skip the wedge below `2 × LineWidth` (the slicer
    bridges it). If F needs a wedge plane that hits the part before reaching the bed, step 9 catches it.

`tests/test_wedge_math.py` covers, before any FreeCAD work: a 45° slope (right triangle, base == height),
a level ledge (45° free hypotenuse, trapezoid clip), a very tall wedge (thickness grows), a short wedge
(chamfer shrinks or the wedge is skipped), a wide face (multiple wedges), tab count at the boundaries,
tab height == gap, and gap measured normal to the face.

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
3. **Gap by distance, not volume:** `part.distToShape(wedges_without_tabs)[0] ≥ SupportGap − 0.005`.
   **Tabs:** each tab's `distToShape(part) ≤ 0.001` (touching), and
   `tab.common(part).Volume ≤ 1e-6` (not overlapping). On a sloped contact, each tab's **contact face** Z extent = `SupportTabLayers × LayerHeight` ± 0.01.
4. Per wedge: the gap normal to the face at the contact midpoint = `SupportGap` ± 0.005, `t` matches
   step 5, the land width = `SupportContactLand`, and the footprint passes the step 6 check.
5. `Supports.Shape.isValid()`, closed solids, and `Supports` ZMin == part ZMin.
6. **Flex test:** change `OverhangAngle`, `SupportGap`, `SupportTabLayers` (1→2), `SupportTabPitch`,
   `SupportChamferDepth`, `FixtureHeight`, and `FixtureSlopeAngle`, recompute, and re-check 3–5. A binding that doesn't
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

Answered 2026-10-23 (all rounds):
- Supports are a separate object, and 3MF replaces STEP + split. Delivered as a workbench.
- **Gap = 0.25 mm absolute**, normal to the face, per the video sketch.
- **45° right-triangle wedge** with a **heavily chamfered** contact edge (image 4).
- **Rectangular tabs** on the support that touch the part, never added to the part. Tabs are
  **1–2 layers** tall and **5–10 mm apart** (default 7.5 mm).

Remaining (non-blocking; *(proposal)* defaults stand until the test print): plate thickness 2.0 mm,
slenderness ≤ 40, contact land 0.84 mm, chamfer depth 3 mm, wedge pitch 15 mm.
