# Commercial 3D Design Standards
**Version:** 1.0
**Project Path:** ~/Documents/3dPrinting/Commercial License

## 1. Engineering Constraints
* **Unit System:** All dimensions MUST be in millimeters (mm).
* **Manifold Geometry:** Every model must be watertight (manifold) with no self-intersecting faces to ensure 120mm x 140mm prints are successful.
* **Workbenches:** Prioritize the `Part` and `PartDesign` workbenches for boolean operations to ensure features like **ribs** or **honeycombs** are fully fused.
* **Print Bed Centering:** All objects must be centered at (0,0,0) for the **Creality K2 Plus** and **ELEGOO Saturn 4**.

## 2. Commercial & Pricing Guardrails
* **Target Price Points:** Designs should be optimized for the **$36 - $45** range.
* **Aesthetic Focus:** Optimize geometry for "Silk" filaments (Gold/Copper), avoiding sharp overhangs that cause artifacts.
* **Wall Thickness:** Default to a consistent 2.0mm - 3.0mm wall thickness unless specified, ensuring a "solid, printable piece".

## 3. Workflow & DevOps (Gitflow)
* **Environment:** Python **3.13.11** via `pyenv` and `.venv`.
* **Branching:**
    * `main`: Verified, watertight STLs ready for sale.
    * `develop`: Active parametric modeling and Python scripting.
    * `feature/*`: Specific iterations (e.g., `feature/hex-drainage-v2`).
* **Automation:** Use the `freecad` MCP tool for all geometry generation.

## 4. File Structure
* `/cad_files`: .FCStd and Python scripts.
* `/stls`: Final exported watertight models.
* `/renders`: CAD-style renders for image-to-3D testing.
