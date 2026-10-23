# Tools Reference

Quick reference for the **152** tools exposed by the FreeCAD Robust MCP Server
(`freecad-robust-mcp` 0.6.3.dev15+g41a36e3c1). Generated 2026-10-23 from the live tool schemas.
In Claude Code every name is prefixed `mcp__freecad__`.

For parameters, defaults, and known issues, see [MCP_TOOLS_REFERENCE.md](MCP_TOOLS_REFERENCE.md).
If this list and the running server disagree, the server wins: check with `ToolSearch` and regenerate.

**Undo:** per the server's descriptions, `safe_execute` runs inside an undo transaction and
`undo` / `redo` / `undo_if_invalid` act on the document's undo stack. Not every tool states that it is
transaction-wrapped, so don't assume one `undo` reverts an arbitrary operation. Check
`get_undo_redo_status`.

---

## Tool categories

| Category | Tools | Description |
| --- | --- | --- |
| [Execution & diagnostics](#execution--diagnostics) | 6 | Python execution, connection, console |
| [Documents](#documents) | 8 | Open, save, close, recompute |
| [Objects](#objects) | 10 | Inspect, edit, delete, place, copy |
| [Part primitives](#part-primitives) | 12 | Basic Part shapes and curves |
| [Part shape operations](#part-shape-operations) | 15 | Booleans, wires/faces, extrude, loft, offset, section |
| [PartDesign: bodies, sketches, datums](#partdesign-bodies-sketches-datums) | 5 | Body, sketch, datum plane/line/point |
| [PartDesign: additive](#partdesign-additive) | 4 | Pad, revolution, loft, sweep |
| [PartDesign: subtractive](#partdesign-subtractive) | 5 | Pocket, groove, hole, subtractive loft/pipe |
| [PartDesign: dress-up](#partdesign-dress-up) | 4 | Fillet, chamfer, thickness, draft angle |
| [PartDesign: patterns](#partdesign-patterns) | 3 | Linear, polar, mirrored |
| [Sketch geometry](#sketch-geometry) | 13 | Lines, arcs, shapes, construction, external geometry |
| [Sketch constraints](#sketch-constraints) | 15 | Geometric and dimensional constraints |
| [Spreadsheet](#spreadsheet) | 10 | Spreadsheet cells, aliases, binding |
| [Draft ShapeString](#draft-shapestring) | 6 | 3D text |
| [Validation & recovery](#validation--recovery) | 4 | Health checks, auto-rollback |
| [View & display](#view--display) | 9 | Camera, screenshots, appearance |
| [Workbenches](#workbenches) | 2 | List/activate workbenches |
| [Selection](#selection) | 3 | GUI selection |
| [Undo / redo](#undo--redo) | 3 | Undo stack |
| [Import / export](#import--export) | 7 | STL, 3MF, STEP, OBJ, IGES |
| [Macros](#macros) | 6 | Macro management |
| [Parts library](#parts-library) | 2 | Parts library |
| **Total** | **152** | |

---

## Execution & diagnostics

| Tool | Description |
| --- | --- |
| `execute_python` | Execute arbitrary Python in FreeCAD (last resort — hard rule 7) |
| `get_connection_status` | Check the bridge connection — call first |
| `get_freecad_version` | FreeCAD version and build info |
| `get_mcp_server_environment` | Server instance ID, host, FreeCAD connection, env vars |
| `get_console_output` | Recent console lines |
| `get_console_log` | Recent console split into messages / warnings / errors |

## Documents

| Tool | Description |
| --- | --- |
| `list_documents` | List open documents |
| `get_active_document` | Get the active document |
| `create_document` | Create a new document |
| `open_document` | Open a `.FCStd` |
| `save_document` | Save (only after approval) |
| `close_document` | Close, optionally saving |
| `recompute_document` | Recompute a document |
| `recompute` | Force recompute of all objects |

## Objects

| Tool | Description |
| --- | --- |
| `list_objects` | List objects in a document |
| `inspect_object` | Object details (**broken on shape-bearing objects on 1.1.x**) |
| `create_object` | Create any object by type ID |
| `edit_object` | Set property values |
| `delete_object` | Delete an object |
| `copy_object` | Copy with optional offset |
| `set_placement` | Set position / rotation |
| `rotate_object` | Rotate around an axis |
| `scale_object` | Scaled copy (uniform or per-axis) |
| `mirror_object` | Mirrored copy (Part-level) |

## Part primitives

| Tool | Description |
| --- | --- |
| `create_box` | Box |
| `create_cylinder` | Cylinder (optionally partial) |
| `create_sphere` | Sphere |
| `create_cone` | Cone / frustum |
| `create_torus` | Torus |
| `create_wedge` | Tapered wedge |
| `create_prism` | Extruded regular polygon |
| `create_helix` | Helix curve |
| `create_plane` | Flat rectangular face |
| `create_line` | Line edge between two points |
| `create_ellipse` | Ellipse curve |
| `create_regular_polygon` | Regular polygon wire |

## Part shape operations

| Tool | Description |
| --- | --- |
| `boolean_operation` | Fuse / cut / common of two objects |
| `fuse_all` | Fuse many objects |
| `common_all` | Intersect many objects |
| `make_wire` | Polyline wire from points |
| `make_face` | Face from closed wire |
| `make_compound` | Compound (not fused) |
| `explode_compound` | Split compound into objects |
| `extrude_shape` | Extrude wire/face along a vector |
| `revolve_shape` | Revolve wire/face around an axis |
| `part_loft` | Loft through wires/faces |
| `part_sweep` | Sweep profile along spine |
| `offset_3d` | 3D offset |
| `shell_object` | Hollow a solid (Part-level) |
| `section_shape` | Cross-section at XY/XZ/YZ + offset |
| `slice_shape` | Slice by arbitrary plane |

## PartDesign: bodies, sketches, datums

| Tool | Description |
| --- | --- |
| `create_partdesign_body` | PartDesign Body |
| `create_sketch` | Sketch on a base plane (don't use its face option — hard rule 3) |
| `create_datum_plane` | Datum plane offset from a base plane |
| `create_datum_line` | Datum axis |
| `create_datum_point` | Datum point |

## PartDesign: additive

| Tool | Description |
| --- | --- |
| `pad_sketch` | Pad |
| `revolution_sketch` | Revolution |
| `loft_sketches` | Additive loft |
| `sweep_sketch` | Additive pipe/sweep |

## PartDesign: subtractive

| Tool | Description |
| --- | --- |
| `pocket_sketch` | Pocket |
| `groove_sketch` | Groove |
| `create_hole` | Hole from sketch points (optionally threaded) |
| `subtractive_loft` | Subtractive loft |
| `subtractive_pipe` | Subtractive pipe/sweep |

## PartDesign: dress-up

| Tool | Description |
| --- | --- |
| `fillet_edges` | Fillet (all edges if none given) |
| `chamfer_edges` | Chamfer (all edges if none given) |
| `thickness_feature` | PartDesign shell |
| `draft_feature` | Draft (mold-release) angle on faces |

## PartDesign: patterns

| Tool | Description |
| --- | --- |
| `linear_pattern` | Linear pattern along X/Y/Z |
| `polar_pattern` | Polar pattern about X/Y/Z |
| `mirrored_feature` | Mirror feature across XY/XZ/YZ |

## Sketch geometry

| Tool | Description |
| --- | --- |
| `add_sketch_line` | Line (optionally construction) |
| `add_sketch_arc` | Arc |
| `add_sketch_circle` | Circle |
| `add_sketch_ellipse` | Ellipse |
| `add_sketch_bspline` | B-spline from control points |
| `add_sketch_point` | Point (hole centers) |
| `add_sketch_polygon` | Regular polygon |
| `add_sketch_rectangle` | Rectangle |
| `add_sketch_slot` | Slot (obround) |
| `add_external_geometry` | Reference external edge/face (**broken on 1.1.x**) |
| `delete_sketch_geometry` | Delete geometry by index |
| `toggle_construction` | Toggle construction mode |
| `get_sketch_info` | Sketch counts / DOF (**broken on 1.1.x**) |

## Sketch constraints

| Tool | Description |
| --- | --- |
| `add_sketch_constraint` | General constraint (incl. Symmetric, Block, Diameter, point-to-point DistanceX/Y) |
| `constrain_coincident` | Coincident points |
| `constrain_horizontal` | Horizontal line |
| `constrain_vertical` | Vertical line |
| `constrain_parallel` | Parallel lines |
| `constrain_perpendicular` | Perpendicular lines |
| `constrain_tangent` | Tangent curves |
| `constrain_equal` | Equal length/radius |
| `constrain_fix` | Lock point or element |
| `constrain_distance` | Length / point–point / point–line (unsigned) |
| `constrain_distance_x` | Horizontal distance from origin |
| `constrain_distance_y` | Vertical distance from origin |
| `constrain_radius` | Radius |
| `constrain_angle` | Angle (vs. line or horizontal) |
| `delete_sketch_constraint` | Delete constraint by index |

## Spreadsheet

These work on Spreadsheet objects, not VarSets (Bradley's projects use a VarSet in `Params.FCStd`).

| Tool | Description |
| --- | --- |
| `spreadsheet_create` | Create a spreadsheet |
| `spreadsheet_set_cell` | Set value or formula |
| `spreadsheet_get_cell` | Get raw + computed value |
| `spreadsheet_get_cell_range` | Get a range |
| `spreadsheet_set_alias` | Set a cell alias |
| `spreadsheet_get_aliases` | List aliases |
| `spreadsheet_clear_cell` | Clear cell and alias |
| `spreadsheet_bind_property` | Bind object property to an alias |
| `spreadsheet_import_csv` | Import CSV |
| `spreadsheet_export_csv` | Export CSV |

## Draft ShapeString

| Tool | Description |
| --- | --- |
| `draft_list_fonts` | List system fonts |
| `draft_shapestring` | Create ShapeString text |
| `draft_shapestring_to_sketch` | Convert to Sketch (for Pad/Pocket) |
| `draft_shapestring_to_face` | Convert to Part face |
| `draft_extrude_shapestring` | Extrude to solid text |
| `draft_text_on_surface` | Emboss/engrave on a named face (Part boolean, face-referenced) |

## Validation & recovery

| Tool | Description |
| --- | --- |
| `validate_object` | Check one object's health |
| `validate_document` | Check all objects |
| `undo_if_invalid` | Validate, then undo once if invalid |
| `safe_execute` | Python in a transaction with validation + auto-rollback |

## View & display

| Tool | Mode | Description |
| --- | --- | --- |
| `get_screenshot` | GUI | Capture 3D view (base64 PNG) |
| `set_view_angle` | — | Set standard view |
| `fit_all` | — | Fit all |
| `zoom_in` | GUI | Zoom in |
| `zoom_out` | GUI | Zoom out |
| `set_camera_position` | GUI | Set camera position / look-at |
| `set_object_visibility` | — | Show / hide |
| `set_display_mode` | — | Flat Lines / Shaded / Wireframe / Points |
| `set_object_color` | — | RGB color |

"GUI" is marked only where the server's description states it. "—" means the description doesn't say.

## Workbenches

| Tool | Description |
| --- | --- |
| `list_workbenches` | List workbenches |
| `activate_workbench` | Activate a workbench |

## Selection

| Tool | Description |
| --- | --- |
| `get_selection` | Get selection (GUI) |
| `set_selection` | Select objects (GUI) |
| `clear_selection` | Clear selection (GUI) |

## Undo / redo

| Tool | Description |
| --- | --- |
| `undo` | Undo last operation |
| `redo` | Redo |
| `get_undo_redo_status` | Undo/redo counts and names |

## Import / export

| Tool | Description |
| --- | --- |
| `export_stl` | STL |
| `export_3mf` | 3MF |
| `export_step` | STEP |
| `export_obj` | OBJ |
| `export_iges` | IGES |
| `import_step` | Import STEP |
| `import_stl` | Import STL (mesh) |

## Macros

| Tool | Description |
| --- | --- |
| `list_macros` | List macros |
| `read_macro` | Read macro source |
| `run_macro` | Run a macro by name |
| `create_macro` | Create macro in FreeCAD's user macro dir (not project `macros/`) |
| `create_macro_from_template` | Create from template |
| `delete_macro` | Delete a user macro |

## Parts library

| Tool | Description |
| --- | --- |
| `list_parts_library` | List library parts |
| `insert_part_from_library` | Insert a library part |
