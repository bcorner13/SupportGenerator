#!/usr/bin/env python3
"""Unit tests for supportgen.params_schema (pure Python, no FreeCAD).

    python3 workbench/SupportGenerator/tests/test_params_schema.py

Results only count with the TEST ENVIRONMENT VERIFIED banner (PROJECT_BOOTSTRAP Step 8).
"""
import dataclasses
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WB_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(WB_DIR))
sys.path.insert(0, WB_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from supportgen import params_schema as S  # noqa: E402
from supportgen import wedge_math as wm  # noqa: E402

VALID_TYPES = {"App::PropertyAngle", "App::PropertyLength", "App::PropertyFloat",
               "App::PropertyInteger", "App::PropertyArea"}


class TestSchema(unittest.TestCase):
    def test_names_unique_and_prefixed(self):
        names = [p.name for p in S.PARAMS]
        self.assertEqual(len(names), len(set(names)))
        for n in names:
            self.assertTrue(n.startswith("Support"), n)

    def test_types_valid(self):
        for p in S.PARAMS:
            self.assertIn(p.type, VALID_TYPES, p.name)

    def test_exactly_one_of_default_or_expression(self):
        for p in S.PARAMS:
            self.assertTrue((p.default is None) != (p.expression is None), p.name)

    def test_expressions_reference_only_earlier_params(self):
        seen = set()
        for p in S.PARAMS:
            if p.expression:
                for ident in re.findall(r"[A-Za-z_]\w*", p.expression):
                    self.assertIn(ident, seen, f"{p.name} references {ident} before it exists")
            seen.add(p.name)

    def test_plan_rev4_defaults(self):
        d = {p.name: p.default for p in S.PARAMS}
        self.assertEqual(d["SupportGap"], 0.25)
        self.assertEqual(d["SupportTabLayers"], 1)
        self.assertEqual(d["SupportTabPitch"], 7.5)
        self.assertEqual(d["SupportPlateThick"], 2.0)
        self.assertEqual(S.BY_NAME["SupportContactLand"].expression, "SupportLineWidth * 2")

    def test_feature_bindings_cover_every_param_once(self):
        self.assertEqual(sorted(S.FEATURE_BINDINGS.values()), sorted(S.BY_NAME))

    def test_bindings_feed_every_wedge_param(self):
        # every WedgeParams field must be fed by some Supports property
        wedge_fields = {f.name for f in dataclasses.fields(wm.WedgeParams)}
        feature_to_field = {"Gap": "gap", "WedgeAngle": "wedge_angle", "PlateThick": "plate_thick",
                            "MaxSlenderness": "max_slenderness", "ContactLand": "contact_land",
                            "ChamferDepth": "chamfer_depth", "TabLayers": "tab_layers",
                            "TabPitch": "tab_pitch", "LayerHeight": "layer_height",
                            "LineWidth": "line_width"}
        self.assertEqual(set(feature_to_field.values()), wedge_fields)
        self.assertTrue(set(feature_to_field) <= set(S.FEATURE_BINDINGS))

    def test_binding_expression_canonical_form(self):
        self.assertEqual(S.binding_expression("SupportGap"), "<<Params>>#VarSet.SupportGap")


def setUpModule():
    from test_env_guard import require_laptop
    print(require_laptop(need_freecad=False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
