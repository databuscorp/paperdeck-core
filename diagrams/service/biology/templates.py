"""Named base artworks for the `labeled_schematic` biology renderer.

This is the config-defined "template layer": each entry is a labelled diagram authored
entirely as DATA — primitive shapes + leader-line labels on a 0–100 grid (top-left origin).
Adding a new "label the parts" diagram means adding a dict here, NOT writing a renderer.

Grid conventions:
  • x and y run 0→100, origin top-left (so authoring reads like a page).
  • shapes: kind ∈ ellipse|circle|rect|polygon|line|path with the fields that kind needs
    (see diagrams/schemas/biology.py SchematicShape).
  • labels: {text, x, y, target:[tx,ty]} — the label box sits at (x,y) and a leader line
    runs to (tx,ty). Omit target for a free-floating caption.

A question can pull a template by name and, by supplying its own `labels`, relabel or blank
the parts (e.g. an unlabelled diagram for students to fill in).
"""

BIOLOGY_TEMPLATES = {
    # ── Plant cell ────────────────────────────────────────────────────────────
    "plant_cell": {
        "title": "Plant Cell",
        "shapes": [
            {"kind": "rect", "x": 22, "y": 14, "w": 50, "h": 72,
             "fill": "#e8f5e9", "stroke": "#388e3c", "stroke_width": 3},      # cell wall
            {"kind": "rect", "x": 25, "y": 17, "w": 44, "h": 66,
             "fill": "#f1f8e9", "stroke": "#e53935", "stroke_width": 1.2},     # membrane
            {"kind": "ellipse", "cx": 48, "cy": 54, "rx": 15, "ry": 22,
             "fill": "#e3f2fd", "stroke": "#42a5f5", "stroke_width": 1.4},     # vacuole
            {"kind": "circle", "cx": 39, "cy": 30, "r": 7,
             "fill": "#ede7f6", "stroke": "#5c35b5", "stroke_width": 1.4},     # nucleus
            {"kind": "circle", "cx": 39, "cy": 30, "r": 2.4,
             "fill": "#7e57c2", "stroke": "#7e57c2", "stroke_width": 0.5},     # nucleolus
            {"kind": "ellipse", "cx": 60, "cy": 34, "rx": 4, "ry": 2.2,
             "fill": "#66bb6a", "stroke": "#2e7d32", "stroke_width": 0.8},     # chloroplast
            {"kind": "ellipse", "cx": 55, "cy": 70, "rx": 4, "ry": 2.2,
             "fill": "#66bb6a", "stroke": "#2e7d32", "stroke_width": 0.8},     # chloroplast
            {"kind": "ellipse", "cx": 33, "cy": 66, "rx": 5, "ry": 2.6,
             "fill": "#ef6c00", "stroke": "#bf360c", "stroke_width": 0.8},     # mitochondrion
        ],
        "labels": [
            {"text": "Cell wall", "x": 90, "y": 17, "target": [72, 20]},
            {"text": "Cell membrane", "x": 90, "y": 31, "target": [69, 33]},
            {"text": "Vacuole", "x": 90, "y": 54, "target": [60, 54]},
            {"text": "Chloroplast", "x": 90, "y": 70, "target": [55, 70]},
            {"text": "Nucleus", "x": 9, "y": 26, "target": [39, 30]},
            {"text": "Mitochondrion", "x": 9, "y": 66, "target": [33, 66]},
        ],
    },

    # ── Animal cell ───────────────────────────────────────────────────────────
    "animal_cell": {
        "title": "Animal Cell",
        "shapes": [
            {"kind": "ellipse", "cx": 47, "cy": 50, "rx": 26, "ry": 30,
             "fill": "#fff3e0", "stroke": "#e53935", "stroke_width": 2.5},     # cell membrane
            {"kind": "circle", "cx": 45, "cy": 44, "r": 9,
             "fill": "#ede7f6", "stroke": "#5c35b5", "stroke_width": 1.5},     # nucleus
            {"kind": "circle", "cx": 45, "cy": 44, "r": 3,
             "fill": "#7e57c2", "stroke": "#7e57c2", "stroke_width": 0.5},     # nucleolus
            {"kind": "ellipse", "cx": 58, "cy": 62, "rx": 5, "ry": 2.6,
             "fill": "#ef6c00", "stroke": "#bf360c", "stroke_width": 0.8},     # mitochondrion
            {"kind": "ellipse", "cx": 34, "cy": 60, "rx": 5, "ry": 2.6,
             "fill": "#ef6c00", "stroke": "#bf360c", "stroke_width": 0.8},     # mitochondrion
            {"kind": "circle", "cx": 55, "cy": 38, "r": 1.1,
             "fill": "#6d4c41", "stroke": "#6d4c41", "stroke_width": 0.4},     # ribosome
            {"kind": "circle", "cx": 52, "cy": 34, "r": 1.1,
             "fill": "#6d4c41", "stroke": "#6d4c41", "stroke_width": 0.4},     # ribosome
        ],
        "labels": [
            {"text": "Cell membrane", "x": 90, "y": 22, "target": [70, 34]},
            {"text": "Nucleus", "x": 9, "y": 40, "target": [45, 44]},
            {"text": "Nucleolus", "x": 90, "y": 46, "target": [46, 44]},
            {"text": "Mitochondrion", "x": 90, "y": 66, "target": [58, 62]},
            {"text": "Cytoplasm", "x": 9, "y": 70, "target": [30, 66]},
        ],
    },

    # ── Neuron ────────────────────────────────────────────────────────────────
    "neuron": {
        "title": "Neuron",
        "shapes": [
            {"kind": "circle", "cx": 24, "cy": 50, "r": 10,
             "fill": "#ede7f6", "stroke": "#5c35b5", "stroke_width": 2},       # soma
            {"kind": "circle", "cx": 24, "cy": 50, "r": 3.5,
             "fill": "#7e57c2", "stroke": "#7e57c2", "stroke_width": 0.5},     # nucleus
            {"kind": "line", "points": [[16, 44], [6, 34]], "stroke": "#5c35b5", "stroke_width": 1.6},
            {"kind": "line", "points": [[15, 50], [4, 50]], "stroke": "#5c35b5", "stroke_width": 1.6},
            {"kind": "line", "points": [[16, 56], [6, 66]], "stroke": "#5c35b5", "stroke_width": 1.6},
            {"kind": "line", "points": [[34, 50], [82, 50]], "stroke": "#5c35b5", "stroke_width": 2.4},  # axon
            {"kind": "ellipse", "cx": 46, "cy": 50, "rx": 5, "ry": 3,
             "fill": "#fff9c4", "stroke": "#f9a825", "stroke_width": 1},       # myelin
            {"kind": "ellipse", "cx": 60, "cy": 50, "rx": 5, "ry": 3,
             "fill": "#fff9c4", "stroke": "#f9a825", "stroke_width": 1},       # myelin
            {"kind": "ellipse", "cx": 74, "cy": 50, "rx": 5, "ry": 3,
             "fill": "#fff9c4", "stroke": "#f9a825", "stroke_width": 1},       # myelin
            {"kind": "line", "points": [[82, 50], [90, 44]], "stroke": "#5c35b5", "stroke_width": 1.4},
            {"kind": "line", "points": [[82, 50], [92, 50]], "stroke": "#5c35b5", "stroke_width": 1.4},
            {"kind": "line", "points": [[82, 50], [90, 56]], "stroke": "#5c35b5", "stroke_width": 1.4},
        ],
        "labels": [
            {"text": "Dendrites", "x": 8, "y": 22, "target": [8, 36]},
            {"text": "Nucleus", "x": 24, "y": 80, "target": [24, 52]},
            {"text": "Cell body", "x": 8, "y": 68, "target": [18, 56]},
            {"text": "Axon", "x": 40, "y": 34, "target": [40, 50]},
            {"text": "Myelin sheath", "x": 66, "y": 30, "target": [60, 47]},
            {"text": "Axon terminals", "x": 90, "y": 74, "target": [88, 55]},
        ],
    },
}
