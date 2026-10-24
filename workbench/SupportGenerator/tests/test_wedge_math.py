#!/usr/bin/env python3
"""Unit tests for wedge_math (pure Python, no FreeCAD).

Run from anywhere:
    python3 workbench/SupportGenerator/tests/test_wedge_math.py

Results only count with the TEST ENVIRONMENT VERIFIED banner (PROJECT_BOOTSTRAP Step 8).

2D convention used throughout: a wedge lives in the vertical (s, z) plane, where s runs along
the face's horizontal "downhill" direction d. The 45-degree reference case is a part whose
sloped underside runs from (0, 0) up to (10, 10), with part material above-left of that line,
so the outward face normal is (+sqrt(1/2), -sqrt(1/2)) and the support sits below-right
(video reference image: images/video_ref_wedge_45deg_chamfered.png).
"""
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WB_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(WB_DIR))
sys.path.insert(0, WB_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from supportgen import wedge_math as wm  # noqa: E402

R = math.sqrt(0.5)
N45 = (R, -R)  # outward normal of the 45-degree reference face, in (s, z)
TOL = 1e-9


def default_params(**overrides):
    p = dict(
        gap=0.25,
        wedge_angle=45.0,
        plate_thick=2.0,
        max_slenderness=40.0,
        contact_land=0.84,
        chamfer_depth=3.0,
        tab_layers=1,
        tab_pitch=7.5,
        layer_height=0.2,
        line_width=0.42,
    )
    p.update(overrides)
    return wm.WedgeParams(**p)


def perp_dist_to_line(pt, a, b):
    """Distance from pt to the infinite line through a and b."""
    (x, y), (x1, y1), (x2, y2) = pt, a, b
    return abs((x2 - x1) * (y1 - y) - (x1 - x) * (y2 - y1)) / math.hypot(x2 - x1, y2 - y1)


def bed_length(profile, bed_z):
    xs = [s for s, z in profile if abs(z - bed_z) < 1e-9]
    return max(xs) - min(xs)


class TestNeedsSupport(unittest.TestCase):
    def test_level_underside(self):
        self.assertTrue(wm.needs_support((0, 0, -1), 45))

    def test_45_degree_underside_counts(self):
        self.assertTrue(wm.needs_support((R, 0, -R), 45))

    def test_steep_face_does_not(self):
        # 30 degrees from vertical: normal.z = -sin(30) = -0.5
        self.assertFalse(wm.needs_support((math.cos(math.radians(30)), 0, -0.5), 45))

    def test_vertical_wall_and_top_face_do_not(self):
        self.assertFalse(wm.needs_support((1, 0, 0), 45))
        self.assertFalse(wm.needs_support((0, 0, 1), 45))


class TestOffsetAndSlope(unittest.TestCase):
    def test_level_face_offsets_straight_down(self):
        lo, hi = wm.offset_segment((0, 17), (25, 17), (0, -1), 0.25)
        self.assertAlmostEqual(lo[1], 16.75)
        self.assertAlmostEqual(hi[1], 16.75)
        self.assertAlmostEqual(lo[0], 0)
        self.assertAlmostEqual(hi[0], 25)

    def test_gap_is_normal_to_45_face(self):
        lo, hi = wm.offset_segment((0, 0), (10, 10), N45, 0.25)
        for p in (lo, hi):
            self.assertAlmostEqual(perp_dist_to_line(p, (0, 0), (10, 10)), 0.25)

    def test_contact_slope(self):
        self.assertAlmostEqual(wm.contact_slope((0, 0), (10, 10)), math.radians(45))
        self.assertAlmostEqual(wm.contact_slope((0, 5), (10, 5)), 0.0)
        self.assertAlmostEqual(wm.contact_slope((10, 10), (0, 0)), math.radians(45))


class TestProfile(unittest.TestCase):
    def test_45_slope_is_right_triangle_base_equals_height(self):
        lo, hi = wm.offset_segment((0, 0), (10, 10), N45, 0.25)
        prof = wm.wedge_profile(lo, hi, bed_z=0.0, wedge_angle_deg=45)
        self.assertEqual(len(prof), 3)
        h = max(z for _, z in prof)
        self.assertAlmostEqual(bed_length(prof, 0.0), h)
        # hypotenuse stays exactly one gap off the part face
        for s, z in prof:
            if z > 1e-9:
                self.assertAlmostEqual(perp_dist_to_line((s, z), (0, 0), (10, 10)), 0.25)
        self.assertTrue(wm.footprint_ok(prof, 0.0, 45))

    def test_profile_is_ccw(self):
        lo, hi = wm.offset_segment((0, 0), (10, 10), N45, 0.25)
        prof = wm.wedge_profile(lo, hi, 0.0, 45)
        self.assertGreater(wm.signed_area(prof), 0)

    def test_level_ledge_flares_free_end_at_wedge_angle(self):
        lo, hi = wm.offset_segment((0, 17), (25, 17), (0, -1), 0.25)
        prof = wm.wedge_profile(lo, hi, 0.0, 45, flare_end="hi")
        self.assertEqual(len(prof), 4)
        self.assertAlmostEqual(bed_length(prof, 0.0), 25 + 16.75)
        self.assertTrue(wm.footprint_ok(prof, 0.0, 45))
        self.assertGreater(wm.signed_area(prof), 0)

    def test_level_ledge_flare_lo_goes_negative_s(self):
        lo, hi = wm.offset_segment((0, 17), (25, 17), (0, -1), 0.25)
        prof = wm.wedge_profile(lo, hi, 0.0, 45, flare_end="lo")
        self.assertAlmostEqual(min(s for s, _ in prof), -16.75)

    def test_raised_slope_gives_right_trapezoid(self):
        # sloped face that starts 5 mm above the bed: vertical leg at both ends
        lo, hi = wm.offset_segment((0, 5), (10, 15), N45, 0.25)
        prof = wm.wedge_profile(lo, hi, 0.0, 45)
        self.assertEqual(len(prof), 4)

    def test_footprint_fails_when_too_narrow(self):
        # a 60-degree contact over 2 mm of run at 45-deg rule: base 2 < height ~3.46
        prof = [(0, 0), (2, 0), (2, 2 * math.tan(math.radians(60)))]
        self.assertFalse(wm.footprint_ok(prof, 0.0, 45))


class TestThickness(unittest.TestCase):
    def test_short_wedge_keeps_plate_thick(self):
        self.assertAlmostEqual(wm.plate_thickness(20, 2.0, 40), 2.0)

    def test_tall_wedge_thickens(self):
        self.assertAlmostEqual(wm.plate_thickness(120, 2.0, 40), 3.0)

    def test_too_short(self):
        self.assertTrue(wm.too_short(0.5, 0.42))
        self.assertFalse(wm.too_short(0.9, 0.42))


class TestWedgeOffsets(unittest.TestCase):
    def test_fixture_depth_gives_three(self):
        offs = wm.wedge_offsets(20, plate_thick=2.0, gap=0.25, pitch=15)
        self.assertEqual(len(offs), 3)
        self.assertAlmostEqual(offs[0], -8.75)
        self.assertAlmostEqual(offs[1], 0.0)
        self.assertAlmostEqual(offs[2], 8.75)

    def test_spacing_never_exceeds_pitch(self):
        for width in (16, 20, 31, 47.5, 100):
            offs = wm.wedge_offsets(width, 2.0, 0.25, 15)
            gaps = [b - a for a, b in zip(offs, offs[1:])]
            self.assertTrue(all(g <= 15 + TOL for g in gaps), (width, gaps))

    def test_narrow_face_one_centered(self):
        self.assertEqual(wm.wedge_offsets(10, 2.0, 0.25, 15), [0.0])

    def test_face_narrower_than_plate_gets_none(self):
        self.assertEqual(wm.wedge_offsets(2.0, 2.0, 0.25, 15), [])


class TestTabs(unittest.TestCase):
    def test_minimum_two(self):
        self.assertEqual(wm.tab_positions(10, 7.5), [2.5, 7.5])

    def test_short_edge_still_two(self):
        pos = wm.tab_positions(7.5, 7.5)
        self.assertEqual(len(pos), 2)
        self.assertAlmostEqual(pos[0], 1.875)
        self.assertAlmostEqual(pos[1], 5.625)

    def test_long_edge_spacing_within_pitch(self):
        pos = wm.tab_positions(30, 7.5)
        self.assertEqual(len(pos), 4)
        self.assertEqual(pos, [3.75, 11.25, 18.75, 26.25])

    def test_tab_spans_exact_layers_on_45(self):
        th = math.radians(45)
        for layers in (1, 2):
            L = wm.tab_length(layers, 0.2, th, 0.42)
            self.assertAlmostEqual(L * math.sin(th), layers * 0.2)
        self.assertAlmostEqual(wm.tab_length(1, 0.2, th, 0.42), 0.2 / math.sin(th))  # 0.2828 mm

    def test_level_contact_falls_back_to_line_width(self):
        self.assertAlmostEqual(wm.tab_length(1, 0.2, 0.0, 0.42), 0.42)


class TestChamfer(unittest.TestCase):
    def test_depth_limited_by_profile(self):
        self.assertAlmostEqual(wm.effective_chamfer_depth(3.0, 0.84, 2.0, profile_min_dim=4.0), 2.0)
        self.assertAlmostEqual(wm.effective_chamfer_depth(3.0, 0.84, 2.0, profile_min_dim=20.0), 3.0)

    def test_no_chamfer_when_plate_not_wider_than_land(self):
        self.assertEqual(wm.effective_chamfer_depth(3.0, 0.84, 0.84, 20.0), 0.0)

    def test_halfwidth_ramps_land_to_plate(self):
        self.assertAlmostEqual(wm.chamfer_halfwidth(0.0, 2.0, 0.84, 3.0), 0.42)
        self.assertAlmostEqual(wm.chamfer_halfwidth(1.5, 2.0, 0.84, 3.0), 0.71)
        self.assertAlmostEqual(wm.chamfer_halfwidth(3.0, 2.0, 0.84, 3.0), 1.0)
        self.assertAlmostEqual(wm.chamfer_halfwidth(9.0, 2.0, 0.84, 3.0), 1.0)


class TestPlanWedge(unittest.TestCase):
    def test_45_reference_case(self):
        plan = wm.plan_wedge((0, 0), (10, 10), N45, 0.0, default_params())
        self.assertIsNone(plan.skipped)
        self.assertEqual(len(plan.profile), 3)
        self.assertAlmostEqual(plan.thickness, 2.0)
        self.assertAlmostEqual(plan.chamfer_depth, 3.0)
        self.assertEqual(len(plan.tabs), 2)  # contact ~13.9 mm, pitch 7.5 -> 2
        for pos, length in plan.tabs:
            self.assertAlmostEqual(length * math.sin(math.radians(45)), 0.2)
            self.assertTrue(0 < pos < plan.contact_length)

    def test_two_layer_tabs(self):
        plan = wm.plan_wedge((0, 0), (10, 10), N45, 0.0, default_params(tab_layers=2))
        for _, length in plan.tabs:
            self.assertAlmostEqual(length * math.sin(math.radians(45)), 0.4)

    def test_tall_slope_thickens(self):
        plan = wm.plan_wedge((0, 0), (150, 150), N45, 0.0, default_params())
        self.assertGreater(plan.thickness, 2.0)
        self.assertAlmostEqual(plan.thickness, max(p[1] for p in plan.profile) / 40)

    def test_short_wedge_skipped(self):
        plan = wm.plan_wedge((0, 0), (0.8, 0.8), N45, 0.0, default_params())
        self.assertIsNotNone(plan.skipped)

    def test_short_wedge_chamfer_shrinks(self):
        plan = wm.plan_wedge((0, 0), (3, 3), N45, 0.0, default_params())
        self.assertIsNone(plan.skipped)
        self.assertLess(plan.chamfer_depth, 3.0)

    def test_level_ledge_plan(self):
        plan = wm.plan_wedge((0, 17), (25, 17), (0, -1), 0.0, default_params(), flare_end="hi")
        self.assertIsNone(plan.skipped)
        self.assertEqual(len(plan.profile), 4)
        self.assertEqual(len(plan.tabs), 4)  # 25 mm / 7.5 -> ceil = 4
        for _, length in plan.tabs:
            self.assertAlmostEqual(length, 0.42)

    def test_invalid_tab_layers_rejected(self):
        with self.assertRaises(ValueError):
            wm.plan_wedge((0, 0), (10, 10), N45, 0.0, default_params(tab_layers=0))


def setUpModule():
    from test_env_guard import require_laptop
    print(require_laptop(need_freecad=False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
