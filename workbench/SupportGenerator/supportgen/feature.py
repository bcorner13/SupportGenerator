"""Supports: Part::FeaturePython that builds break-away wedge supports for a Source Body.

FROZEN API: the proxy class paths `supportgen.feature.SupportFeature` and
`supportgen.feature.ViewProviderSupport` are saved inside every model file that has
supports. Don't rename the module or the classes; add a compatibility alias instead.

Geometry recipe: plan.md rev 4, WEDGE SIZING, and rev 5, INTERFACE DECK. The numbers come from wedge_math (pure
Python); this module only reads the B-rep, maps each wedge into its own (s, z) plane,
and turns the plans back into solids. Every numeric input is a feature property bound
to <<Params>>#VarSet.Support* (see params_schema.FEATURE_BINDINGS); the only literals
here are geometric tolerances, commented where used.
"""
import os
from collections import namedtuple

import FreeCAD as App
import Part

from . import params_schema as S
from . import wedge_math as wm

V = App.Vector
Z = V(0, 0, 1)

TOL = 1e-6        # length tolerance for vertex/plane tests, mm
BED_TOL = 1e-3    # a solid "stands on the bed" if its ZMin is within this, mm
OFFSET_TOL = 1e-3  # makeOffsetShape tolerance, mm (Phase 0 spike A)
OVERLAP = 0.01    # tabs reach this far into the land so they fuse solidly, mm
CUT_EXT = 0.05    # chamfer cutters overshoot the plate by this much, mm

# Rev 5 interface deck inputs: SupportDeckAngle (deg), SupportDeckThick, SupportDeckPitch (mm)
DeckSpec = namedtuple("DeckSpec", "angle thick pitch")
DECKS_OFF = 95.0  # deg; any deck angle > 90 means no decks (wedge_math.deck_needed)

_ICON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "Resources", "icons", "SupportGenerator.svg")


# --- reading the properties --------------------------------------------------------

def _val(x):
    return x.Value if hasattr(x, "Value") else x


def read_inputs(fp):
    """Feature properties -> (WedgeParams, overhang_angle, wedge_pitch, min_area, DeckSpec)."""
    g = {prop: _val(getattr(fp, prop)) for prop in S.FEATURE_BINDINGS}
    wp = wm.WedgeParams(
        gap=g["Gap"], wedge_angle=g["WedgeAngle"], plate_thick=g["PlateThick"],
        max_slenderness=g["MaxSlenderness"], contact_land=g["ContactLand"],
        chamfer_depth=g["ChamferDepth"], tab_layers=int(g["TabLayers"]),
        tab_pitch=g["TabPitch"], layer_height=g["LayerHeight"], line_width=g["LineWidth"])
    deck = DeckSpec(g["DeckAngle"], g["DeckThick"], g["DeckPitch"])
    return wp, g["OverhangAngle"], g["WedgePitch"], g["MinArea"], deck


# --- face analysis -----------------------------------------------------------------

def _face_normal(face):
    u0, u1, v0, v1 = face.ParameterRange
    return face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)  # respects orientation: outward


def overhang_faces(part, overhang_angle, min_area, bed_z):
    """[(face, outward normal)] for planar faces that need support, plus warnings."""
    found, warnings = [], []
    for i, face in enumerate(part.Faces):
        if face.BoundBox.ZMax <= bed_z + TOL:
            continue  # resting on the bed
        n = _face_normal(face)
        if not wm.needs_support((n.x, n.y, n.z), overhang_angle):
            continue
        if face.Area < min_area:
            continue
        if not isinstance(face.Surface, Part.Plane):
            warnings.append(f"Face{i + 1}: curved overhang skipped (planar faces only in v1)")
            continue
        found.append((i, face, n))
    return found, warnings


def face_frame(face, n):
    """(d, w): horizontal downhill direction and the horizontal direction across it.
    A level face has no downhill; use its longer bounding-box side (v1: axis-aligned)."""
    h = V(n.x, n.y, 0)
    if h.Length > TOL:
        d = h.normalize()
    else:
        bb = face.BoundBox
        d = V(1, 0, 0) if bb.XLength >= bb.YLength else V(0, 1, 0)
    return d, V(-d.y, d.x, 0)


def _section_points(face, w, offset):
    pts = []
    for wire in face.slice(w, offset):
        pts += [v.Point for v in wire.Vertexes]
    if len(pts) < 2:
        return None
    # the two section points farthest apart (a convex planar face gives exactly two)
    best = max(((a, b) for i, a in enumerate(pts) for b in pts[i + 1:]),
               key=lambda ab: (ab[0] - ab[1]).Length)
    return best if (best[0] - best[1]).Length > TOL else None


def _wall_at(part, end, other, n, reach):
    """True if part material sits just past `end` (away from `other`) on the support side."""
    along = end - other
    probe = end + along.normalize() * reach + n * reach
    return part.isInside(probe, TOL, True)


# --- solids ------------------------------------------------------------------------

def _to3d(s, z, d, w_at):
    return d * s + w_at + Z * z


def _plate(profile, d, w, c, t):
    w_at = w * (c - t / 2)
    pts = [_to3d(s, z, d, w_at) for s, z in profile]
    face = Part.Face(Part.makePolygon(pts + [pts[0]]))
    return face.extrude(w * t)


def _chamfer_cutters(a3, b3, u3, w, t, land, depth):
    """Two prisms that bevel the plate from t down to `land` over `depth` back from the
    contact edge a3-b3 (on the plate's mid-plane). u3 points from the edge into the plate."""
    edge = b3 - a3
    length = edge.Length
    e3 = V(edge).normalize()
    start = a3 - e3 * CUT_EXT
    out = []
    for side in (1, -1):
        def p(u, wv):
            return start + u3 * u + w * (side * wv)
        w_back = land / 2 - (t - land) / 2 * (CUT_EXT / depth)  # chamfer line at u = -CUT_EXT
        quad = [p(-CUT_EXT, w_back), p(depth, t / 2), p(depth, t / 2 + CUT_EXT),
                p(-CUT_EXT, t / 2 + CUT_EXT)]
        prof = Part.Face(Part.makePolygon(quad + [quad[0]]))
        out.append(prof.extrude(e3 * (length + 2 * CUT_EXT)))
    return out


def _tab(a3, e3, u3, w, pos, length, land, gap):
    """Box on the land: `land` across, `length` along the edge, from the land out to the
    part face (touching it) plus OVERLAP back into the land. a3 is on the mid-plane."""
    corner = a3 + e3 * (pos - length / 2) - u3 * gap - w * (land / 2)
    pts = [corner, corner + e3 * length, corner + e3 * length + w * land, corner + w * land]
    face = Part.Face(Part.makePolygon(pts + [pts[0]]))
    return face.extrude(u3 * (gap + OVERLAP))


def _fuse(shapes):
    if not shapes:
        return None
    return shapes[0].multiFuse(shapes[1:]) if len(shapes) > 1 else shapes[0]


def _deck_slab(face, n, gap, thick):
    """The face, moved `gap` out along its normal and extruded `thick` further (rev 5)."""
    slab = face.copy()
    slab.translate(n * gap)
    return slab.extrude(n * thick)


def build_supports(part, wp, overhang_angle, wedge_pitch, min_area, deck=None):
    """Build the supports for `part`. deck: DeckSpec, or None for rev 4 (no decks).

    Returns a dict: shape (compound of solids), plates (deck + plates after the clearance
    cut, no tabs), tabs, wedges (per-wedge records for validation), decks
    ([{tag, face, slab}]), warnings."""
    bed_z = part.BoundBox.ZMin
    faces, warnings = overhang_faces(part, overhang_angle, min_area, bed_z)
    plates, wedges, decks = [], [], []
    for fi, face, n in faces:
        is_deck = deck is not None and wm.deck_needed((n.x, n.y, n.z), deck.angle)
        if is_deck:
            decks.append({"tag": f"Face{fi + 1} deck", "face": fi + 1,
                          "slab": _deck_slab(face, n, wp.gap, deck.thick)})
            plates.append(decks[-1]["slab"])
            contact_offset = wm.deck_contact_offset(wp.gap, deck.thick, OVERLAP)
            pitch = deck.pitch
        else:
            contact_offset, pitch = None, wedge_pitch
        d, w = face_frame(face, n)
        n_dz = (n.dot(d), n.z)
        u3 = (d * n_dz[0] + Z * n_dz[1]).normalize()
        ws = [v.Point.dot(w) for v in face.Vertexes]
        wc = (min(ws) + max(ws)) / 2
        level = V(n.x, n.y, 0).Length < abs(n.z) * 1e-2  # within ~0.6 deg of level
        for off in wm.wedge_offsets(max(ws) - min(ws), wp.plate_thick, wp.gap, pitch):
            c = wc + off
            sec = _section_points(face, w, c)
            if sec is None:
                warnings.append(f"Face{fi + 1} @ {off:+.2f}: no section")
                continue
            p, q = sorted(sec, key=lambda v: (v.z, v.dot(d)))
            flare = None
            if level:
                walls = {"lo": _wall_at(part, p, q, n, 2 * wp.gap),
                         "hi": _wall_at(part, q, p, n, 2 * wp.gap)}
                free = [k for k, wall in walls.items() if not wall]
                flare = free[0] if len(free) == 1 else None
            plan = wm.plan_wedge((p.dot(d), p.z), (q.dot(d), q.z), n_dz, bed_z, wp, flare,
                                 contact_offset=contact_offset, chamfer=not is_deck)
            tag = f"Face{fi + 1} @ {off:+.2f}"
            if plan.skipped:
                warnings.append(f"{tag}: skipped, {plan.skipped}")
                continue
            warnings += [f"{tag}: {msg}" for msg in plan.warnings]
            solid = _plate(plan.profile, d, w, c, plan.thickness)
            (sa, za), (sb, zb) = plan.contact
            w_at = w * c
            a3, b3 = _to3d(sa, za, d, w_at), _to3d(sb, zb, d, w_at)
            if plan.chamfer_depth > 0:
                cutters = _chamfer_cutters(a3, b3, u3, w, plan.thickness,
                                           wp.contact_land, plan.chamfer_depth)
                solid = solid.cut(_fuse(cutters))
            plates.append(solid)
            # tabs stand on the contact surface SupportGap below the part: the plate land
            # (rev 4), or the deck top above a deck plate (rev 5)
            lift = u3 * (plan.contact_offset - wp.gap)
            wedges.append({"tag": tag, "plan": plan, "a3": a3, "b3": b3, "u3": u3,
                           "w": w, "c": c, "normal": n, "deck": is_deck,
                           "tab_a3": a3 - lift, "tab_b3": b3 - lift})
    if not plates:
        return {"shape": Part.Shape(), "plates": None, "tabs": [], "wedges": wedges,
                "decks": decks, "warnings": warnings or ["no faces need support"]}

    clearance = part.makeOffsetShape(wp.gap, OFFSET_TOL)
    cut = _fuse(plates).cut(clearance)
    kept = []
    for sol in cut.Solids:
        if sol.BoundBox.ZMin <= bed_z + BED_TOL:
            kept.append(sol)
        else:
            warnings.append(f"dropped a wedge piece not standing on the bed (ZMin "
                            f"{sol.BoundBox.ZMin:.2f}): support-on-part is Phase 6")
    if not kept:
        return {"shape": Part.Shape(), "plates": None, "tabs": [], "wedges": wedges,
                "decks": decks, "warnings": warnings + ["clearance cut removed every wedge"]}
    plates_shape = Part.makeCompound(kept)

    tabs = []
    for wd in wedges:
        e3 = V(wd["tab_b3"] - wd["tab_a3"]).normalize()
        for pos, length in wd["plan"].tabs:
            tab = _tab(wd["tab_a3"], e3, wd["u3"], wd["w"], pos, length,
                       wp.contact_land, wp.gap)
            if tab.common(plates_shape).Volume <= TOL:
                warnings.append(f"{wd['tag']}: tab at {pos:.2f} mm not on a kept wedge, dropped")
            elif tab.common(part).Volume > TOL:
                warnings.append(f"{wd['tag']}: tab at {pos:.2f} mm overlaps the part, dropped")
            else:
                tabs.append(tab)
    shape = plates_shape.multiFuse(tabs) if tabs else plates_shape
    shape = Part.makeCompound(shape.Solids)
    return {"shape": shape, "plates": plates_shape, "tabs": tabs, "wedges": wedges,
            "decks": decks, "warnings": warnings}


# --- FeaturePython -----------------------------------------------------------------

class SupportFeature:
    """Proxy for the Supports object. FROZEN class path: supportgen.feature.SupportFeature"""

    def __init__(self, obj):
        obj.Proxy = self
        self._add_properties(obj)

    @staticmethod
    def _add_properties(obj):
        have = obj.PropertiesList
        if "Source" not in have:
            obj.addProperty("App::PropertyLink", "Source", "Supports",
                            "Body to support (supports are a separate object, never fused to it)")
        for prop, pname in S.FEATURE_BINDINGS.items():
            if prop not in have:
                p = S.BY_NAME[pname]
                obj.addProperty(p.type, prop, "Params", f"{p.doc} (bound to {pname})")
        if "DeckAngle" not in have:
            # A rev 4 file gains the deck properties unbound (0). Deck angle 0 would deck
            # every face with thickness 0; keep decks off until Add Supports binds them.
            obj.DeckAngle = DECKS_OFF
        if "WedgeCount" not in have:
            obj.addProperty("App::PropertyInteger", "WedgeCount", "Result",
                            "Wedges built on the last recompute", 1)  # 1 = read-only
        if "DeckCount" not in have:
            obj.addProperty("App::PropertyInteger", "DeckCount", "Result",
                            "Interface decks built on the last recompute (rev 5)", 1)
        if "Warnings" not in have:
            obj.addProperty("App::PropertyStringList", "Warnings", "Result",
                            "Messages from the last recompute", 1)

    def onDocumentRestored(self, obj):
        self._add_properties(obj)  # files from older versions get any new properties

    def execute(self, obj):
        src = obj.Source
        if src is None or src.Shape.isNull() or not src.Shape.Solids:
            self._empty(obj, "Source is empty or has no solid")
            return
        wp, angle, pitch, min_area, deck = read_inputs(obj)
        try:
            res = build_supports(src.Shape, wp, angle, pitch, min_area, deck)
        except ValueError as e:  # e.g. TabLayers < 1, DeckThick too thin
            self._empty(obj, str(e))
            return
        obj.Shape = res["shape"]
        # rev 5: count planned plates, not solids (a deck fuses its plates into one solid)
        obj.WedgeCount = len(res["wedges"]) if not res["shape"].isNull() else 0
        obj.DeckCount = len(res["decks"]) if not res["shape"].isNull() else 0
        obj.Warnings = res["warnings"]
        for msg in res["warnings"]:
            App.Console.PrintWarning(f"Supports ({obj.Label}): {msg}\n")

    @staticmethod
    def _empty(obj, message):
        obj.Shape = Part.Shape()
        obj.WedgeCount = 0
        obj.DeckCount = 0
        obj.Warnings = [message]

    def dumps(self):
        return None

    def loads(self, state):
        return None

    __getstate__ = dumps
    __setstate__ = loads


class ViewProviderSupport:
    """FROZEN class path: supportgen.feature.ViewProviderSupport"""

    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = vobj.Object

    def getIcon(self):
        return _ICON

    def claimChildren(self):
        return []

    def dumps(self):
        return None

    def loads(self, state):
        return None

    __getstate__ = dumps
    __setstate__ = loads


# --- creation (used by the Add Supports command and project macros) ---------------

def find_supports(doc, source):
    for obj in doc.Objects:
        if getattr(obj, "Proxy", None).__class__.__name__ == "SupportFeature" \
                and getattr(obj, "Source", None) == source:
            return obj
    return None


def make_supports(source, varset):
    """Create (or re-bind) the Supports object for `source`, bound to `varset`'s Params.

    Both documents must already be saved: FreeCAD 1.1.4 refuses cross-document
    expressions otherwise ("Linked/Owner document not saved"). Doesn't save anything."""
    doc = source.Document
    for d, what in ((varset.Document, "the Params document"), (doc, f"'{doc.Label}'")):
        if not d.FileName:
            raise RuntimeError(f"Save {what} once first: cross-document bindings need both "
                               "files on disk.")
    obj = find_supports(doc, source)
    if obj is None:
        obj = doc.addObject("Part::FeaturePython", "Supports")
        SupportFeature(obj)
        obj.Label = f"{source.Label}_Supports"
        if App.GuiUp:
            ViewProviderSupport(obj.ViewObject)
            obj.ViewObject.ShapeColor = (0.95, 0.70, 0.24)  # support orange, matches the icon
    else:
        SupportFeature._add_properties(obj)  # an older Supports gains new Params properties
    obj.Source = source
    vdoc, vname = varset.Document.Label, varset.Name
    for prop, pname in S.FEATURE_BINDINGS.items():
        obj.setExpression(prop, S.binding_expression(pname, vdoc, vname))
    doc.recompute()
    return obj
