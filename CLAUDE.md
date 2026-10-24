# Project rules — SupportGenerator

This project is a **tool**, not a single part. It's a FreeCAD **workbench** (`workbench/SupportGenerator/`,
symlinked into `Mod/`) whose FeaturePython `Supports` object
has to follow any Body it's pointed at. The main parametric risk is the generated `Supports`
object going **stale or literal**: a one-shot `Part::Feature`, a gap typed as `0.25` instead of
bound to `<<Params>>#VarSet.SupportGap`, or a proxy module that fails to load on reopen and leaves a
dead shape behind. Every generator input must be expression-bound, and every change must be proven
with a flex test (change the Param, recompute, re-measure).

> Source technique: *"Without a Trace: 3D Printed Supports That Remove Like Magic"*
> (https://youtu.be/1Zocl7n98xY). Claude cannot watch it, so the technique details come from
> Bradley's summary in `intent.md` and his video screenshots (described in plan.md rev 4). Don't
> invent "what the video says."

---

## Hard rules (this project)

1. **Everything parametric.** This covers the test-fixture sketch (bind every dimension to the
   `Fixture*` Params) and every `Supports` FeaturePython input property, each bound to its
   `<<Params>>#VarSet.*` variable (full list: plan.md → PARAMETERS → Generator). Workbench code may
   contain only the tool defaults in `params_schema.py` and numeric tolerances, both commented inline.
   Wedge *sizing* (plate thickness, triangle profile, chamfer, tab length from layer count, wedge and
   tab counts) is computed in `wedge_math.py` from those Params, never hard-coded. No prior incident; this is a fresh project.

2. **No fixing geometry by editing raw sketch coordinates.** No prior incident in this project; rule
   applies preventively. A wrong support shape is fixed in the algorithm or a Param, never by
   hand-editing the generated shape.

3. **Attach sketches to datum planes, not feature faces.** No prior DAG incident; rule applies
   preventively. The fixture's `ProfileSketch` attaches to `XZ_Datum`.

4. **Clearance concepts stay decoupled.** Clearance Params in use:
   - `SupportGap` (0.25 mm absolute, normal to the face, per the video sketch): air gap between the
     part and the support wedges' contact land, on every side. The tabs bridge it. It was briefly
     0.25 × layer height (0.05 mm) on 2026-10-23, but that's below slicer resolution and would fuse the
     whole edge. Don't go back to a ratio without a test print showing it works. This is one interface (the support contact), so one Param. If a test
     print shows the top and side gaps need different values, split it into `SupportZGap` /
     `SupportXYGap`. Don't overload it.
   - No print-fit mating clearances; the fixture has no mating parts.

---

## Assembly architecture

There are two objects, and they are never fused:

- **Part**: any PartDesign Body (in this project, the `Fixture` Body: a Γ-shaped cantilever whose ledge
  underside is the overhang under test). It sits on the bed at its own ZMin.
- **Supports** (`Part::FeaturePython`): its `Source` links to the Part. It holds 45° right-triangle wedge plates, each with a heavily chamfered contact edge
  (narrow land) running one `SupportGap` below the overhang face, standing on the same bed plane and
  `SupportGap` clear of every part surface. Small **rectangular tabs** (1–2 layers tall, 5–10 mm apart)
  on the land bridge the gap and **touch** the part (zero gap, zero overlap). They're the only contact. It's a **separate object** so the slicer treats it as
  independent geometry (the video's "split to objects" step happens at export instead).
- Both are exported as two objects in one 3MF. Slicer supports are **off**.

---

## Files in this project

| File | Role | Depends on | Status |
|---|---|---|---|
| `Params.FCStd` | VarSet: generator + fixture Params | — | ⏳ not yet created (`macros/00-bootstrap_params.FCMacro`, Phase 1) |
| `SupportGenerator.FCStd` | Fixture Body + `Supports` | `Params.FCStd`, the SupportGenerator workbench | ⏳ not yet created (Phase 2–4) |

No broken files.

---

## Params variables (summary)

See `plan.md` → PARAMETERS. Groups:
- **Support:** `OverhangAngle`, `LineWidth`, `LayerHeight`, `SupportGap`, `SupportWedgeAngle`,
  `SupportPlateThick`, `SupportMaxSlenderness`, `SupportContactLand` (derived, 2 × LineWidth),
  `SupportChamferDepth`, `SupportWedgePitch`, `SupportTabLayers`, `SupportTabPitch`, `MinOverhangArea`.
- **Fixture:** `FixtureColumnW`, `FixtureDepth`, `FixtureHeight`, `FixtureLedgeLen`, `FixtureLedgeThick`, `FixtureSlopeAngle`.

Run `python3 scripts/audit_parametric.py` to check bindings.

---

## How to verify your change didn't break parametric

After any FreeCAD edit, before considering the task done:

```bash
python3 scripts/audit_parametric.py
```

This script flags:
- Sketches with 0 constraints
- Sketches with dimensional constraints lacking expression bindings
- Sketches attached to feature faces (DAG risk)
- Params variables used nowhere (dead Params)

The script is authoritative. If it reports violations, fix them via a `macros/*.FCMacro` change before saving or committing — never by direct coordinate edits or FCStd XML surgery.

No exemptions; audit must be clean. Note that the audit **does not see FeaturePython properties**
the way it sees Pad/Pocket dims, and it doesn't check them. So the `Supports` bindings are verified
by plan.md VALIDATION step 5 (flex test), not by the audit. This copy of the script comes from
MagicCardBox (constraint-type and Pad/Pocket enum fixes) and adds `Diameter`/`Depth` to the
feature-dim list (the Hole blind spot).

---

## Memory files (deeper context)

`~/.claude/projects/-Users-bradleycorner-Documents-3dPrinting-Commercial-License-SupportGenerator/memory/MEMORY.md` indexes the persistent memories for this project. If you're unsure *why* a rule exists, read those files first — they trace each rule to a concrete past incident.

No project-scoped memories yet — this is a fresh project. Relevant global ones:
`reference_printinplace_verify_by_distance.md` (check gaps with `distToShape`, never
`common().Volume`) and `reference_audit_parametric_type_bug.md`.

---

## Workflow notes

**Invariant (apply to every FreeCAD project — do not edit):**

- **Inspect/edit FreeCAD models via the MCP bridge — never with shell tools.** Do **not** `unzip`/`grep`/`cat`/`sed`/`strings`/etc. a `.FCStd`. Use the FreeCAD Robust MCP server: `get_connection_status` first, then `open_document`, `list_objects`, `inspect_object`, `execute_python`, and macros. This is **enforced** by a PreToolUse hook in `.claude/settings.json` (copied from the root `settings.template.json` during bootstrap) — raw shell access to `.FCStd` is blocked. Only fall back to read-only `unzip` if the MCP bridge is genuinely unreachable, and ask the user first.
- **MCP server auto-starts with FreeCAD.** If an `mcp__freecad__*` call fails, the right interpretation is "FreeCAD isn't running" — ask whether to launch it. Do **not** silently fall back to `unzip` + XML parsing, and do **not** retry the same MCP call.
- **Write changes as `macros/*.FCMacro` files**, not direct XML edits. Reasons: reviewable, re-runnable, idempotent-friendly, uses FreeCAD's own serialization.
- **Cross-document expressions**: use the canonical form `<<Params>>#VarSet.VarName`. The shorter `<<Params>>.VarName` form sometimes fails with "Params not found."
- **Run `python3 scripts/audit_parametric.py` before committing.** If it reports violations, fix via macro, not by editing FCStd XML.
- **Stop means stop; only Bradley's laptop counts.** If the laptop's FreeCAD or MCP bridge is unreachable, the plan isn't approved, or required files are missing, the task is **blocked**: report it with the evidence and end the turn. Do not install, download, or run any other FreeCAD, MCP server, VM, sandbox, or headless instance, or take any other route to the result not described here, including routes this file doesn't mention. Every validation run (FreeCAD checks, sweeps, audit) calls `require_laptop()` from `scripts/test_env_guard.py` first and quotes its banner. A result without a `TEST ENVIRONMENT VERIFIED` banner is **invalid**, not partial evidence, and must never be reported as passing. Never edit, stub, or bypass the guard, and never run `--enroll`; only Bradley enrolls the machine.

**Project-specific:**

- **Workbench, not macro.** Source is `workbench/SupportGenerator/`, symlinked to
  `~/Library/Application Support/FreeCAD/v1-1/Mod/SupportGenerator`. Changes to it need a FreeCAD
  restart. Project `macros/` (`SG-` prefix in FreeCAD's Macro dir) only build *this project's*
  Params and fixture.
- `InitGui.py` is a **stub loader** that execs `supportgen/gui.py` with an explicit namespace. Don't put
  workbench code in `InitGui.py` (see global memory `feedback_freecad_initgui_exec.md`).
- **Frozen API:** the proxy path `supportgen.feature.SupportFeature` is saved inside every model file
  that uses supports. Renaming the module or class breaks those files. Add a compatibility alias
  rather than renaming.
- **Settings are per project:** *Ensure Support Params* adds `Support*` variables to whichever
  project's `Params` VarSet is open. Don't point another project's supports at this project's Params.
- `wedge_math.py` has **no FreeCAD imports**, so it's testable with plain `python3`. Keep it that way.
- The two-object 3MF → Creality Print import is **unverified** (plan.md Phase 5). If Creality merges
  the objects, see the CircleInlayRouterJig export macro for a custom 3MF writer.

---

## Print profile

**No successful test print yet — profile TBD.** Fill in after Phase 4. At minimum record: layer
height, line width (the gap derives from it), the gap ratio used, slicer supports off, and how
the supports broke away.
