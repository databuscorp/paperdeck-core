"""
Unit tests for the PDF composer.
"""
from django.test import TestCase


class TestPDFComposer(TestCase):
    def _minimal_paper(self):
        return {
            "title": "Test Paper",
            "exam_name": "Test Exam",
            "duration_minutes": 60,
            "total_marks": 100,
            "instructions": ["Answer all questions."],
            "sections": [
                {
                    "name": "Section 1",
                    "questions": [
                        {
                            "number": 1,
                            "text": "What is 2 + 2?",
                            "options": [
                                {"text": "3", "correct": False},
                                {"text": "4", "correct": True},
                                {"text": "5", "correct": False},
                                {"text": "6", "correct": False},
                            ],
                            "marks": 4,
                            "negative_marks": -1,
                        }
                    ],
                }
            ],
        }

    def test_generate_paper_pdf_returns_bytes(self):
        from diagrams.service.pdf.composer import generate_paper_pdf
        pdf = generate_paper_pdf(self._minimal_paper())
        self.assertIsInstance(pdf, bytes)
        self.assertGreater(len(pdf), 100)

    def test_pdf_has_pdf_header(self):
        from diagrams.service.pdf.composer import generate_paper_pdf
        pdf = generate_paper_pdf(self._minimal_paper())
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_generate_with_diagram(self):
        from diagrams.service.pdf.composer import generate_paper_pdf
        paper = self._minimal_paper()
        # Add a simple inline SVG diagram to the first question
        paper["sections"][0]["questions"][0]["diagram_svg"] = (
            '<svg width="400" height="280" xmlns="http://www.w3.org/2000/svg">'
            '<rect width="400" height="280" fill="white"/>'
            '<line x1="10" y1="140" x2="390" y2="140" stroke="black" stroke-width="2"/>'
            '<text x="200" y="130" text-anchor="middle">Test Diagram</text>'
            '</svg>'
        )
        pdf = generate_paper_pdf(paper)
        self.assertIsInstance(pdf, bytes)
        self.assertGreater(len(pdf), 100)

    def test_empty_paper(self):
        from diagrams.service.pdf.composer import generate_paper_pdf
        paper = {
            "title": "Empty",
            "sections": [],
        }
        pdf = generate_paper_pdf(paper)
        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_generate_diagram_pdf(self):
        from diagrams.service.pdf.composer import generate_diagram_pdf
        pdf = generate_diagram_pdf({
            "title": "Inclined Plane",
            "svg_content": (
                '<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">'
                '<rect width="800" height="600" fill="white"/>'
                '<polygon points="100,500 700,500 100,100" '
                'stroke="black" stroke-width="2" fill="#f0f0f0"/>'
                '</svg>'
            ),
            "description": "Test inclined plane diagram",
        })
        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_multiple_sections(self):
        from diagrams.service.pdf.composer import generate_paper_pdf
        paper = {
            "title": "Multi-Section Test",
            "duration_minutes": 180,
            "total_marks": 360,
            "sections": [
                {
                    "name": f"Section {i} - Subject {i}",
                    "questions": [
                        {
                            "number": j,
                            "text": f"Question {j} in section {i}",
                            "marks": 4,
                            "options": [
                                {"text": f"Option {k}", "correct": k == 0}
                                for k in range(4)
                            ],
                        }
                        for j in range(1, 4)
                    ],
                }
                for i in range(1, 4)
            ],
        }
        pdf = generate_paper_pdf(paper)
        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF"))
