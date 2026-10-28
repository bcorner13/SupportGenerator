"""Wedge sizing math for SupportGenerator. Pure Python: NO FreeCAD imports.

Keep it that way so it stays unit-testable with plain python3
(tests/test_wedge_math.py); lives in the supportgen package. support_feature.py pulls the numbers out of the B-rep,
calls these functions, and turns the results back into solids.

2D convention: a wedge lives in a vertical plane with coordinates (s, z), where s
runs along the face's horizontal "downhill" direction d and z is world Z. Points are
(s, z) tuples. A face normal in this plane is (n_d, n_z) and points OUT of the part,
i.e. toward the support.

Design reference: plan.md rev 4, "WEDGE SIZING", and rev 5, "INTERFACE DECK". Every numeric input comes from
WedgeParams (bound to Params); the only literals here are numeric tolerances.
"""
import math
from dataclasses import dataclass, field

EPS = 1e-9  # geometric tolerance, mm
LEVEL_EPS_RAD = math.radians(1.0)  # contacts flatter than this are treated as level


@dataclass
class WedgeParams:
    gap: float              # SupportGap, mm, normal to the face
    wedge_angle: float      # SupportWedgeAngle, degrees
    plate_thick: float      # SupportPlateThick, mm
    max_slenderness: float  # SupportMaxSlenderness, height / thickness
    contact_land: float     # SupportContactLand, mm
    chamfer_depth: float    # SupportChamferDepth, mm
    tab_layers: int         # SupportTabLayers
    tab_pitch: float        # SupportTabPitch, mm
    layer_height: float     # LayerHeight, mm
    line_width: float       # LineWidth, mm


@dataclass
class WedgePlan:
    contact: tuple = None          # ((s, z), (s, z)) offset + bed-clipped contact segment
    contact_offset: float = 0.0    # how far the contact sits from the face, along n, mm
    profile: list = field(default_factory=list)  # CCW polygon in (s, z)
    thickness: float = 0.0         # plate thickness t, mm
    chamfer_depth: float = 0.0     # effective chamfer run-back, mm
    contact_length: float = 0.0    # mm along the contact segment
    height: float = 0.0            # wedge height above bed, mm
    tabs: list = field(default_factory=list)  # [(distance along contact from contact[0], length)]
    skipped: str = None            # reason, when no wedge should be built
    warnings: list = field(default_factory=list)


def needs_support(normal, overhang_angle_deg):
    """True if a face with this outward unit normal (x, y, z) leans at least
    overhang_angle_deg from vertical, i.e. normal.z <= -sin(angle)."""
    return normal[2] <= -math.sin(math.radians(overhang_angle_deg)) + 1e-6


def deck_needed(normal, deck_angle_deg):
    """True if a support face gets an interface deck (rev 5): it leans at least
    deck_angle_deg from vertical. Same test as needs_support; above 90 deg, never
    (checked explicitly: sin() is symmetric about 90, so 95 deg would act like 85)."""
    if deck_angle_deg > 90.0:
        return False
    return needs_support(normal, deck_angle_deg)


def deck_contact_offset(gap, deck_thick, overlap):
    """Offset, along the outward normal, of the plates' contact under a deck: they stop
    `overlap` inside the deck's underside so plates and deck fuse into one solid."""
    if deck_thick <= overlap + EPS:
        raise ValueError(f"SupportDeckThick must be > {overlap} mm, got {deck_thick}")
    return gap + deck_thick - overlap


def offset_segment(p_lo, p_hi, n_dz, gap):
    """Move a contact segment `gap` along the (normalized) outward face normal."""
    nd, nz = n_dz
    mag = math.hypot(nd, nz)
    nd, nz = nd / mag, nz / mag
    return ((p_lo[0] + gap * nd, p_lo[1] + gap * nz),
            (p_hi[0] + gap * nd, p_hi[1] + gap * nz))


def contact_slope(a, b):
    """Slope of segment a-b from horizontal, radians in [0, pi/2]."""
    return math.atan2(abs(b[1] - a[1]), abs(b[0] - a[0]))


def clip_to_bed(a, b, bed_z):
    """Trim the part of segment a-b that lies below the bed. None if all of it does."""
    za, zb = a[1] - bed_z, b[1] - bed_z
    if za < -EPS and zb < -EPS:
        return None
    if za >= -EPS and zb >= -EPS:
        return a, b
    t = za / (za - zb)  # parameter where the segment crosses the bed
    cross = (a[0] + t * (b[0] - a[0]), bed_z)
    return (cross, b) if za < 0 else (a, cross)


def signed_area(poly):
    return 0.5 * sum(x1 * y2 - x2 * y1
                     for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]))


def wedge_profile(p_lo, p_hi, bed_z, wedge_angle_deg, flare_end=None):
    """CCW polygon under the contact segment, down to the bed.

    Verticals drop from both contact ends (a sloped contact reaching the bed gives the
    video's right triangle). flare_end ("lo" / "hi", naming the argument, not the
    height) pushes that end's foot outward by h * cot(wedge_angle), giving a free
    hypotenuse. Used for level ledges, at the end away from the supporting wall.
    """
    seg = clip_to_bed(p_lo, p_hi, bed_z)
    if seg is None:
        return []
    a, b = seg
    cot = 1.0 / math.tan(math.radians(wedge_angle_deg))
    foot_a, foot_b = a[0], b[0]
    if flare_end == "lo":
        foot_a += math.copysign((a[1] - bed_z) * cot, a[0] - b[0])
    elif flare_end == "hi":
        foot_b += math.copysign((b[1] - bed_z) * cot, b[0] - a[0])
    poly = [(foot_a, bed_z), (foot_b, bed_z)]
    if b[1] - bed_z > EPS:
        poly.append(b)
    if a[1] - bed_z > EPS:
        poly.append(a)
    if signed_area(poly) < 0:
        poly.reverse()
    return poly


def _bed_length(profile, bed_z):
    xs = [s for s, z in profile if abs(z - bed_z) <= EPS]
    return max(xs) - min(xs) if xs else 0.0


def footprint_ok(profile, bed_z, wedge_angle_deg):
    """Base on the bed must be >= height * cot(wedge_angle) (at 45 deg: base >= height)."""
    h = max(z for _, z in profile) - bed_z
    need = h / math.tan(math.radians(wedge_angle_deg))
    return _bed_length(profile, bed_z) >= need - 1e-6


def plate_thickness(h_max, plate_thick, max_slenderness):
    return max(plate_thick, h_max / max_slenderness)


def too_short(h_max, line_width):
    """Below two line widths a wedge can't print; the slicer bridges the gap instead."""
    return h_max < 2 * line_width


def wedge_offsets(width, plate_thick, gap, pitch):
    """Offsets (along w, centered on the face) of the wedges across a face `width` wide.
    Spacing never exceeds `pitch`; one centered wedge when the face is narrow."""
    usable = width - 2 * (gap + plate_thick / 2)
    if usable < -EPS:
        return []
    if usable <= pitch + EPS:
        return [0.0]
    n = math.ceil(usable / pitch - EPS) + 1
    step = usable / (n - 1)
    return [-usable / 2 + i * step for i in range(n)]


def tab_positions(contact_len, pitch):
    """At least two tabs, evenly spaced (spacing <= pitch), half a space in from each end."""
    n = max(2, math.ceil(contact_len / pitch - EPS))
    step = contact_len / n
    return [(i + 0.5) * step for i in range(n)]


def tab_length(layers, layer_height, theta, line_width):
    """Tab length along the contact edge so its contact face spans exactly `layers`
    print layers in Z: layers * layer_height / sin(theta). Capped at `layers` line
    widths so near-level contacts don't grow long tabs; a level contact (no Z span to
    measure) gets that cap."""
    cap = layers * line_width
    if theta < LEVEL_EPS_RAD:
        return cap
    return min(layers * layer_height / math.sin(theta), cap)


def effective_chamfer_depth(depth, land, plate_thick, profile_min_dim):
    """Chamfer run-back, limited to half the wedge's smallest dimension. 0 if the
    plate is not wider than the land (nothing to bevel)."""
    if plate_thick <= land + EPS:
        return 0.0
    return min(depth, 0.5 * profile_min_dim)


def chamfer_halfwidth(u, plate_thick, land, depth):
    """Plate half-thickness at distance u back from the contact edge: ramps linearly
    from land/2 at the edge to plate_thick/2 at `depth`."""
    if depth <= 0 or u >= depth:
        return plate_thick / 2
    return land / 2 + (plate_thick - land) / 2 * (u / depth)


def plan_wedge(p_lo, p_hi, n_dz, bed_z, params, flare_end=None, contact_offset=None,
               chamfer=True):
    """Size one wedge under the face cross-section p_lo-p_hi (on the part surface).

    contact_offset: distance of the contact from the face along n (default params.gap,
    the rev 4 wedge). A plate under a rev 5 deck uses deck_contact_offset() and
    chamfer=False: full plate width into the deck, the break is the deck-to-part gap."""
    if params.tab_layers < 1:
        raise ValueError(f"SupportTabLayers must be >= 1, got {params.tab_layers}")
    plan = WedgePlan()
    plan.contact_offset = params.gap if contact_offset is None else contact_offset
    lo, hi = offset_segment(p_lo, p_hi, n_dz, plan.contact_offset)
    seg = clip_to_bed(lo, hi, bed_z)
    if seg is None:
        plan.skipped = "contact lies below the bed"
        return plan
    plan.contact = seg
    a, b = seg
    plan.height = max(a[1], b[1]) - bed_z
    if too_short(plan.height, params.line_width):
        plan.skipped = f"wedge height {plan.height:.3f} mm < 2 x LineWidth"
        return plan
    plan.thickness = plate_thickness(plan.height, params.plate_thick, params.max_slenderness)
    plan.profile = wedge_profile(a, b, bed_z, params.wedge_angle, flare_end)
    if not footprint_ok(plan.profile, bed_z, params.wedge_angle):
        plan.warnings.append("footprint shorter than height * cot(SupportWedgeAngle)")
    min_dim = min(_bed_length(plan.profile, bed_z), plan.height)
    if chamfer:
        plan.chamfer_depth = effective_chamfer_depth(
            params.chamfer_depth, params.contact_land, plan.thickness, min_dim)
    plan.contact_length = math.hypot(b[0] - a[0], b[1] - a[1])
    length = tab_length(params.tab_layers, params.layer_height,
                        contact_slope(a, b), params.line_width)
    plan.tabs = [(pos, length) for pos in tab_positions(plan.contact_length, params.tab_pitch)]
    return plan
