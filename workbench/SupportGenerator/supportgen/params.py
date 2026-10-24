"""Find a project's Params VarSet and add any missing Support* variables to it.

FreeCAD-side (imports FreeCAD). The table itself lives in params_schema.py.
Never overwrites an existing value; never saves (PROJECT_BOOTSTRAP Step 6).
"""
import FreeCAD as App

from . import params_schema as S


def find_params_varset(doc_label="Params", varset_name="VarSet"):
    """The VarSet in the open document labelled/named `doc_label`, or None."""
    for doc in App.listDocuments().values():
        if doc_label in (doc.Label, doc.Name):
            vs = doc.getObject(varset_name)
            if vs is not None and vs.TypeId == "App::VarSet":
                return vs
    return None


def ensure_params(varset):
    """Add missing Support* variables to `varset`.

    Returns {"added": [...], "kept": [...], "conflicts": [(name, existing_type, wanted_type)]}.
    A conflict is a same-named variable of the wrong type; it is reported, not touched.
    """
    report = {"added": [], "kept": [], "conflicts": []}
    for p in S.PARAMS:
        if p.name in varset.PropertiesList:
            have = varset.getTypeIdOfProperty(p.name)
            if have == p.type:
                report["kept"].append(p.name)
            else:
                report["conflicts"].append((p.name, have, p.type))
            continue
        varset.addProperty(p.type, p.name, S.GROUP, p.doc)
        if p.expression:
            varset.setExpression(p.name, p.expression)
        else:
            setattr(varset, p.name, p.default)
        report["added"].append(p.name)
    return report
