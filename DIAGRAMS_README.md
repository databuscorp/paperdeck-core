# PaperDeck STEM Diagram Rendering Engine

A production-grade, deterministic diagram rendering system for Physics, Chemistry,
Mathematics, and Circuit diagrams — built into the PaperDeck backend.

## Architecture

```
Question Generator AI
    ↓
Diagram Schema Generator AI   ← AI generates semantic JSON ONLY
    ↓
JSON Schema Validation         ← Pydantic (strict)
    ↓
Deterministic Rendering        ← svgwrite / matplotlib / schemdraw / rdkit
    ↓
SVG / PNG Output
    ↓
PDF Composer                   ← ReportLab
```

**AI never generates SVG, coordinates, or geometry. It only describes diagram intent.**

---

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: install cairosvg for PNG export
pip install cairosvg

# Optional: install rdkit for organic chemistry
pip install rdkit-pypi

# Apply migrations
python manage.py migrate

# Run server
python manage.py runserver
```

### Docker

```bash
docker-compose up --build
```

---

## API Reference

### `POST /api/diagrams/render/`

Validate and render a diagram from a JSON schema.

**Request body:**
```json
{
  "diagram_type": "physics",
  "subtype": "inclined_plane",
  "canvas": { "width": 800, "height": 600 },
  "params": {
    "angle": 37,
    "forces": ["mg", "N", "f"],
    "block_label": "m"
  }
}
```

**Response (200):**
```json
{
  "success": true,
  "diagram_id": "uuid-here",
  "diagram_type": "physics",
  "subtype": "inclined_plane",
  "svg_content": "<svg ...>...</svg>",
  "svg_path": "rendered/physics/uuid.svg",
  "svg_url": "/media/rendered/physics/uuid.svg",
  "render_time_ms": 12,
  "validation": { "valid": true, "errors": [], "warnings": [] }
}
```

**Error (422):**
```json
{
  "success": false,
  "error": "...",
  "validation": {
    "valid": false,
    "errors": [{ "field": "params.angle", "message": "...", "type": "..." }]
  }
}
```

---

### `POST /api/diagrams/validate/`

Validate a schema without rendering.

```json
{ "diagram_type": "physics", "subtype": "inclined_plane", "params": { "angle": 37 } }
```

Response: `{ "valid": true, "errors": [], "warnings": [] }`

---

### `POST /api/diagrams/pdf/`

Generate a complete question paper PDF.

```json
{
  "title": "JEE Mains Mock Test",
  "exam_name": "JEE Mains",
  "duration_minutes": 180,
  "total_marks": 360,
  "instructions": ["Read all questions carefully.", "Each question carries 4 marks."],
  "sections": [
    {
      "name": "Section A - Physics",
      "questions": [
        {
          "number": 1,
          "text": "A block of mass 2 kg rests on a 37° incline. Find the normal force.",
          "options": [
            { "text": "15.6 N", "correct": true },
            { "text": "19.6 N", "correct": false },
            { "text": "12.4 N", "correct": false },
            { "text": "9.8 N", "correct": false }
          ],
          "marks": 4,
          "negative_marks": -1,
          "diagram_svg": "<svg ...>...</svg>"
        }
      ]
    }
  ]
}
```

Returns: binary PDF download (`application/pdf`).

---

### `GET /api/diagrams/types/`

List all supported diagram types and subtypes.

```json
{
  "supported_types": {
    "physics": ["inclined_plane", "free_body_diagram", "pulley_system",
                "projectile_motion", "spring_block", "optics_convex_lens",
                "optics_concave_mirror", "wave_diagram"],
    "chemistry": ["organic_structure", "inorganic_structure",
                  "orbital_diagram", "reaction_coordinate_graph"],
    "mathematics": ["function_graph", "geometry_triangle", "geometry_circle",
                    "coordinate_geometry", "calculus_graph"],
    "circuits": ["resistor_network", "capacitor_network", "basic_dc_circuit"]
  }
}
```

---

### `GET /api/health/`

Health check with dependency status.

```json
{
  "status": "healthy",
  "timestamp": "2025-05-25T10:00:00Z",
  "checks": {
    "database": "ok",
    "svgwrite": "1.4.3",
    "matplotlib": "3.8.0",
    "schemdraw": "0.18",
    "rdkit": "not installed (organic structure rendering uses fallback)",
    "reportlab": "4.1.0",
    "cairosvg": "2.7.1",
    "pydantic": "2.5.0"
  }
}
```

---

## Schema Reference

### Physics Diagrams

#### `inclined_plane`
```json
{
  "diagram_type": "physics",
  "subtype": "inclined_plane",
  "params": {
    "angle": 37,
    "block_label": "m",
    "forces": ["mg", "N", "f"],
    "show_angle_label": true,
    "friction_direction": "up"
  }
}
```

#### `free_body_diagram`
```json
{
  "diagram_type": "physics",
  "subtype": "free_body_diagram",
  "params": {
    "object": { "shape": "square", "label": "m" },
    "forces": [
      { "label": "mg", "direction_deg": 270 },
      { "label": "N", "direction_deg": 90 },
      { "label": "T", "direction_deg": 0, "magnitude": 30 }
    ]
  }
}
```
> `direction_deg`: 0=right, 90=up, 180=left, 270=down

#### `pulley_system`
```json
{
  "diagram_type": "physics",
  "subtype": "pulley_system",
  "params": {
    "pulley_count": 1,
    "masses": [
      { "label": "m₁", "mass": 5 },
      { "label": "m₂", "mass": 3 }
    ]
  }
}
```

#### `projectile_motion`
```json
{
  "diagram_type": "physics",
  "subtype": "projectile_motion",
  "params": {
    "initial_velocity": 20,
    "launch_angle": 45,
    "show_components": true,
    "show_max_height_line": true,
    "label_points": ["O", "H", "R"]
  }
}
```

#### `spring_block`
```json
{
  "diagram_type": "physics",
  "subtype": "spring_block",
  "params": {
    "orientation": "horizontal",
    "block_label": "m",
    "spring_label": "k",
    "displacement_label": "x"
  }
}
```

#### `optics_convex_lens`
```json
{
  "diagram_type": "physics",
  "subtype": "optics_convex_lens",
  "params": {
    "focal_length": 100,
    "show_rays": true,
    "show_focal_points": true
  }
}
```

#### `optics_concave_mirror`
```json
{
  "diagram_type": "physics",
  "subtype": "optics_concave_mirror",
  "params": {
    "focal_length": 110,
    "show_rays": true,
    "show_focal_points": true
  }
}
```

#### `wave_diagram`
```json
{
  "diagram_type": "physics",
  "subtype": "wave_diagram",
  "params": {
    "amplitude": 80,
    "wavelength_px": 160,
    "num_cycles": 2.5,
    "label_amplitude": true,
    "label_wavelength": true
  }
}
```

---

### Chemistry Diagrams

#### `organic_structure` (SMILES)
```json
{
  "diagram_type": "chemistry",
  "subtype": "organic_structure",
  "params": {
    "smiles": "CC(=O)O",
    "name": "Acetic Acid"
  }
}
```
> Requires `rdkit-pypi` for actual structure rendering; falls back to SMILES text display.

#### `inorganic_structure`
```json
{
  "diagram_type": "chemistry",
  "subtype": "inorganic_structure",
  "params": {
    "atoms": [
      { "symbol": "N", "label": "N" },
      { "symbol": "H", "label": "H" },
      { "symbol": "H", "label": "H" },
      { "symbol": "H", "label": "H" }
    ],
    "bonds": [
      { "from_atom": 0, "to_atom": 1, "bond_type": "single" },
      { "from_atom": 0, "to_atom": 2, "bond_type": "single" },
      { "from_atom": 0, "to_atom": 3, "bond_type": "single" }
    ],
    "title": "Ammonia (NH₃)"
  }
}
```

#### `reaction_coordinate_graph`
```json
{
  "diagram_type": "chemistry",
  "subtype": "reaction_coordinate_graph",
  "params": {
    "reactant_label": "A + B",
    "product_label": "C + D",
    "reactant_energy": 0,
    "product_energy": -50,
    "activation_energy": 100,
    "label_delta_h": true,
    "label_ea": true
  }
}
```

#### `orbital_diagram`
```json
{
  "diagram_type": "chemistry",
  "subtype": "orbital_diagram",
  "params": {
    "element": "Oxygen",
    "electron_config": [
      { "shell": "1s", "electrons": 2, "max_electrons": 2, "sublevel_count": 1 },
      { "shell": "2s", "electrons": 2, "max_electrons": 2, "sublevel_count": 1 },
      { "shell": "2p", "electrons": 4, "max_electrons": 6, "sublevel_count": 3 }
    ]
  }
}
```

---

### Mathematics Diagrams

#### `function_graph`
```json
{
  "diagram_type": "mathematics",
  "subtype": "function_graph",
  "params": {
    "functions": [
      { "expression": "x**2 - 4", "label": "f(x) = x² - 4", "x_range": [-4, 4] },
      { "expression": "2*x + 1", "label": "g(x) = 2x+1", "x_range": [-4, 4] }
    ],
    "x_range": [-5, 5],
    "grid": true
  }
}
```

#### `geometry_triangle`
```json
{
  "diagram_type": "mathematics",
  "subtype": "geometry_triangle",
  "params": {
    "vertices": [
      { "label": "A", "x": 0, "y": 0 },
      { "label": "B", "x": 6, "y": 0 },
      { "label": "C", "x": 3, "y": 4 }
    ],
    "sides": [
      { "label": "a" },
      { "label": "b" },
      { "label": "c" }
    ],
    "angles": [null, null, 90],
    "show_right_angle": true
  }
}
```

#### `calculus_graph`
```json
{
  "diagram_type": "mathematics",
  "subtype": "calculus_graph",
  "params": {
    "function": "x**3 - 3*x",
    "x_range": [-3, 3],
    "shaded_regions": [
      { "x_from": -1.73, "x_to": 0, "label": "A₁", "color": "lightblue" },
      { "x_from": 0, "x_to": 1.73, "label": "A₂", "color": "lightcoral" }
    ],
    "show_derivative": true,
    "label_zeros": true,
    "label_extrema": true
  }
}
```

---

### Circuit Diagrams

#### `resistor_network`
```json
{
  "diagram_type": "circuits",
  "subtype": "resistor_network",
  "params": {
    "topology": "series",
    "resistors": ["R₁=2Ω", "R₂=3Ω", "R₃=5Ω"],
    "voltage_source": "12V",
    "show_current": true,
    "equivalent_label": true
  }
}
```

#### `basic_dc_circuit`
```json
{
  "diagram_type": "circuits",
  "subtype": "basic_dc_circuit",
  "params": {
    "components": [
      { "type": "battery", "value": "9V", "direction": "up" },
      { "type": "resistor", "label": "R₁", "value": "100Ω", "direction": "right" },
      { "type": "switch", "direction": "right" },
      { "type": "resistor", "label": "R₂", "value": "47Ω", "direction": "down" }
    ],
    "title": "Simple Loop Circuit",
    "show_current_direction": true
  }
}
```

---

## Dependency Matrix

| Feature | Library | Required |
|---------|---------|----------|
| Physics diagrams | `svgwrite` | ✅ Required |
| Math diagrams | `matplotlib`, `numpy`, `sympy` | ✅ Required |
| PDF export | `reportlab` | ✅ Required |
| Validation | `pydantic` | ✅ Required |
| Circuit diagrams | `schemdraw` | ⚠️ Optional (svgwrite fallback) |
| Organic chemistry | `rdkit-pypi` | ⚠️ Optional (text fallback) |
| SVG→PNG export | `cairosvg` | ⚠️ Optional (Pillow fallback) |

---

## Admin Panel

Visit `/admin/` to:
- **Browse rendered diagrams** — with inline SVG preview
- **Filter failures** — by status, diagram type
- **Retry failed renders** — bulk action
- **Manage templates** — pre-seeded diagram schemas

---

## Testing

```bash
# All diagram tests
python manage.py test diagrams

# Specific suites
python manage.py test diagrams.tests.test_validators   # 18 tests
python manage.py test diagrams.tests.test_renderers    # 38 tests
python manage.py test diagrams.tests.test_api          # 13 tests
python manage.py test diagrams.tests.test_pdf          # 6 tests
```

---

## File Structure

```
diagrams/
├── models.py                         ← DiagramTemplate, RenderedDiagram, RenderingJob
├── admin.py                          ← Admin with SVG preview + retry actions
├── apps.py
├── urls.py                           ← /render/, /validate/, /pdf/, /types/
├── urls_health.py                    ← /health/
├── processor/
│   └── diagramprocessor.py           ← marshmallow request schemas
├── controller/
│   └── diagramcontroller.py          ← HTTP handlers
├── service/
│   ├── dispatcher.py                 ← validate → route → render → save
│   ├── physics/renderer.py           ← svgwrite physics engine (8 types)
│   ├── chemistry/renderer.py         ← rdkit + matplotlib chemistry (4 types)
│   ├── mathematics/renderer.py       ← matplotlib math engine (5 types)
│   ├── circuits/renderer.py          ← schemdraw + svgwrite circuits (3 types)
│   └── pdf/composer.py              ← ReportLab PDF composer
├── schemas/
│   ├── base.py                       ← Master DiagramSchema
│   ├── physics.py                    ← Physics sub-schemas
│   ├── chemistry.py                  ← Chemistry sub-schemas
│   ├── mathematics.py                ← Mathematics sub-schemas
│   └── circuits.py                   ← Circuits sub-schemas
├── validators/
│   └── schema_validator.py           ← Two-phase Pydantic validation
└── tests/
    ├── test_validators.py            ← 18 tests
    ├── test_renderers.py             ← 38 tests
    ├── test_api.py                   ← 13 tests
    └── test_pdf.py                   ← 6 tests
```
