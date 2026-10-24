"""SupportGenerator workbench + commands.

Executed by InitGui.py's stub loader inside an explicit namespace (FreeCAD's
RunInitGuiPy does not give class methods a usable __globals__ otherwise; see
~/.claude memory feedback_freecad_initgui_exec.md). __file__ is injected by the stub.
Command logic lives in importable supportgen modules; this file only wires the GUI.
"""
import os

import FreeCAD as App
import FreeCADGui as Gui

_WB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ICON = os.path.join(_WB_DIR, "Resources", "icons", "SupportGenerator.svg")


def _msg(text):
    App.Console.PrintMessage(f"SupportGenerator: {text}\n")


class _EnsureSupportParams:
    def GetResources(self):
        return {"Pixmap": _ICON,
                "MenuText": "Ensure Support Params",
                "ToolTip": "Add any missing Support* variables to the open Params VarSet "
                           "(existing values are never changed; nothing is saved)"}

    def IsActive(self):
        from supportgen import params
        return params.find_params_varset() is not None

    def Activated(self):
        from supportgen import params
        vs = params.find_params_varset()
        doc = vs.Document
        doc.openTransaction("Ensure Support Params")
        try:
            rep = params.ensure_params(vs)
            doc.recompute()
        finally:
            doc.commitTransaction()
        _msg(f"added {len(rep['added'])}: {', '.join(rep['added']) or '-'}")
        _msg(f"kept {len(rep['kept'])} existing")
        for name, have, want in rep["conflicts"]:
            App.Console.PrintWarning(
                f"SupportGenerator: {name} exists as {have}, expected {want}; left unchanged\n")
        if rep["added"]:
            _msg(f"{doc.Label} modified, not saved")


class _AddSupports:
    def GetResources(self):
        return {"Pixmap": _ICON,
                "MenuText": "Add Supports",
                "ToolTip": "Generate break-away wedge supports for the selected Body "
                           "(not built yet: plan.md Phase 4)"}

    def IsActive(self):
        return False  # Phase 4

    def Activated(self):
        pass


class _ExportPartAndSupports:
    def GetResources(self):
        return {"Pixmap": _ICON,
                "MenuText": "Export Part + Supports (3MF)",
                "ToolTip": "Export the Body and its Supports as two objects in one 3MF "
                           "(not built yet: plan.md Phase 5)"}

    def IsActive(self):
        return False  # Phase 5

    def Activated(self):
        pass


COMMANDS = {
    "SG_EnsureSupportParams": _EnsureSupportParams,
    "SG_AddSupports": _AddSupports,
    "SG_ExportPartAndSupports": _ExportPartAndSupports,
}


class SupportGeneratorWorkbench(Gui.Workbench):
    MenuText = "SupportGenerator"
    ToolTip = "Modeled break-away wedge supports (separate object, touching tabs)"
    Icon = _ICON

    def Initialize(self):
        for name, cls in COMMANDS.items():
            Gui.addCommand(name, cls())
        self.appendToolbar("SupportGenerator", list(COMMANDS))
        self.appendMenu("SupportGenerator", list(COMMANDS))

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(SupportGeneratorWorkbench())
