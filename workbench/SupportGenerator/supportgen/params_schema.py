"""The one table of SupportGenerator Params: names, VarSet property types, groups,
tool defaults. Pure Python, NO FreeCAD imports (tested by tests/test_params_schema.py).

These are the *tool defaults* only. Each project keeps its own values in its own
Params VarSet; *Ensure Support Params* copies a default in only when the variable is
missing, and never overwrites an existing value.

Every name carries the `Support` prefix so the tool never adopts a same-named
variable another project uses for something else (e.g. a sketch `LineWidth`).
Order matters: a variable with an `expression` must come after what it references.
"""
from collections import namedtuple

GROUP = "Support"

Param = namedtuple("Param", "name type default expression doc")

PARAMS = [
    Param("SupportOverhangAngle", "App::PropertyAngle", 45.0, None,
          "A face needs support when it leans this far or more from vertical"),
    Param("SupportLineWidth", "App::PropertyLength", 0.42, None,
          "Slicer extrusion line width (0.4 nozzle); caps tab length"),
    Param("SupportLayerHeight", "App::PropertyLength", 0.20, None,
          "Slicer layer height; sizes tabs in layers"),
    Param("SupportGap", "App::PropertyLength", 0.25, None,
          "Air gap between part and wedge contact land, normal to the face"),
    Param("SupportWedgeAngle", "App::PropertyAngle", 45.0, None,
          "Angle of a wedge's free hypotenuse (level overhangs)"),
    Param("SupportPlateThick", "App::PropertyLength", 2.0, None,
          "Wedge plate body thickness (minimum)"),
    Param("SupportMaxSlenderness", "App::PropertyFloat", 40.0, None,
          "Max wedge height / plate thickness before the plate thickens"),
    Param("SupportContactLand", "App::PropertyLength", None, "SupportLineWidth * 2",
          "Width of the flat strip left at the contact edge after the chamfers"),
    Param("SupportChamferDepth", "App::PropertyLength", 3.0, None,
          "How far the double chamfer runs back from the contact edge"),
    Param("SupportWedgePitch", "App::PropertyLength", 15.0, None,
          "Max spacing between wedges across a wide overhang"),
    Param("SupportTabLayers", "App::PropertyInteger", 1, None,
          "Tab height where it meets the part, in print layers (1-2)"),
    Param("SupportTabPitch", "App::PropertyLength", 7.5, None,
          "Max spacing between tabs along a wedge (5-10 mm)"),
    Param("SupportMinOverhangArea", "App::PropertyArea", 4.0, None,
          "Ignore overhang faces smaller than this (slicer bridges them)"),
]

BY_NAME = {p.name: p for p in PARAMS}

# FeaturePython property on the Supports object -> Params variable it is bound to.
# Feature property names stay short; the binding is the contract.
FEATURE_BINDINGS = {
    "OverhangAngle": "SupportOverhangAngle",
    "LineWidth": "SupportLineWidth",
    "LayerHeight": "SupportLayerHeight",
    "Gap": "SupportGap",
    "WedgeAngle": "SupportWedgeAngle",
    "PlateThick": "SupportPlateThick",
    "MaxSlenderness": "SupportMaxSlenderness",
    "ContactLand": "SupportContactLand",
    "ChamferDepth": "SupportChamferDepth",
    "WedgePitch": "SupportWedgePitch",
    "TabLayers": "SupportTabLayers",
    "TabPitch": "SupportTabPitch",
    "MinArea": "SupportMinOverhangArea",
}


def binding_expression(param_name, params_doc="Params", varset="VarSet"):
    """Canonical cross-document form (global rule): <<Params>>#VarSet.Name"""
    return f"<<{params_doc}>>#{varset}.{param_name}"
