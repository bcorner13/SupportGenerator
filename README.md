# SupportGenerator

A FreeCAD 1.1 workbench that generates **modeled, break-away print supports** for a selected
PartDesign Body: thin wedges with a small air gap to the part (0.25 × line width), output as a
**separate object**. Part and supports export together as a two-object 3MF, the slicer prints them
with its own supports off, and the supports snap away clean.

Inspired by *"Without a Trace: 3D Printed Supports That Remove Like Magic"*
(https://youtu.be/1Zocl7n98xY).

**Status:** scaffolded 2026-10-23. `plan.md` rev 2 (workbench) is awaiting approval. No code or geometry yet.

## Layout

| Path | Contents |
|---|---|
| `intent.md` / `plan.md` | Goal and the approved build plan |
| `Params.FCStd` | VarSet of generator settings (gap, wall thickness, overhang angle…) and test-fixture dimensions. Created by `macros/00-bootstrap_params.FCMacro` |
| `SupportGenerator.FCStd` | Test-fixture Body + generated `Supports` (after Phase 2) |
| `workbench/SupportGenerator/` | The workbench addon, symlinked into FreeCAD's `Mod/` dir |
| `macros/` | This project's own build macros (Params + test fixture), `SG-` prefix in FreeCAD's Macro dir |
| `scripts/audit_parametric.py` | Parametric audit; run before every commit |
| `3mf/`, `stl/` | Print-ready exports |
| `gcode/` | Slicer output (gitignored) |
| `images/` | Screenshots and print photos |

## Usage (once built)

1. Open `Params.FCStd` and the document holding your Body.
2. Switch to the **SupportGenerator** workbench, select the Body → **Add Supports**. Any missing
   `Support*` Params are added to your project's VarSet first.
3. A `Supports` object appears. It recomputes when the Body or Params change.
4. **Export Part + Supports (3MF)** → slice with slicer supports **off**.
