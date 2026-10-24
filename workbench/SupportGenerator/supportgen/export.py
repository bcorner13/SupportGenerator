"""Export a part and its Supports as two named objects in one 3MF (plus optional STLs).

The video exported STEP and used the slicer's "split to objects"; a 3MF with two
<object>s and two build <item>s gets there directly. Both are written in model (world)
coordinates with identity transforms, so their relative position is exact: the tabs
touch the part and the gap stays SupportGap. In the slicer, don't Arrange (it would
move the objects apart) and keep slicer supports off.

FreeCAD's own Mesh.export also writes separate objects, but unnamed and without a
read-back check, so this module writes the 3MF core-spec package itself.
"""
import math
import os
import re
import zipfile

import FreeCAD as App
import MeshPart

LINEAR_DEFLECTION = 0.01       # mm; mesh tolerance (planar faces are exact anyway)
ANGULAR_DEFLECTION_DEG = 5.0   # degrees; curved faces only
BED_TOL = 1e-3                 # mm; part and supports must stand on the same bed plane
EXTENT_TOL = 1e-4              # mm; read-back bounding box vs mesh

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
    ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
    ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
    '</Types>\n')
RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
    ' <Relationship Target="/3D/3dmodel.model" Id="rel0" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
    '</Relationships>\n')
MODEL_ENTRY = "3D/3dmodel.model"


def _fmt(x):
    s = f"{x:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _xml_attr(text):
    return (text.replace("&", "&amp;").replace('"', "&quot;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def mesh_shape(shape):
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=LINEAR_DEFLECTION,
                                  AngularDeflection=math.radians(ANGULAR_DEFLECTION_DEG),
                                  Relative=False)
    if not mesh.isSolid() or mesh.hasNonManifolds():
        raise RuntimeError("mesh is not a closed manifold solid")
    return mesh


def write_3mf(path, named_meshes):
    """named_meshes: [(name, Mesh.Mesh)]. One <object> + one <item> per mesh."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n'
           '<model unit="millimeter" xml:lang="en-US" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
           ' <metadata name="Application">FreeCAD SupportGenerator</metadata>\n <resources>\n']
    for oid, (name, mesh) in enumerate(named_meshes, start=1):
        points, facets = mesh.Topology
        out.append(f'  <object id="{oid}" name="{_xml_attr(name)}" type="model">\n'
                   '   <mesh>\n    <vertices>\n')
        out += [f'     <vertex x="{_fmt(p.x)}" y="{_fmt(p.y)}" z="{_fmt(p.z)}"/>\n' for p in points]
        out.append('    </vertices>\n    <triangles>\n')
        out += [f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n' for a, b, c in facets]
        out.append('    </triangles>\n   </mesh>\n  </object>\n')
    out.append(' </resources>\n <build>\n')
    out += [f'  <item objectid="{oid}"/>\n' for oid in range(1, len(named_meshes) + 1)]
    out.append(' </build>\n</model>\n')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr(MODEL_ENTRY, "".join(out))


def verify_3mf(path, named_meshes):
    """Read the file back: names, vertex/triangle counts and bounding boxes per object."""
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise RuntimeError("3MF failed the zip CRC check")
        model = z.read(MODEL_ENTRY).decode("utf-8")
    blocks = re.findall(r'<object id="(\d+)" name="([^"]*)" type="model">(.*?)</object>', model, re.S)
    if len(blocks) != len(named_meshes) or model.count("<item ") != len(named_meshes):
        raise RuntimeError(f"3MF has {len(blocks)} objects, expected {len(named_meshes)}")
    report = []
    for (oid, name, body), (want_name, mesh) in zip(blocks, named_meshes):
        verts = [tuple(float(c) for c in m) for m in
                 re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"/>', body)]
        if name != _xml_attr(want_name):
            raise RuntimeError(f"object {oid} is named {name!r}, expected {want_name!r}")
        if len(verts) != mesh.CountPoints or body.count("<triangle ") != mesh.CountFacets:
            raise RuntimeError(f"object {name}: vertex/triangle count mismatch")
        bb = mesh.BoundBox
        for axis, (lo, hi) in enumerate(((bb.XMin, bb.XMax), (bb.YMin, bb.YMax), (bb.ZMin, bb.ZMax))):
            vals = [v[axis] for v in verts]
            if abs(min(vals) - lo) > EXTENT_TOL or abs(max(vals) - hi) > EXTENT_TOL:
                raise RuntimeError(f"object {name}: extent wrong on axis {'XYZ'[axis]}")
        report.append({"name": name, "vertices": len(verts), "triangles": mesh.CountFacets})
    return report


def export_part_and_supports(supports, path_3mf, stl_dir=None):
    """Pre-flight, mesh, write and verify. Returns a report dict. Doesn't save documents."""
    part = supports.Source
    problems = []
    if part is None:
        problems.append("Supports has no Source")
    else:
        if not part.Shape.isValid() or not part.Shape.Solids:
            problems.append(f"{part.Label} is not a valid solid")
        if supports.Shape.isNull() or not supports.Shape.Solids:
            problems.append(f"{supports.Label} is empty")
        elif abs(supports.Shape.BoundBox.ZMin - part.Shape.BoundBox.ZMin) > BED_TOL:
            problems.append("part and supports don't stand on the same bed plane")
    for obj in (o for o in (part, supports) if o is not None):
        bad = set(obj.State) & {"Invalid", "Error", "Touched"}
        if bad:
            problems.append(f"{obj.Label} is {sorted(bad)}: recompute first")
    if problems:
        raise RuntimeError("; ".join(problems))

    named = [(part.Label, mesh_shape(part.Shape)), (supports.Label, mesh_shape(supports.Shape))]
    os.makedirs(os.path.dirname(path_3mf), exist_ok=True)
    write_3mf(path_3mf, named)
    report = {"3mf": path_3mf, "objects": verify_3mf(path_3mf, named), "stl": []}
    if stl_dir:
        os.makedirs(stl_dir, exist_ok=True)
        for name, mesh in named:
            p = os.path.join(stl_dir, f"{name}.stl")
            mesh.write(p)
            report["stl"].append(p)
    return report
