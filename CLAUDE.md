# Project rules — SupportGenerator

This project is a **tool**, not a single part. It's a FeaturePython support generator whose output
has to follow any Body it's pointed at. The main parametric risk is the generated `Supports`
object going **stale or literal**: a one-shot `Part::Feature`, a gap typed as `0.105` instead of
bound to `<<Params>>#VarSet.SupportGap`, or a proxy module that fails to load on reopen and leaves a
dead shape behind. Every generator input must be expression-bound, and every change must be proven
with a flex test (change the Param, recompute, re-measure).

> Source technique: *"Without a Trace: 3D Printed Supports That Remove Like Magic"*
> (https://youtu.be/1Zocl7n98xY). Claude cannot watch it, so the technique details come from
> Bradley's summary in `intent.md`. Don't invent "what the video says."

---

## Hard rules (this project)

1. **Everything parametric.** This covers the test-fixture sketch (bind every dimension to the
   `Fixture*` Params) and the `Supports` FeaturePython properties (`OverhangAngle`, `Gap`,
   `WallThick`, `Spacing`, `MinArea` → `<<Params>>#VarSet.*`). Literals in `support_generator.py`
   are limited to numeric tolerances, commented inline. No prior incident; this is a fresh project.

2. **No fixing geometry by editing raw sketch coordinates.** No prior incident in this project; rule
   applies preventively. A wrong support shape is fixed in the algorithm or a Param, never by
   hand-editing the generated shape.

3. **Attach sketches to datum planes, not feature faces.** No prior DAG incident; rule applies
   preventively. The fixture's `ProfileSketch` attaches to `XZ_Datum`.

4. **Clearance concepts stay decoupled.** Clearance Params in use:
   - `SupportGap` (= `LineWidth × SupportGapRatio`): air gap between the part and the support
     wedges, on every side. This is one interface (the support contact), so one Param. If a test
     print shows the top and side gaps need different values, split it into `SupportZGap` /
     `SupportXYGap`. Don't overload it.
   - No print-fit mating clearances; the fixture has no mating parts.

---

## Assembly architecture

There are two objects, and they are never fused:

- **Part**: any PartDesign Body (in this project, the `Fixture` Body: a Γ-shaped cantilever whose ledge
  underside is the overhang under test). It sits on the bed at its own ZMin.
- **Supports** (`Part::FeaturePython`): its `Source` links to the Part. It holds thin wedge plates
  standing on the same bed plane, their tops one `SupportGap` below each overhang face, and
  `SupportGap` clear of every part surface. It's a **separate object** so the slicer treats it as
  independent geometry (the video's "split to objects" step happens at export instead).
- Both are exported as two objects in one 3MF. Slicer supports are **off**.

---

## Files in this project

| File | Role | Depends on | Status |
|---|---|---|---|
| `Params.FCStd` | VarSet: generator + fixture Params | — | ⏳ not yet created (`macros/00-bootstrap_params.FCMacro`, Phase 1) |
| `SupportGenerator.FCStd` | Fixture Body + `Supports` | `Params.FCStd`, `macros/support_generator.py` | ⏳ not yet created (Phase 2–3) |

No broken files.

---

## Params variables (summary)

See `plan.md` → PARAMETERS. Groups:
- **Support:** `OverhangAngle`, `LineWidth`, `SupportGapRatio`, `SupportGap` (derived),
  `SupportWallThick` (derived, 2 × LineWidth), `SupportSpacing`, `MinOverhangArea`.
- **Fixture:** `FixtureColumnW`, `FixtureDepth`, `FixtureHeight`, `FixtureLedgeLen`, `FixtureLedgeThick`.

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

**Project-specific:**

- Macros are symlinked into `~/Library/Application Support/FreeCAD/v1-1/Macro/` with the
  **`SG-` prefix** (e.g. `SG-SupportGenerator.FCMacro`, `SG-support_generator.py`).
- `support_generator.py` is a **module**, not a macro. FeaturePython proxies pickle by module
  path, so renaming or moving it breaks every saved `Supports` object. Treat its name as an API.
- Whether FreeCAD's Macro dir is on `sys.path` at document load is **unverified** (plan.md Phase 0).
  Don't assume it is.
- The two-object 3MF → Creality Print import is **unverified** (plan.md Phase 4). If Creality merges
  the objects, see the CircleInlayRouterJig export macro for a custom 3MF writer.

---

## Print profile

**No successful test print yet — profile TBD.** Fill in after Phase 4. At minimum record: layer
height, line width (the gap derives from it), the gap ratio used, slicer supports off, and how
the supports broke away.
