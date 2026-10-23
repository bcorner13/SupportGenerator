# FreeCAD Robust MCP Server Tools Reference

**Source of truth:** generated 2026-10-23 from the live tool schemas of
`freecad-robust-mcp` **0.6.3.dev15+g41a36e3c1** (github.com/spkane/freecad-robust-mcp-and-more),
as launched by `~/Documents/3dPrinting/.mcp.json` (`freecad-mcp`, XML-RPC, port 9875).
Every tool name, parameter, and default below was copied from the server's schemas, not from upstream docs.

**If this file and the running server disagree, the server wins.** Re-check with `ToolSearch`
(`select:mcp__freecad__<name>`) and regenerate this file. Tool names in Claude Code are prefixed
`mcp__freecad__` (e.g. `mcp__freecad__pad_sketch`).

**Scope of what was verified:** names, parameters, defaults, and the descriptions the server publishes.
Runtime behaviour was *not* exercised to produce this file. Notes marked **Known issue** come from
`~/.claude/CLAUDE.md` (confirmed 2026-09-03 on FreeCAD 1.1.3).

---

## Overview

| Category | Tools |
| --- | --- |
| [Execution & diagnostics](#execution--diagnostics) | 6 |
| [Documents](#documents) | 8 |
| [Objects](#objects) | 10 |
| [Part primitives](#part-primitives) | 12 |
| [Part shape operations](#part-shape-operations) | 15 |
| [PartDesign: bodies, sketches, datums](#partdesign-bodies-sketches-datums) | 5 |
| [PartDesign: additive](#partdesign-additive) | 4 |
| [PartDesign: subtractive](#partdesign-subtractive) | 5 |
| [PartDesign: dress-up](#partdesign-dress-up) | 4 |
| [PartDesign: patterns](#partdesign-patterns) | 3 |
| [Sketch geometry](#sketch-geometry) | 13 |
| [Sketch constraints](#sketch-constraints) | 15 |
| [Spreadsheet](#spreadsheet) | 10 |
| [Draft ShapeString](#draft-shapestring) | 6 |
| [Validation & recovery](#validation--recovery) | 4 |
| [View & display](#view--display) | 9 |
| [Workbenches](#workbenches) | 2 |
| [Selection](#selection) | 3 |
| [Undo / redo](#undo--redo) | 3 |
| [Import / export](#import--export) | 7 |
| [Macros](#macros) | 6 |
| [Parts library](#parts-library) | 2 |
| **Total** | **152** |

---

## Conventions

- **`doc_name`** — Unless marked *(no doc_name)*, every tool also accepts `doc_name: str | None = None`
  (uses the active document when omitted). It is left out of the signatures below to keep them readable.
- **`name` / `result_name`** — optional; FreeCAD auto-generates a name when `None`.
- **All numeric arguments are literals.** No typed tool accepts an expression string. Under the
  parametric rules (`~/.claude/CLAUDE.md` hard rule 1), any dimension created through a typed tool must
  then be bound to `<<Params>>#VarSet.VarName` with `setExpression` — normally inside a
  `macros/*.FCMacro`. `spreadsheet_bind_property` binds to a *Spreadsheet* alias, not a VarSet.
- **Sketch point indices:** `1` = start, `2` = end, `3` = center, `-1` = the edge itself.
  Geometry index `-2` = "not used" / horizontal axis, depending on the tool (see each one).
- **Errors:** failures come back as `success: false` plus an error message or traceback.

---

## Execution & diagnostics

### `execute_python` *(no doc_name)*
```python
execute_python(code: str, timeout_ms: int = 30000)
```
Runs arbitrary Python in FreeCAD (`FreeCAD`, `App`, `FreeCADGui`, `Gui` available). Set
`_result_ = value` to return data. Returns `success`, `result`, `stdout`, `stderr`,
`execution_time_ms`, `error_type`, `error_traceback`.
Last resort per hard rule 7 — prefer a typed tool or a macro.

### `get_connection_status` *(no doc_name)*
```python
get_connection_status()
```
Returns `connected`, `mode` (embedded / xmlrpc / socket), `freecad_version`, `gui_available`,
`last_ping_ms`, `error`. **Call this first in any FreeCAD session.**

### `get_freecad_version` *(no doc_name)*
```python
get_freecad_version()
```
Returns `version`, `version_tuple`, `build_date`, `python_version`, `gui_available`.

### `get_mcp_server_environment` *(no doc_name)*
```python
get_mcp_server_environment()
```
Returns `instance_id` (UUID per server start), `hostname`, `os_name`, `os_version`, `platform`,
`python_version`, `freecad` {`connected`, `mode`, `version`, `gui_available`, `is_headless`},
`env_vars` {`FREECAD_MODE`, `FREECAD_SOCKET_HOST`, `FREECAD_SOCKET_PORT`, `FREECAD_XMLRPC_PORT`}.

### `get_console_output` *(no doc_name)*
```python
get_console_output(lines: int = 100)
```
Returns a list of recent console lines, most recent last.

### `get_console_log` *(no doc_name)*
```python
get_console_log(lines: int = 50)
```
Returns `messages`, `warnings`, `errors` as separate lists.

---

## Documents

### `list_documents` *(no doc_name)*
```python
list_documents()
```
Each entry: `name`, `label`, `path`, `is_modified`, `object_count`, `active_object`.

### `get_active_document` *(no doc_name)*
```python
get_active_document()
```
Returns `name`, `label`, `path`, `is_modified`, `objects`, `active_object`, or `None`.

### `create_document` *(no doc_name)*
```python
create_document(name: str = "Unnamed", label: str | None = None)
```
`name` is sanitized (no spaces). Returns `name`, `label`, `path` (None until saved).

### `open_document` *(no doc_name)*
```python
open_document(path: str)
```
Full path to a `.FCStd`. Returns `name`, `label`, `path`, `objects`.

### `save_document`
```python
save_document(doc_name: str | None = None, path: str | None = None)
```
`path` is required for a never-saved document. **Save only after Bradley approves**
(PROJECT_BOOTSTRAP Step 6).

### `close_document`
```python
close_document(doc_name: str | None = None, save_changes: bool = False)
```

### `recompute_document`
```python
recompute_document(doc_name: str | None = None)
```
Returns `success`.

### `recompute`
```python
recompute(doc_name: str | None = None)
```
"Force recompute of all objects." Returns `success`, `touch_count`.

---

## Objects

### `list_objects`
```python
list_objects()
```
Each entry: `name`, `label`, `type_id`, `visibility`.

### `inspect_object`
```python
inspect_object(object_name: str, include_properties: bool = True, include_shape: bool = True)
```
Returns `name`, `label`, `type_id`, `properties`, `shape_info`, `children`, `parents`, `visibility`.
**Known issue (FreeCAD 1.1.x):** fails with a generic `"Failed to get object"` on shape-bearing objects
(sketches, Pads, Bodies). Works on plain objects such as `App::VarSet`. Read shape objects with
`execute_python` instead.

### `create_object`
```python
create_object(type_id: str, name: str | None = None, properties: dict | None = None)
```
Any FreeCAD type, e.g. `Part::Box`, `Part::Feature`, `Sketcher::SketchObject`, `PartDesign::Body`.

### `edit_object`
```python
edit_object(object_name: str, properties: dict)
```
Sets property values. The schema does not say whether it accepts expressions — treat values as literals.

### `delete_object`
```python
delete_object(object_name: str)
```

### `copy_object`
```python
copy_object(object_name: str, new_name: str | None = None, offset: list[float] | None = None)
```
`offset` is `[x, y, z]`, default `[0, 0, 0]`.

### `set_placement`
```python
set_placement(object_name: str, position: list[float] | None = None, rotation: list[float] | None = None)
```
`position` `[x, y, z]`; `rotation` `[yaw, pitch, roll]` in degrees. `None` keeps the current value.

### `rotate_object`
```python
rotate_object(object_name: str, axis: list[float], angle: float, center: list[float] | None = None)
```
Modifies placement in place. `center` defaults to the object center.

### `scale_object`
```python
scale_object(object_name: str, scale: float | list[float], result_name: str | None = None)
```
Creates a new scaled copy (`Part.Scale`). Single float = uniform, `[sx, sy, sz]` = non-uniform.

### `mirror_object`
```python
mirror_object(object_name: str, plane: str = "XY", result_name: str | None = None)
```
`plane`: `"XY"`, `"XZ"`, `"YZ"`. Creates a new mirrored copy (Part-level; for PartDesign use
`mirrored_feature`).

---

## Part primitives

All create Part-workbench objects (not PartDesign features).

| Tool | Signature (defaults) |
| --- | --- |
| `create_box` | `(length=10, width=10, height=10, name=None)` |
| `create_cylinder` | `(radius=5, height=10, angle=360, name=None)` |
| `create_sphere` | `(radius=5, name=None)` |
| `create_cone` | `(radius1=5, radius2=0, height=10, angle=360, name=None)` |
| `create_torus` | `(radius1=10, radius2=2, angle1=-180, angle2=180, angle3=360, name=None)` |
| `create_wedge` | `(xmin=0, ymin=0, zmin=0, x2min=2, z2min=2, xmax=10, ymax=10, zmax=10, x2max=8, z2max=8, name=None)` |
| `create_prism` | `(polygon_sides=6, circumradius=5, height=10, name=None)` |
| `create_helix` | `(pitch=5, height=20, radius=5, angle=0, left_handed=False, name=None)` — `angle` = taper |
| `create_plane` | `(length=10, width=10, name=None)` — flat rectangular face |
| `create_line` | `(point1: [x,y,z], point2: [x,y,z], name=None)` — returns `length` |
| `create_ellipse` | `(major_radius=10, minor_radius=5, angle1=0, angle2=360, name=None)` |
| `create_regular_polygon` | `(polygon_sides=6, circumradius=5, name=None)` — 2D wire |

---

## Part shape operations

### `boolean_operation`
```python
boolean_operation(operation: str, object1_name: str, object2_name: str, result_name: str | None = None)
```
`operation`: `"fuse"`, `"cut"` (object1 − object2), `"common"`.

### `fuse_all`
```python
fuse_all(object_names: list[str], result_name: str | None = None)
```

### `common_all`
```python
common_all(object_names: list[str], result_name: str | None = None)
```

### `make_wire`
```python
make_wire(points: list[list[float]], closed: bool = False, name: str | None = None)
```
Points are `[x, y, z]`. Returns `length`.

### `make_face`
```python
make_face(object_name: str, result_name: str | None = None)
```
From a closed wire. Returns `area`.

### `make_compound`
```python
make_compound(object_names: list[str], result_name: str | None = None)
```
Not fused. Returns `shape_count`.

### `explode_compound`
```python
explode_compound(object_name: str)
```
Returns `created_objects`.

### `extrude_shape`
```python
extrude_shape(object_name: str, direction: list[float], result_name: str | None = None)
```
`direction` `[x, y, z]` encodes both direction and length.

### `revolve_shape`
```python
revolve_shape(object_name: str, axis_point: list[float], axis_direction: list[float],
              angle: float = 360, result_name: str | None = None)
```

### `part_loft`
```python
part_loft(profile_names: list[str], solid: bool = True, ruled: bool = False,
          closed: bool = False, result_name: str | None = None)
```

### `part_sweep`
```python
part_sweep(profile_name: str, spine_name: str, solid: bool = True,
           frenet: bool = True, result_name: str | None = None)
```

### `offset_3d`
```python
offset_3d(object_name: str, offset: float, result_name: str | None = None)
```
Positive = outward, negative = inward.

### `shell_object`
```python
shell_object(object_name: str, thickness: float, faces_to_remove: list[str] | None = None,
             result_name: str | None = None)
```
Part-level hollow. Positive = outward. If `faces_to_remove` is `None`, it tries to remove the largest
face. For PartDesign use `thickness_feature`.

### `section_shape`
```python
section_shape(object_name: str, plane: str = "XY", offset: float = 0, result_name: str | None = None)
```

### `slice_shape`
```python
slice_shape(object_name: str, plane_point: list[float], plane_normal: list[float],
            result_name: str | None = None)
```

---

## PartDesign: bodies, sketches, datums

### `create_partdesign_body`
```python
create_partdesign_body(name: str | None = None)
```

### `create_sketch`
```python
create_sketch(body_name: str | None = None, plane: str = "XY_Plane", name: str | None = None)
```
`plane`: `"XY_Plane"`, `"XZ_Plane"`, `"YZ_Plane"`, or a face name like `"Face1"`.
`body_name=None` creates a standalone sketch.
**Do not pass a face name** — hard rule 3 forbids attaching sketches to feature faces. Create a datum
plane first and attach to it.

### `create_datum_plane`
```python
create_datum_plane(body_name: str, offset: float = 0, base_plane: str = "XY_Plane", name: str | None = None)
```
`base_plane`: `"XY_Plane"`, `"XZ_Plane"`, `"YZ_Plane"`. `offset` is a literal — bind it to a Param afterwards.

### `create_datum_line`
```python
create_datum_line(body_name: str, base_axis: str = "X_Axis", name: str | None = None)
```
`base_axis`: `"X_Axis"`, `"Y_Axis"`, `"Z_Axis"`.

### `create_datum_point`
```python
create_datum_point(body_name: str, position: list[float] | None = None, name: str | None = None)
```

---

## PartDesign: additive

### `pad_sketch`
```python
pad_sketch(sketch_name: str, length: float, symmetric: bool = False,
           reversed: bool = False, name: str | None = None)
```

### `revolution_sketch`
```python
revolution_sketch(sketch_name: str, angle: float = 360, axis: str = "Base_X",
                  symmetric: bool = False, reversed: bool = False, name: str | None = None)
```
`axis`: `"Base_X"`, `"Base_Y"`, `"Base_Z"`, `"Sketch_V"`, `"Sketch_H"`.

### `loft_sketches`
```python
loft_sketches(sketch_names: list[str], ruled: bool = False, closed: bool = False, name: str | None = None)
```

### `sweep_sketch`
```python
sweep_sketch(profile_sketch: str, spine_sketch: str, transition: str = "Transformed", name: str | None = None)
```
`transition`: `"Transformed"`, `"Right"`, `"Round"`.

---

## PartDesign: subtractive

### `pocket_sketch`
```python
pocket_sketch(sketch_name: str, length: float, type: str = "Length", name: str | None = None)
```
`type`: `"Length"`, `"ThroughAll"`, `"UpToFirst"`, `"UpToFace"`. `length` is required even for
non-`Length` types.

### `groove_sketch`
```python
groove_sketch(sketch_name: str, angle: float = 360, axis: str = "Base_X",
              symmetric: bool = False, reversed: bool = False, name: str | None = None)
```
Same `axis` options as `revolution_sketch`.

### `create_hole`
```python
create_hole(sketch_name: str, diameter: float = 6.0, depth: float = 10.0, hole_type: str = "Dimension",
            threaded: bool = False, thread_type: str = "ISO", thread_size: str = "M6", name: str | None = None)
```
Sketch must contain center point(s). `hole_type`: `"Dimension"`, `"ThroughAll"`, `"UpToFirst"`.
`thread_type`: `"ISO"`, `"UNC"`, `"UNF"`. No countersink/counterbore parameters — set those on the
Hole object in a macro.

### `subtractive_loft`
```python
subtractive_loft(sketch_names: list[str], ruled: bool = False, closed: bool = False, name: str | None = None)
```

### `subtractive_pipe`
```python
subtractive_pipe(profile_sketch: str, spine_sketch: str, transition: str = "Transformed", name: str | None = None)
```

---

## PartDesign: dress-up

### `fillet_edges`
```python
fillet_edges(object_name: str, radius: float, edges: list[str] | None = None, name: str | None = None)
```
`edges=None` fillets **all** edges.

### `chamfer_edges`
```python
chamfer_edges(object_name: str, size: float, edges: list[str] | None = None, name: str | None = None)
```
`edges=None` chamfers **all** edges.

### `thickness_feature`
```python
thickness_feature(object_name: str, thickness: float, faces_to_remove: list[str], name: str | None = None)
```
Positive = inward. `faces_to_remove` is required.

### `draft_feature`
```python
draft_feature(object_name: str, angle: float, plane: str = "XY", faces: list[str] | None = None,
              name: str | None = None)
```
Draft (mold-release) angle. `plane` = neutral plane: `"XY"`, `"XZ"`, `"YZ"`. `faces=None` drafts all
suitable faces. Not related to the Draft workbench.

---

## PartDesign: patterns

### `linear_pattern`
```python
linear_pattern(feature_name: str, direction: str = "X", length: float = 50.0,
               occurrences: int = 3, name: str | None = None)
```
`direction`: `"X"`, `"Y"`, `"Z"`. Afterwards set `body.Tip` to the pattern before adding the next
feature (UnderDeskCableTray build gotcha).

### `polar_pattern`
```python
polar_pattern(feature_name: str, axis: str = "Z", angle: float = 360.0,
              occurrences: int = 6, name: str | None = None)
```

### `mirrored_feature`
```python
mirrored_feature(feature_name: str, plane: str = "XY", name: str | None = None)
```

---

## Sketch geometry

All return `geometry_index` (or first index) and `geometry_count` unless noted.

| Tool | Signature |
| --- | --- |
| `add_sketch_line` | `(sketch_name, x1, y1, x2, y2, construction=False)` |
| `add_sketch_arc` | `(sketch_name, center_x, center_y, radius, start_angle, end_angle)` — degrees |
| `add_sketch_circle` | `(sketch_name, center_x, center_y, radius)` |
| `add_sketch_ellipse` | `(sketch_name, center_x, center_y, major_radius, minor_radius)` |
| `add_sketch_bspline` | `(sketch_name, points: [[x, y], ...], closed=False)` |
| `add_sketch_point` | `(sketch_name, x, y)` — use for hole centers |
| `add_sketch_polygon` | `(sketch_name, center_x, center_y, radius, sides=6)` — returns `first_line_index` |
| `add_sketch_rectangle` | `(sketch_name, x, y, width, height)` — bottom-left corner; returns `constraint_count`, `geometry_count` |
| `add_sketch_slot` | `(sketch_name, center1_x, center1_y, center2_x, center2_y, radius)` — returns `first_geometry_index` |
| `add_external_geometry` | `(sketch_name, object_name, element)` — e.g. `"Edge1"` |
| `delete_sketch_geometry` | `(sketch_name, geometry_index)` |
| `toggle_construction` | `(sketch_name, geometry_index)` — returns `is_construction` |
| `get_sketch_info` | `(sketch_name)` — returns geometry/constraint counts, `fully_constrained`, `dof` |

**Known issues (FreeCAD 1.1.x):** `get_sketch_info` and `add_external_geometry` throw
`AttributeError: 'Sketcher.SketchObject' object has no attribute 'ExternalGeometryCount'`.
Read sketch state via `execute_python` (`sk.Geometry`, `sk.Constraints`, `sk.ExpressionEngine`).
Projecting external geometry also conflicts with project rules that re-derive geometry from Params.

---

## Sketch constraints

All return `constraint_index`. Dimensional values are literals — bind each to a Param afterwards.

### `add_sketch_constraint` (general purpose)
```python
add_sketch_constraint(sketch_name: str, constraint_type: str, geometry1: int, point1: int = -1,
                      geometry2: int = -2, point2: int = -1, value: float | None = None)
```
`constraint_type` — geometric: `Coincident`, `Horizontal`, `Vertical`, `Parallel`, `Perpendicular`,
`Tangent`, `Equal`, `Symmetric`, `Block`; dimensional: `Distance`, `DistanceX`, `DistanceY`, `Radius`,
`Diameter`, `Angle`. `geometry2 = -2` means external / not used. This is the only typed route to
`Symmetric`, `Block`, `Diameter`, and point-to-point `DistanceX`/`DistanceY`.

### Geometric

| Tool | Signature |
| --- | --- |
| `constrain_coincident` | `(sketch_name, geometry1, point1, geometry2, point2)` — all required |
| `constrain_horizontal` | `(sketch_name, geometry_index)` |
| `constrain_vertical` | `(sketch_name, geometry_index)` |
| `constrain_parallel` | `(sketch_name, geometry1, geometry2)` |
| `constrain_perpendicular` | `(sketch_name, geometry1, geometry2)` |
| `constrain_tangent` | `(sketch_name, geometry1, geometry2)` |
| `constrain_equal` | `(sketch_name, geometry1, geometry2)` — length or radius |
| `constrain_fix` | `(sketch_name, geometry_index, point_index=-1)` — `-1` fixes the whole element |

### Dimensional

| Tool | Signature |
| --- | --- |
| `constrain_distance` | `(sketch_name, geometry1, distance, point1=-1, geometry2=-2, point2=-1)` — line length, point–point, or point–line. **Unsigned.** |
| `constrain_distance_x` | `(sketch_name, geometry, point, distance)` — horizontal distance from origin |
| `constrain_distance_y` | `(sketch_name, geometry, point, distance)` — vertical distance from origin |
| `constrain_radius` | `(sketch_name, geometry_index, radius)` |
| `constrain_angle` | `(sketch_name, geometry1, angle, geometry2=-2)` — degrees; `-2` = from horizontal |

For signed point-to-point offsets, use `add_sketch_constraint` with `DistanceX` / `DistanceY`
(unsigned `Distance` let a neck flip sides in UnderDeskCableTray).

### `delete_sketch_constraint`
```python
delete_sketch_constraint(sketch_name: str, constraint_index: int)
```
Returns the remaining `constraint_count`.

---

## Spreadsheet

Bradley's projects keep Params in a **VarSet**, not a Spreadsheet. These tools do not operate on VarSets.

| Tool | Signature |
| --- | --- |
| `spreadsheet_create` | `(name=None)` |
| `spreadsheet_set_cell` | `(spreadsheet_name, cell, value: str \| int \| float)` — formulas start with `=` |
| `spreadsheet_get_cell` | `(spreadsheet_name, cell)` — returns `value`, `computed`, `alias` |
| `spreadsheet_get_cell_range` | `(spreadsheet_name, start_cell, end_cell)` |
| `spreadsheet_set_alias` | `(spreadsheet_name, cell, alias)` — alias must be a valid identifier |
| `spreadsheet_get_aliases` | `(spreadsheet_name)` |
| `spreadsheet_clear_cell` | `(spreadsheet_name, cell)` — also removes the alias |
| `spreadsheet_bind_property` | `(spreadsheet_name, alias, target_object, target_property)` |
| `spreadsheet_import_csv` | `(spreadsheet_name, file_path, delimiter=",", start_cell="A1")` |
| `spreadsheet_export_csv` | `(spreadsheet_name, file_path, delimiter=",", max_row_limit=1000, max_col_limit=52)` |

---

## Draft ShapeString

### `draft_list_fonts` *(no doc_name)*
```python
draft_list_fonts()
```
Returns `fonts` [{`name`, `path`, `type`}], `count`, `directories`. For `.ttc`, only the first face is used.

### `draft_shapestring`
```python
draft_shapestring(text: str, font_path: str | None = None, size: float = 10.0,
                  position: list[float] | None = None, name: str | None = None)
```
`position` `[x, y, z]`. `font_path=None` uses FreeCAD's default font.

### `draft_shapestring_to_sketch`
```python
draft_shapestring_to_sketch(shapestring_name: str, body_name: str | None = None,
                            plane: str = "XY_Plane", sketch_name: str | None = None)
```
Converts to a `Sketcher::SketchObject` for Pad/Pocket. Returns `wire_count`.

### `draft_shapestring_to_face`
```python
draft_shapestring_to_face(shapestring_name: str, name: str | None = None)
```
Creates a `Part::Feature` face. Returns `face_count`, `area`.

### `draft_extrude_shapestring`
```python
draft_extrude_shapestring(shapestring_name: str, height: float = 10.0,
                          direction: list[float] | None = None, name: str | None = None)
```
`direction` defaults to `[0, 0, 1]`.

### `draft_text_on_surface`
```python
draft_text_on_surface(text: str, target_face: str, target_object: str, depth: float = 2.0,
                      font_path: str | None = None, size: float = 10.0,
                      position: list[float] | None = None, operation: str = "engrave",
                      name: str | None = None)
```
`operation`: `"emboss"` or `"engrave"`; `position` is `[x, y]` on the face. This is a Part boolean onto a
named face, so it is face-referenced and literal-valued. For parametric logos use a ShapeString sketch
on a datum plane inside the Body.

---

## Validation & recovery

### `validate_object`
```python
validate_object(object_name: str)
```
Returns `valid`, `shape_valid`, `has_errors`, `state`, `recompute_needed`, `volume`, `area`,
`error_messages`, `warnings`.

### `validate_document`
```python
validate_document()
```
Returns `valid`, `total_objects`, `valid_objects`, `invalid_objects`, `objects_with_errors`,
`objects_needing_recompute`, `recompute_needed`, `summary`.

### `undo_if_invalid`
```python
undo_if_invalid()
```
Validates; if anything is invalid, performs **one** undo. Returns `was_valid`, `undone`,
`invalid_objects`, `objects_with_errors`, `message`, `validation_after`.

### `safe_execute`
```python
safe_execute(code: str, validate_after: bool = True, auto_undo_on_failure: bool = True)
```
`execute_python` wrapped in an undo transaction, with validation and automatic rollback.
Returns `success`, `result`, `rolled_back`, `execution_success`, `execution_error`, `validation`, `message`.

---

## View & display

| Tool | Signature | Notes |
| --- | --- | --- |
| `get_screenshot` | `(view_angle="Isometric", width=800, height=600)` | **GUI only.** Returns base64 PNG in `data` |
| `set_view_angle` | `(view_angle)` | |
| `fit_all` | `()` | |
| `zoom_in` | `(factor=1.5)` | **GUI only** |
| `zoom_out` | `(factor=1.5)` | **GUI only** |
| `set_camera_position` | `(position: [x,y,z], look_at=None)` | **GUI only.** `look_at` defaults to the origin |
| `set_object_visibility` | `(object_name, visible: bool)` | |
| `set_display_mode` | `(object_name, mode)` | `"Flat Lines"`, `"Shaded"`, `"Wireframe"`, `"Points"` |
| `set_object_color` | `(object_name, color: [r,g,b])` | 0.0–1.0 |

`view_angle` options: `Isometric`, `Front`, `Back`, `Top`, `Bottom`, `Left`, `Right`, `FitAll`.
"GUI only" is marked only where the server's own description says so.

---

## Workbenches

| Tool | Signature |
| --- | --- |
| `list_workbenches` *(no doc_name)* | `()` — returns `name`, `label`, `is_active` |
| `activate_workbench` *(no doc_name)* | `(workbench_name)` — e.g. `PartDesignWorkbench`, `SketcherWorkbench`, `MeshWorkbench` |

---

## Selection

All three require GUI mode.

| Tool | Signature |
| --- | --- |
| `get_selection` | `()` — returns `name`, `label`, `type_id`, `sub_elements` |
| `set_selection` | `(object_names: list[str], clear_existing=True)` |
| `clear_selection` *(no doc_name)* | `()` |

---

## Undo / redo

| Tool | Signature |
| --- | --- |
| `undo` | `()` — returns `success`, `can_undo` |
| `redo` | `()` — returns `success`, `can_redo` |
| `get_undo_redo_status` | `()` — returns `undo_count`, `redo_count`, `undo_names` |

---

## Import / export

| Tool | Signature |
| --- | --- |
| `export_stl` | `(file_path, object_names=None, mesh_tolerance=0.1)` |
| `export_3mf` | `(file_path, object_names=None, mesh_tolerance=0.1)` |
| `export_step` | `(file_path, object_names=None)` |
| `export_obj` | `(file_path, object_names=None, mesh_tolerance=0.1)` |
| `export_iges` | `(file_path, object_names=None)` |
| `import_step` | `(file_path, doc_name=None)` — creates a new document if `doc_name` is None |
| `import_stl` | `(file_path, doc_name=None)` — creates a new document if `doc_name` is None |

`object_names=None` exports **all visible** objects; pass the Body explicitly. There is no
placement/rotation parameter, so rotation into print pose has to happen before export.

---

## Macros

All six take no `doc_name`.

| Tool | Signature |
| --- | --- |
| `list_macros` | `()` — returns `name`, `path`, `description`, `is_system` |
| `read_macro` | `(macro_name)` — name without `.FCMacro` |
| `run_macro` | `(macro_name, args: dict \| None = None)` — `args` are set as variables before execution |
| `create_macro` | `(name, code, description="")` — writes to FreeCAD's **user macro dir** and adds standard imports |
| `create_macro_from_template` | `(name, template="basic", description="")` — `basic`, `part`, `sketch`, `gui`, `selection` |
| `delete_macro` | `(macro_name)` — user macros only |

`create_macro` writes into FreeCAD's macro directory, **not** the project's `macros/`. Project macros
should be written to `macros/` and symlinked into the FreeCAD macro dir per the bootstrap layout.

---

## Parts library

| Tool | Signature |
| --- | --- |
| `list_parts_library` *(no doc_name)* | `()` — returns `name`, `path`, `category` |
| `insert_part_from_library` | `(part_path, name=None, position: [x,y,z] \| None = None)` |
