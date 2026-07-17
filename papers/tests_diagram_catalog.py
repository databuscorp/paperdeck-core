"""The three subtype lists must agree, and every catalog example must actually render.

Only three places know which diagrams exist:
  1. the renderer registries        (diagrams/service/<domain>/renderer.py)
  2. the validator registry         (diagrams/validators/schema_validator.py::_SUBTYPE_SCHEMAS)
  3. the LLM prompt catalog         (papers/service/aigeneratorservice.py::_DIAGRAM_SCHEMA_HINT)

Drift between them is the failure mode of this whole subsystem, and it is INVISIBLE:
  - a renderer missing from the catalog is dead code — the model is never told it exists, so it
    is never used, and nobody notices we paid to build it;
  - a catalog entry missing from the validator is a guaranteed hard failure at generation time;
  - a catalog EXAMPLE that doesn't render teaches the model a shape that always fails, and it will
    keep emitting it, burning the repair loop on every image-based question.

These tests are the reason the wiring can be trusted. They are deliberately derived from the code
rather than from a hand-maintained list, so they cannot go stale.
"""
from __future__ import annotations

import json
import re

from django.test import SimpleTestCase

from diagrams.service.biology.renderer import BIOLOGY_RENDERERS
from diagrams.service.chemistry.renderer import CHEMISTRY_RENDERERS
from diagrams.service.circuits.renderer import CIRCUIT_RENDERERS
from diagrams.service.mathematics.renderer import MATHEMATICS_RENDERERS
from diagrams.service.physics.renderer import PHYSICS_RENDERERS
from diagrams.validators.schema_validator import _SUBTYPE_SCHEMAS
from papers.service.aigeneratorservice import _DIAGRAM_SCHEMA_HINT

RENDERERS = {
    "physics": PHYSICS_RENDERERS,
    "chemistry": CHEMISTRY_RENDERERS,
    "mathematics": MATHEMATICS_RENDERERS,
    "circuits": CIRCUIT_RENDERERS,
    "biology": BIOLOGY_RENDERERS,
}


_RAW_LINES = re.findall(r'^\s*(\{"diagram_type".*\})\s*$', _DIAGRAM_SCHEMA_HINT, re.M)


def _catalog_lines() -> list[tuple[str, dict | None]]:
    """Every catalog line, paired with its parse (None if it is not valid JSON)."""
    out: list[tuple[str, dict | None]] = []
    for raw in _RAW_LINES:
        try:
            out.append((raw, json.loads(raw)))
        except json.JSONDecodeError:
            out.append((raw, None))
    return out


def _catalog_examples() -> list[dict]:
    return [ex for _, ex in _catalog_lines() if ex is not None]


def _catalog_subtypes() -> dict[str, set[str]]:
    """Subtypes named in the catalog. Read from the raw text, so a line that fails to parse
    still counts as 'advertised' — otherwise a broken example would masquerade as a missing one."""
    by_domain: dict[str, set[str]] = {}
    for raw in _RAW_LINES:
        m = re.search(r'"diagram_type":"(\w+)".*?"subtype":"(\w+)"', raw)
        if m:
            by_domain.setdefault(m.group(1), set()).add(m.group(2))
    return by_domain


class CatalogParityTests(SimpleTestCase):

    def test_every_renderer_is_registered_in_the_validator(self):
        """A renderer with no schema can never be validated, so it can never be rendered."""
        for domain, registry in RENDERERS.items():
            validator = set(_SUBTYPE_SCHEMAS.get(domain, {}))
            missing = set(registry) - validator
            self.assertFalse(
                missing, f"{domain}: renderers with no validator schema: {sorted(missing)}")

    def test_every_validator_schema_has_a_renderer(self):
        """A schema with no renderer validates and then dies in dispatch_render."""
        for domain, registry in RENDERERS.items():
            validator = set(_SUBTYPE_SCHEMAS.get(domain, {}))
            missing = validator - set(registry)
            self.assertFalse(
                missing, f"{domain}: validator schemas with no renderer: {sorted(missing)}")

    def test_every_subtype_is_advertised_to_the_model(self):
        """THE expensive one. A subtype absent from the prompt catalog is dead code: the model is
        never told it exists, so it is never emitted, so the renderer never runs."""
        catalog = _catalog_subtypes()
        for domain, registry in RENDERERS.items():
            missing = set(registry) - catalog.get(domain, set())
            self.assertFalse(
                missing, f"{domain}: built but never advertised to the model: {sorted(missing)}")

    def test_the_catalog_advertises_nothing_that_does_not_exist(self):
        """A catalog entry with no renderer is a guaranteed failure on every use."""
        for domain, subtypes in _catalog_subtypes().items():
            self.assertIn(domain, RENDERERS, f"catalog names unknown domain '{domain}'")
            unknown = subtypes - set(RENDERERS[domain])
            self.assertFalse(
                unknown, f"{domain}: advertised to the model but not implemented: {sorted(unknown)}")


class CatalogExamplesRenderTests(SimpleTestCase):
    """Every example in the prompt is a worked demonstration we hand the model. If one of them
    does not render, we are actively teaching the model to emit a broken shape."""

    def test_the_catalog_is_not_empty(self):
        self.assertGreater(len(_catalog_examples()), 50)

    def test_every_catalog_line_is_concrete_valid_json(self):
        """The catalog originally shipped pseudo-JSON templates — {"angle":<deg 1-89>},
        {"smiles":"<SMILES string>"}. Two costs: the model is shown a shape it must never copy
        literally (and sometimes does), and nothing downstream can machine-check that the example
        actually renders. Every example must be a concrete, working call."""
        unparseable = [raw for raw, ex in _catalog_lines() if ex is None]
        self.assertFalse(
            unparseable,
            "catalog lines that are not valid JSON (placeholders must be concrete values):\n"
            + "\n".join(unparseable))

    def test_every_catalog_example_validates_and_renders(self):
        from diagrams.service.dispatcher import dispatch_render

        failures = []
        for ex in _catalog_examples():
            label = f"{ex['diagram_type']}/{ex['subtype']}"
            try:
                validation, result = dispatch_render(ex, save_files=False)
                if not validation.valid:
                    failures.append(f"{label}: INVALID: {validation.errors}")
                elif not result.success:
                    failures.append(f"{label}: RENDER FAILED: {result.error[:200]}")
                elif "<svg" not in result.svg_content:
                    failures.append(f"{label}: produced no SVG")
            except Exception as exc:  # noqa: BLE001 - report, don't abort the sweep
                failures.append(f"{label}: RAISED {type(exc).__name__}: {exc}")

        self.assertFalse(failures, "catalog examples that do not work:\n" + "\n".join(failures))
