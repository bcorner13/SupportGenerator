#!/usr/bin/env python3
"""Audit all FCStd files in the project for parametric integrity.

Flags:
  - Sketches with zero constraints (unconstrained geometry)
  - Sketches with dimensional constraints that lack expression bindings
  - Sketches attached to feature faces (DAG-cycle risk)
  - Features with Length/Offset/Radius/etc. set to a literal number rather than an expression

Run from the project root:
    python3 scripts/audit_parametric.py

Exit code 0 = clean. Non-zero = violations found.

Intended for manual pre-commit use. Can also be wired as a pre-commit hook.
"""
import os
import re
import sys
import tempfile
import zipfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Constraint Types that are "dimensional" (i.e. driven by a numeric value) and
# therefore need expression bindings.
#
# CORRECTED 2026-06-04 for the Clocks project: the canonical copy of this script
# carried a WRONG enum mapping (it labeled 5=ParallelDistance, 9=Radius, 10=Angle,
# 17=Diameter, 18=Weight). That misclassified geometric constraints — Tangent(5),
# Perpendicular(10), Block(17) — as unbound dimensions (false positives) and missed
# real Radius(11)/Diameter(18). Verified empirically against the live Sketcher API
# (XML Type integers align 1:1 with o.Constraints[i].Type). The values below match
# FreeCAD's Sketcher Constraint.h enum:
#   0 None 1 Coincident 2 Horizontal 3 Vertical 4 Parallel 5 Tangent 6 Distance
#   7 DistanceX 8 DistanceY 9 Angle 10 Perpendicular 11 Radius 12 Equal
#   13 PointOnObject 14 Symmetric 15 InternalAlignment 16 SnellsLaw 17 Block
#   18 Diameter 19 Weight
# Weight(19) is a B-spline control-point weight — NOT a user dimension — and is
# intentionally excluded (documented exemption).
DIMENSIONAL_TYPES = {
    6: "Distance",
    7: "DistanceX",
    8: "DistanceY",
    9: "Angle",
    11: "Radius",
    18: "Diameter",
}

# Angle constraints at exactly 90 degrees are perpendicularity expressed as an angle;
# they are geometric, not design dimensions. Exempt (matches the Weight exemption).
RIGHT_ANGLE_RAD = 1.5707963267948966

# PartDesign Pad/Pocket Type enum. The inherited table here was WRONG and produced a
# false positive the moment a feature used Type index 1. Verified empirically against
# FreeCAD 1.1.3 on 2026-09-13 via getEnumerationsOfProperty("Type"):
#
#   Pad:    0 Length, 1 UpToLast,   2 UpToFirst, 3 UpToFace, 4 TwoLengths, 5 UpToShape
#   Pocket: 0 Length, 1 ThroughAll, 2 UpToFirst, 3 UpToFace, 4 TwoLengths, 5 UpToShape
#
# Two errors in the old table: it claimed TwoLengths was index 1 (it is 4), and it
# assumed Pad and Pocket share an enum (they differ at index 1 — UpToLast vs ThroughAll).
# Effect: a Pocket with Type=ThroughAll (index 1) was read as TwoLengths, so its inert
# Length/Length2 were reported as unbound dimensions. Same family of defect as the
# DIMENSIONAL_TYPES bug — see the reference_audit_parametric_type_bug memory.
#
# Length is only active for Length(0) and TwoLengths(4); Length2 only for TwoLengths(4).
# Conveniently the active sets coincide for Pad and Pocket, so one pair still suffices.
LENGTH_ACTIVE_TYPES = {0, 4}
LENGTH2_ACTIVE_TYPES = {4}


def extract_xml(fcstd_path):
    """Return Document.xml contents of the FCStd ZIP."""
    with zipfile.ZipFile(fcstd_path) as z:
        with z.open("Document.xml") as f:
            return f.read().decode("utf-8")


def find_sketches(xml):
    """Return list of sketch names in the document."""
    return re.findall(r'<Object type="Sketcher::SketchObject" name="(\w+)"', xml)


def get_object(xml, name):
    m = re.search(rf'<Object name="{name}"[^/]*(?:Extensions="True")?>.*?</Object>', xml, re.S)
    return m.group(0) if m else None


def audit_sketch(xml, name):
    issues = []
    body = get_object(xml, name)
    if body is None:
        return [f"[internal] cannot find object body for {name}"]

    cl = re.search(r'<ConstraintList count="(\d+)">(.*?)</ConstraintList>', body, re.S)
    ee = re.search(r'<ExpressionEngine count="(\d+)"[^>]*>(.*?)</ExpressionEngine>', body, re.S)
    fc = re.search(r'<Property name="FullyConstrained"[^>]*>\s*<Bool value="(\w+)"', body)
    attach = re.search(r'AttachmentSupport".*?<Link obj="(\w+)" sub="([^"]*)"', body, re.S)

    cl_count = int(cl.group(1)) if cl else 0
    fully = fc.group(1) == "true" if fc else False

    if cl_count == 0:
        issues.append(f"  UNCONSTRAINED: {name} has 0 constraints")
    elif not fully:
        issues.append(f"  UNDERCONSTRAINED: {name} has {cl_count} constraints but FullyConstrained=false")

    # For dimensional constraints, check that they're bound by expression
    if cl:
        # Index of each dimensional constraint. Enumerate EVERY <Constrain> element so
        # the enumeration index matches the live o.Constraints[i] index 1:1.
        dim_indices = []
        for idx, c in enumerate(re.finditer(r'<Constrain\b([^>]*?)/>', cl.group(2))):
            attrs = c.group(1)
            tm = re.search(r'\bType="(\d+)"', attrs)
            t = int(tm.group(1)) if tm else -1
            if t not in DIMENSIONAL_TYPES:
                continue
            if t == 9:  # Angle — exempt exact 90deg (perpendicularity)
                vm = re.search(r'\bValue="([-\d.eE]+)"', attrs)
                if vm and abs(abs(float(vm.group(1))) - RIGHT_ANGLE_RAD) < 1e-3:
                    continue
            dim_indices.append((idx, DIMENSIONAL_TYPES[t]))

        # Which indices have expression bindings?
        bound_indices = set()
        if ee:
            for m in re.finditer(r'<Expression path="Constraints\[(\d+)\]"', ee.group(2)):
                bound_indices.add(int(m.group(1)))

        for idx, tname in dim_indices:
            if idx not in bound_indices:
                issues.append(f"  UNBOUND DIMENSION: {name}.Constraints[{idx}] is {tname} but has no expression binding — value is a literal number")

    # Attachment DAG risk — sketch attached to feature face (Pocket_/Pad_/Body_ + .FaceN)
    if attach:
        obj, sub = attach.group(1), attach.group(2)
        is_datum = "Plane" in obj or "Axis" in obj or "Origin" in obj
        is_feature_face = bool(re.match(r'Face\d+$', sub or ""))
        if is_feature_face and not is_datum:
            issues.append(f"  DAG RISK: {name} attached to feature face {obj}.{sub} — use a datum plane instead")

    return issues


def audit_feature_dimensions(xml):
    """Check Pad/Pocket/Chamfer/Fillet etc. numeric properties for expression bindings.

    Type-aware: a Pad/Pocket's Length is inert unless Type is Length/TwoLengths, and
    Length2 is inert unless Type is TwoLengths. Inert dims are skipped — flagging them
    would demand a meaningless Param (see LENGTH_ACTIVE_TYPES)."""
    issues = []
    for type_name in ["PartDesign::Pad", "PartDesign::Pocket", "PartDesign::Chamfer", "PartDesign::Fillet"]:
        is_pad_pocket = type_name in ("PartDesign::Pad", "PartDesign::Pocket")
        for name in re.findall(rf'<Object type="{type_name}" name="(\w+)"', xml):
            body = get_object(xml, name)
            if body is None:
                continue
            ee = re.search(r'<ExpressionEngine count="(\d+)"[^>]*>(.*?)</ExpressionEngine>', body, re.S)
            bound_paths = set()
            if ee:
                for m in re.finditer(r'<Expression path="([^"]+)"', ee.group(2)):
                    bound_paths.add(m.group(1))

            # Determine which length props are active for this feature.
            ptype = None
            if is_pad_pocket:
                tm = re.search(r'<Property name="Type"[^>]*>\s*<Integer value="(\d+)"', body)
                ptype = int(tm.group(1)) if tm else 0

            for prop in ["Length", "Length2", "Radius", "Offset", "Size", "Diameter", "Depth"]:  # Diameter/Depth: PartDesign::Hole (was unaudited)
                if is_pad_pocket and prop == "Length" and ptype not in LENGTH_ACTIVE_TYPES:
                    continue
                if is_pad_pocket and prop == "Length2" and ptype not in LENGTH2_ACTIVE_TYPES:
                    continue
                p = re.search(rf'<Property name="{prop}"[^>]*>\s*<Float value="([-\d.]+)"', body)
                if p and abs(float(p.group(1))) > 1e-9:
                    if prop not in bound_paths:
                        issues.append(f"  UNBOUND FEATURE DIM: {name}.{prop} = {p.group(1)} has no expression binding")
    return issues


def main():
    # Results only count from Bradley's laptop; see test_env_guard.py.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from test_env_guard import InvalidTestEnvironment, require_laptop
    try:
        print(require_laptop(need_freecad=False))
    except InvalidTestEnvironment as e:
        print(e)
        return 2

    fcstd_files = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # skip venv/git/etc
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "node_modules", "files")]
        for f in files:
            if f.endswith(".FCStd") and not f.endswith(".FCBak"):
                # skip session snapshots
                if "Session-" in f:
                    continue
                fcstd_files.append(os.path.join(root, f))

    total_issues = 0
    for path in sorted(fcstd_files):
        rel = os.path.relpath(path, PROJECT_ROOT)
        try:
            xml = extract_xml(path)
        except Exception as e:
            print(f"[skip] {rel} (unreadable: {e})")
            continue

        file_issues = []
        for name in find_sketches(xml):
            file_issues.extend(audit_sketch(xml, name))
        file_issues.extend(audit_feature_dimensions(xml))

        if file_issues:
            print(f"\n=== {rel} — {len(file_issues)} issue(s) ===")
            for iss in file_issues:
                print(iss)
            total_issues += len(file_issues)
        else:
            print(f"OK  {rel}")

    print(f"\n{'=' * 60}")
    if total_issues == 0:
        print("✓ All files pass parametric audit.")
        return 0
    print(f"✗ {total_issues} parametric issue(s) across project.")
    print("Fix these before considering any geometry task complete.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
