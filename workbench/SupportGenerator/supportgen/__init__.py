"""SupportGenerator package. Unique top-level name on purpose: every Mod/<addon> dir shares
one sys.path, and FreeCADMCPAgent already ships a bare _workbench.py. The proxy path
supportgen.feature.SupportFeature is saved into model files -- treat module names as frozen API."""
