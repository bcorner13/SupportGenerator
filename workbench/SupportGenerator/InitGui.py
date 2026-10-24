"""Stub loader. FreeCAD's RunInitGuiPy exec doesn't share globals with class methods or
callbacks, and doesn't set __file__. Exec the real code with an explicit namespace that
becomes the persistent __globals__ for everything defined in it. Put no workbench code here.
"""
import os
import sys

import FreeCAD as _App

_addon_dir = os.path.join(_App.getUserAppDataDir(), "Mod", "SupportGenerator")
if _addon_dir not in sys.path:
    sys.path.insert(0, _addon_dir)

_real = os.path.join(_addon_dir, "supportgen", "gui.py")
_ns = dict(globals())
_ns["__file__"] = _real
with open(_real) as _f:
    exec(compile(_f.read(), _real, "exec"), _ns)
