# SupportGenerator

A FreeCAD 1.1 workbench that generates **modeled, break-away print supports** for a selected
PartDesign Body: thin 45° wedge plates with a heavily chamfered contact edge, a 0.25 mm air gap
to the part, and small 1–2-layer tabs that touch the part, all in a **separate object**. Part and
supports export together as a two-object 3MF, the slicer prints them with its own supports off, and
the supports snap away clean.

Inspired by *"Without a Trace: 3D Printed Supports That Remove Like Magic"*
(https://youtu.be/1Zocl7n98xY).

**Status (2026-10-24):** workbench working: Add Supports and Export verified on the test fixture
(`plan.md` Phase 4 and 5 results). Awaiting the first test print. v1 supports planar overhangs on
parts standing on the bed.

## Layout

| Path | Contents |
|---|---|
| `intent.md` / `plan.md` | Goal and the approved build plan (with results per phase) |
| `Params.FCStd` | VarSet of generator settings (`Support*`) and test-fixture dimensions (`Fixture*`). Created by `macros/00-bootstrap_params.FCMacro` |
| `SupportGenerator.FCStd` | Test-fixture Body + its generated `Fixture_Supports` |
| `workbench/SupportGenerator/` | The workbench addon, symlinked into FreeCAD's `Mod/` dir |
| `macros/` | This project's own macros (Params, fixture, add supports, export), `SG-` prefix in FreeCAD's Macro dir |
| `scripts/audit_parametric.py` | Parametric audit; run before every commit |
| `3mf/`, `stl/` | Print-ready exports (`SupportGenerator-Fixture.3mf`, `Fixture.stl`, `Fixture_Supports.stl`) |
| `gcode/` | Slicer output (gitignored) |
| `images/` | Screenshots and print photos |

## Usage

1. Close other projects' documents (another open `Params` document would capture the bindings),
   then open your project's `Params.FCStd` and the document holding your Body. Both must have been
   saved at least once.
2. Switch to the **SupportGenerator** workbench, select the Body → **Add Supports**. Any missing
   `Support*` Params are added to your project's VarSet first.
3. A `<Body>_Supports` object appears. It recomputes when the Body or Params change; check its
   `Warnings` property.
4. Select it (or the Body) → **Export Part + Supports (3MF)**. STLs are also written if the project
   has an `stl/` folder.
5. In the slicer: import the 3MF as two objects, slicer supports **off**, and **don't Arrange**
   (it would move the supports away from the part).
