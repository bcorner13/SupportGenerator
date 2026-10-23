# SupportGenerator

A FreeCAD 1.1 macro that generates **modeled, break-away print supports** for a selected
PartDesign Body: thin wedges with a small air gap to the part (0.25 × line width), output as a
**separate object**. Part and supports export together as a two-object 3MF, the slicer prints them
with its own supports off, and the supports snap away clean.

Inspired by *"Without a Trace: 3D Printed Supports That Remove Like Magic"*
(https://youtu.be/1Zocl7n98xY).

**Status:** scaffolded 2026-10-23. `plan.md` rev 1 is awaiting approval. No macros or geometry yet.

## Layout

| Path | Contents |
|---|---|
| `intent.md` / `plan.md` | Goal and the approved build plan |
| `Params.FCStd` | VarSet of generator settings (gap, wall thickness, overhang angle…) and test-fixture dimensions. Created by `macros/00-bootstrap_params.FCMacro` |
| `SupportGenerator.FCStd` | Test-fixture Body + generated `Supports` (after Phase 2) |
| `macros/` | Generator module + command macro, symlinked into FreeCAD's Macro dir with an `SG-` prefix |
| `scripts/audit_parametric.py` | Parametric audit; run before every commit |
| `3mf/`, `stl/` | Print-ready exports |
| `gcode/` | Slicer output (gitignored) |
| `images/` | Screenshots and print photos |

## Usage (once built)

1. Open `Params.FCStd` and the document holding your Body.
2. Select the Body → **Macro → Macros… → SG-SupportGenerator.FCMacro → Execute**.
3. A `Supports` object appears. It recomputes when the Body or Params change.
4. Export Body + Supports to 3MF, slice with slicer supports **off**.
