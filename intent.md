# Intent — SupportGenerator

> Drafted by Claude 2026-10-23 from Bradley's answers in the kickoff session. This file is
> **human input** per PROJECT_BOOTSTRAP — edit it freely; plan.md follows from it.

Goal:
A FreeCAD macro that generates **modeled (CAD-designed) print supports** for a selected
PartDesign Body. The supports are separate solids with a deliberate air gap to the part, so they
snap off cleanly and leave no trace. The slicer prints them as ordinary model geometry, with slicer
supports turned off.

Starting point:
"Without a Trace: 3D Printed Supports That Remove Like Magic"
https://youtu.be/1Zocl7n98xY

Key points from the video (Bradley, 2026-10-23):

* Supports don't need to be thick to work. Use thin wedges.
* Gap between part and wedge = 0.25 × the layer width.
* Supports are a separate object from the part. The video exported STEP, then ran "Split to
  objects" in the slicer. Here, a two-object 3MF should do the same job.

Constraints:

* Must follow CAD_STANDARDS.md and the global parametric rules (~/.claude/CLAUDE.md).
* Generator settings (overhang angle, Z gap, XY gap, etc.) live in Params.FCStd and are
  bound by expression; there are no literals in the macro's output objects.
* Input: a selected PartDesign Body / solid. Mesh (STL) input is out of scope for v1.
* Generated supports must update on recompute when the Body or Params change. Re-running the
  macro is not the way to refresh them.
* Proven by a physical PLA test print of a fixture part before it is used on real projects.
