"""Demand tracking for unrenderable diagrams (DiagramDemand + record_demand)."""
from django.test import TestCase

from diagrams.models import DiagramDemand
from diagrams.service.demand import record_demand


class RecordDemandTests(TestCase):

    def test_first_sighting_creates_at_count_one(self):
        record_demand("physics", "warp_drive", "unknown subtype 'warp_drive'")
        row = DiagramDemand.objects.get(diagram_type="physics", subtype="warp_drive")
        self.assertEqual(row.count, 1)
        self.assertEqual(row.category, DiagramDemand.CATEGORY_UNKNOWN_SUBTYPE)

    def test_repeat_increments_same_row(self):
        for _ in range(3):
            record_demand("physics", "warp_drive", "unknown subtype 'warp_drive'")
        self.assertEqual(DiagramDemand.objects.count(), 1)
        self.assertEqual(DiagramDemand.objects.get().count, 3)

    def test_unknown_type_categorised(self):
        record_demand("astrology", "natal_chart", "No renderer for diagram_type 'astrology'")
        row = DiagramDemand.objects.get(subtype="natal_chart")
        self.assertEqual(row.category, DiagramDemand.CATEGORY_UNKNOWN_TYPE)

    def test_render_error_categorised_and_kept_separate(self):
        record_demand("physics", "bohr_atom", "num_shells: must be a positive integer")
        record_demand("physics", "bohr_atom", "unknown subtype 'bohr_atom'")
        # Same type/subtype, different failure category → two distinct rows.
        cats = set(DiagramDemand.objects.filter(subtype="bohr_atom")
                   .values_list("category", flat=True))
        self.assertEqual(cats, {DiagramDemand.CATEGORY_RENDER_ERROR,
                                DiagramDemand.CATEGORY_UNKNOWN_SUBTYPE})

    def test_never_raises_on_bad_input(self):
        record_demand(None, None, None)  # must not raise
        self.assertTrue(DiagramDemand.objects.filter(diagram_type="?", subtype="?").exists())
