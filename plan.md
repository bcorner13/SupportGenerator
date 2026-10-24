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
| `InitGui.py` | **Stub loader** only: execs `supportgen/gui.py` in an explicit namespace. FreeCAD's `RunInitGuiPy` loses module globals otherwise (known issue from the FreeCADMCPAgent addon) |
| `supportgen/__init__.py` | Package marker. **All code lives in the `supportgen` package** (see Phase 0 result B) |
| `supportgen/gui.py` | `SupportGeneratorWorkbench` + command registration, toolbar and menu |
| `supportgen/feature.py` | `SupportFeature` (Part::FeaturePython proxy) + `ViewProviderSupport`. Builds the geometry in `execute()`. **Saved class path: `supportgen.feature.SupportFeature`** |
| `supportgen/wedge_math.py` | **Pure-Python sizing math, no FreeCAD imports** (see *Wedge sizing*). Unit-tested with plain `python3` |
| `supportgen/params_schema.py` | The one table of Support* Param names, types, groups and tool defaults |
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
**Cost:** the proxy class path (`supportgen.feature.SupportFeature`) is saved inside every `.FCStd`
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

> **Phase 3 rename:** in code every generator variable carries the `Support` prefix
> (`SupportOverhangAngle`, `SupportLineWidth`, `SupportLayerHeight`, `SupportMinOverhangArea`; the
> rest already had it). Otherwise *Ensure Support Params* would adopt a same-named variable that
> another project uses for something else. `supportgen/params_schema.py` is the source of truth.

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
| `FixtureSlopeRun` | App::PropertyLength | 15 mm | Horizontal reach of the slope from the column (−X). Added in Phase 2: without it the slope's extent was undetermined (the sketch had 1 DOF left) |

---

## WEDGE SIZING (the computation) *(proposal)*

All of this lives in `wedge_math.py` as pure functions on plain tuples and floats, so it can be unit-tested
without FreeCAD. `supportgen/feature.py` extracts the numbers from the B-rep, calls these functions,
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
   1. `XZ_Datum` (PartDesign::Plane, FlatFace on XZ_Plane, no offset). As built: the Pad is
      Midplane, so the datum needs no `-FixtureDepth/2` offset to center the part in Y.
   2. `ProfileSketch` on `XZ_Datum`: closed profile with column, level ledge on +X, and a sloped
      overhang at `FixtureSlopeAngle` reaching `FixtureSlopeRun` on −X. Every dimension is bound to
      Fixture Params; the overall X extent is centered on the origin by a bound DistanceX.
   3. `Pad` Midplane, length `=FixtureDepth`, so the part is centered at (0,0,0) in XY per CAD_STANDARDS

**Both documents must be on disk before binding.** FreeCAD 1.1.4 refuses a cross-document
expression unless the Params file ("Linked document not saved") *and* the owner file ("Owner
document not saved") have been saved at least once. `01-build_fixture` checks both and stops with a
message. The same applies to Phase 4: *Add Supports* must refuse an unsaved target document.
2. `Supports` (Part::FeaturePython, created by the *Add Supports* command)
   - `Source` → `Fixture`
   - every input property → `<<Params>>#VarSet.*`

### Export

In the video, the part and supports were exported as STEP, imported into the slicer, and run through
"Split to objects". Here, the *Export* command writes the Body and `Supports` as **two objects in one
3MF** (`3mf/`), plus STLs (`stl/`). Slicer: slicer supports off.
**Verify in Phase 5:** does Creality Print import it as two objects? If it merges them, adapt the
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

## PHASE 0 RESULTS (2026-10-23)

Every result was obtained in the GUI FreeCAD the MCP bridge drives, with the banner
`TEST ENVIRONMENT VERIFIED: NewMacBook.local uuid D8B58553 FreeCAD 1.1.4 GUI`.
Environment (Step 4): MCP connected (xmlrpc, 1.1.4), GUI available, `temp_work` document created.

**A: clearance cut + tab contact** (in-memory fixture: 10 mm column, 25 mm level ledge at z 17, 45°
slope from z 5 to 20, 20 mm deep; wedges sized by `wedge_math`):
- `part.makeOffsetShape(0.25, 1e-3)`: valid, 22 ms.
- All 6 wedges (3 per overhang) after `cut(offset)`: valid, 1 solid each, ZMin 0 (on bed),
  `distToShape(part)` = **0.25** exactly. The level wedges lost exactly the 0.25 mm strip at the
  column wall (8.375 mm³ = 0.25 × 16.75 × 2), as designed.
- One 1-layer tab on the 45° wedge: valid, `distToShape` = **0** (touching), `common().Volume` =
  **0** (no overlap), contact-face Z span = **0.200 mm** (exactly 1 layer).
- **Finding:** the fixture's slope starts 5 mm above the bed, so its wedge is a right trapezoid with
  base 15 < height 19.8, and `footprint_ok` warns. The rule was written for triangles. A trapezoid
  standing next to a wall is stable in `s`, and the thin direction is `w` either way. Kept as a
  **warning only** (no wedge change); revisit after the test print.

**B: proxy reload path:** all 16 installed `Mod/<addon>` dirs are on `sys.path`, and addons import
by bare module name. So a `Mod/SupportGenerator/` package will import. **Collision found:**
FreeCADMCPAgent already ships a bare `_workbench.py`, and other addons expose generic names
(`commands`, `Qt`). Because the proxy path is frozen into model files, all code moved into a
uniquely named package, **`supportgen`**, before anything was saved. The actual restart-and-reopen test
is validation step 7, run in Phase 4 once the workbench is installed. (The Macro dir is also on
`sys.path`, which answers rev 1's open question, but a workbench is no longer conditional on it.)

---

## PHASE 2 RESULTS (2026-10-24)

Banner: `TEST ENVIRONMENT VERIFIED: NewMacBook.local uuid D8B58553 FreeCAD 1.1.4 GUI`.
- `00-bootstrap_params`: 13 Support + 7 Fixture variables; `Params.FCStd` saved with approval.
- `01-build_fixture`: sketch fully constrained (7 lines, 21 constraints, 0 DOF), all 7 dims + Pad
  length bound; 1 valid solid, 7750 mm³ (= 387.5 mm² × 20, hand-checked); bbox X −25..25,
  Y −10..10, Z 0..20; overhang faces: ledge underside (n_z −1, 500 mm²) and 45° slope
  (n_z −0.707, 424 mm²). Flex: `FixtureLedgeLen` +5 → X −27.5..27.5, still centered and fully
  constrained, then restored. `validate_document`: 12/12 valid. Audit clean on the saved file.
- Screenshots: `images/fixture_isometric.png`, `images/fixture_front.png`.

---

## PHASE 4 RESULTS (2026-10-24)

Banner on every FreeCAD check: `TEST ENVIRONMENT VERIFIED: NewMacBook.local uuid D8B58553 FreeCAD 1.1.4 GUI`.
`supportgen/feature.py` (`SupportFeature`, `ViewProviderSupport`, `build_supports`,
`make_supports`); *Add Supports* enabled; `macros/02-add_supports.FCMacro` adds `Fixture_Supports`.

As built (details the sizing section left open):
- Level face: `d` = the face's longer bounding-box side (axis-aligned in v1). Its free end, for
  `flare_end`, is found by probing `2 × SupportGap` past each end on the support side: part
  material there means a wall.
- Off-centre wedges: a dry run caught tabs and chamfer cutters shifted by twice the wedge offset
  (the contact points already carry it). Fixed before anything was saved.
- Tabs reach 0.01 mm back into the land so they fuse; a tab that lands off a kept wedge or overlaps
  the part is dropped with a warning. Results go in the read-only `WedgeCount` and `Warnings`.

Validation on the fixture (defaults): 6 wedges (3 under the slope, 3 under the ledge), 21 tabs.
1. Unit tests pass. 2. Audit clean on the saved file.
3. Plates `distToShape` = 0.250; all tabs touching (0) with zero overlap; sloped tab contact face
   Z span 0.200 (1 layer); level tabs are the 0.42 mm cap.
4. Gap at every wedge midpoint 0.250; land 0.848 at 0.02 mm back (0.84 nominal), 1.42 at 1.5 mm,
   full 2.0 at 4 mm.
5. Valid closed solids, ZMin = part ZMin. Warnings: only the 3 known slope-trapezoid footprint ones.
6. Flex, each restored afterwards (restored volume identical, 4202.425 mm³):
   OverhangAngle 50 → slope drops out, 3 wedges; Gap 0.3 → 0.300 everywhere; TabLayers 2 → 0.400
   contact; TabPitch 5 → 30 tabs; ChamferDepth 2 → 1.71 at 1.5 mm; FixtureHeight 24 → supports
   grow to Z 23.82; FixtureSlopeAngle 40 → follows. `validate_document` 13/13.
7. After a FreeCAD restart and reopen: proxies `supportgen.feature.SupportFeature` /
   `ViewProviderSupport` loaded from `Mod/SupportGenerator`, 13 bindings intact, forced recompute
   gives the same 4202.425 mm³. *Add Supports* is active with Fixture selected, inactive without.
   (Commands register on the first activation of the workbench.)

Note: another project's open `Params` document would capture `<<Params>>` by label. Close other
projects before opening this one (it happened on the reopen: UnderDeskCableTray was open).

---

## PHASES

0. **Environment + spikes:** MCP connection, GUI mode, `temp_work` document (Step 4). Spike
   `makeOffsetShape` on the fixture (step 9) and FeaturePython reload from `Mod/`.
1. `wedge_math.py` + tests, test-first. No FreeCAD needed.
2. `00-bootstrap_params` → `Params.FCStd`; `01-build_fixture` → fixture Body. Save only with approval.
3. Workbench skeleton (stub loader, commands, schema) → symlink into `Mod/` → restart FreeCAD.
4. `supportgen/feature.py`, then *Add Supports* on the fixture; validation 1–7.
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
