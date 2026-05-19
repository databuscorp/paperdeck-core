import json
import os
import time

import anthropic


HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

EXAM_CONFIGS = {
    "NEET": {
        "total_questions": 180,
        "sections": [
            {"subject": "Physics", "questions": 45, "marks_per_q": 4, "negative": -1},
            {"subject": "Chemistry", "questions": 45, "marks_per_q": 4, "negative": -1},
            {"subject": "Botany", "questions": 45, "marks_per_q": 4, "negative": -1},
            {"subject": "Zoology", "questions": 45, "marks_per_q": 4, "negative": -1},
        ],
    },
    "JEE Mains": {
        "total_questions": 90,
        "sections": [
            {"subject": "Physics", "questions": 30, "marks_per_q": 4, "negative": -1},
            {"subject": "Chemistry", "questions": 30, "marks_per_q": 4, "negative": -1},
            {"subject": "Mathematics", "questions": 30, "marks_per_q": 4, "negative": -1},
        ],
    },
    "JEE Advanced": {
        "total_questions": 54,
        "sections": [
            {"subject": "Physics", "questions": 18, "marks_per_q": 3, "negative": -1},
            {"subject": "Chemistry", "questions": 18, "marks_per_q": 3, "negative": -1},
            {"subject": "Mathematics", "questions": 18, "marks_per_q": 3, "negative": -1},
        ],
    },
}


def _build_generation_prompt(exam_type: str, subjects: list, difficulty: str, total_marks: int) -> str:
    config = EXAM_CONFIGS.get(exam_type, {})
    sections_info = ""
    if config:
        for s in config.get("sections", []):
            if not subjects or s["subject"] in subjects:
                sections_info += f"- {s['subject']}: {s['questions']} questions, {s['marks_per_q']} marks each\n"

    return f"""Generate a complete {exam_type} question paper with the following specifications:
Difficulty: {difficulty}
Total Marks: {total_marks}
Subjects: {', '.join(subjects) if subjects else 'all standard subjects'}

{f'Section breakdown:{chr(10)}{sections_info}' if sections_info else ''}

Return ONLY a valid JSON object with this exact structure:
{{
  "sections": [
    {{
      "subject": "Subject Name",
      "questions": [
        {{
          "number": 1,
          "text": "Question text here",
          "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
          "correct_answer": "A",
          "marks": 4,
          "negative_marks": -1,
          "topic": "specific topic",
          "explanation": "Brief explanation of the answer"
        }}
      ]
    }}
  ],
  "total_marks": {total_marks},
  "exam_type": "{exam_type}"
}}

Generate realistic, high-quality MCQ questions appropriate for {exam_type}. Each question must have exactly 4 options labeled A, B, C, D. Include only questions from standard {exam_type} syllabus."""


def _build_crosscheck_prompt(section_json: dict, subject: str) -> str:
    return f"""Review these {subject} questions from a {section_json.get('exam_type', 'competitive exam')} paper.
Identify any questions that have: incorrect answers, ambiguous options, factual errors, or poor wording.

Questions to review:
{json.dumps(section_json, indent=2)}

Return the same JSON structure with corrections applied. Fix any errors found. Return ONLY valid JSON, no explanation text."""


class AIGeneratorService:

    def __init__(self):
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else None

    def generate_paper(self, exam_type: str, subjects: list, difficulty: str, total_marks: int) -> dict:
        if not self._client:
            return self._mock_paper(exam_type, subjects, total_marks)

        prompt = _build_generation_prompt(exam_type, subjects, difficulty, total_marks)
        message = self._client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}]
        )
        content = message.content[0].text
        paper_data = json.loads(content)

        flagged_sections = self._flag_risky_sections(paper_data)
        if flagged_sections:
            paper_data = self._crosscheck_with_sonnet(paper_data, flagged_sections, exam_type)

        return paper_data

    def _flag_risky_sections(self, paper_data: dict) -> list:
        risky = []
        for section in paper_data.get("sections", []):
            subject = section.get("subject", "")
            if subject in ["Physics", "Mathematics"]:
                risky.append(section)
        return risky

    def _crosscheck_with_sonnet(self, paper_data: dict, flagged_sections: list, exam_type: str) -> dict:
        for i, section in enumerate(paper_data.get("sections", [])):
            if section in flagged_sections:
                prompt = _build_crosscheck_prompt({**section, "exam_type": exam_type}, section.get("subject"))
                message = self._client.messages.create(
                    model=SONNET_MODEL,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}]
                )
                corrected = json.loads(message.content[0].text)
                paper_data["sections"][i] = corrected
        return paper_data

    # Max questions per single API call — keeps output tokens well under limit
    _BATCH_SIZE = 10
    # Seconds to wait between batches to stay under 10k output tokens/minute
    _INTER_BATCH_DELAY = 6

    def generate_questions(self, exam: str, subject: str, topic: str, q_type: str,
                           difficulty: str, bloom: str, count: int) -> list:
        if not self._client:
            return self._mock_questions(exam, subject, topic, q_type, difficulty, bloom, count)

        if count <= self._BATCH_SIZE:
            return self._generate_batch(exam, subject, topic, q_type, difficulty, bloom, count)

        results = []
        remaining = count
        while remaining > 0:
            batch = min(remaining, self._BATCH_SIZE)
            if results:
                time.sleep(self._INTER_BATCH_DELAY)
            results.extend(self._generate_batch(exam, subject, topic, q_type, difficulty, bloom, batch))
            remaining -= batch
        return results

    def _generate_batch(self, exam: str, subject: str, topic: str, q_type: str,
                        difficulty: str, bloom: str, count: int, _retry: int = 0) -> list:
        is_image_based = q_type == "Image Based"

        if q_type in ("MCQ", "Image Based"):
            options_instruction = (
                '"options": [{"text": "Option A text", "correct": true}, '
                '{"text": "Option B text", "correct": false}, '
                '{"text": "Option C text", "correct": false}, '
                '{"text": "Option D text", "correct": false}],'
            )
        else:
            options_instruction = '"options": null,'

        image_field = (
            '"image_description": "One-line label for the diagram (e.g. Ray diagram of a concave lens).",'
            '"image_svg": "Complete inline SVG markup. RULES: (1) Use single quotes for ALL XML attributes. (2) viewBox=\'0 0 400 280\' xmlns=\'http://www.w3.org/2000/svg\'. (3) No newlines — write the entire SVG as one line. (4) Use only rect, circle, line, polyline, path, text, ellipse elements. (5) Draw a clear, labelled scientific diagram relevant to the question (e.g. circuit with resistors and battery, lens with rays, cell diagram, force diagram). (6) Black strokes on white background. Example start: <svg viewBox=\'0 0 400 280\' xmlns=\'http://www.w3.org/2000/svg\'><rect width=\'400\' height=\'280\' fill=\'white\'/>...</svg>",'
            if is_image_based else
            '"image_description": null, "image_svg": null,'
        )

        diff_instruction = "" if difficulty == "Mixed" else f"Difficulty: {difficulty}."
        bloom_instruction = "" if bloom == "Mixed" else f"Bloom's level: {bloom}."

        q_type_label = "MCQ" if is_image_based else q_type
        type_note = (
            "These are diagram/figure-based MCQs. Each question must reference a specific diagram or figure. "
            "Write the question text as if the student is looking at the described figure."
            if is_image_based else ""
        )

        prompt = f"""Generate exactly {count} {q_type_label} questions for the {exam} exam.
Subject: {subject}
Topic: {topic or 'General'}
{diff_instruction} {bloom_instruction}
{type_note}

Return ONLY a valid JSON array with no markdown or extra text. Each element:
{{
  "exam": "{exam}",
  "subject": "{subject}",
  "topic": "{topic or 'General'}",
  "q_type": "{q_type}",
  "difficulty": "Easy|Medium|Hard|HOTS",
  "bloom": "Remember|Understand|Apply|Analyze|Evaluate|Create",
  "marks": 4,
  "text": "Question text here",
  {image_field}
  {options_instruction}
  "explanation": "One sentence explanation"
}}

Return exactly {count} questions as a JSON array. Keep explanations concise (one sentence)."""

        try:
            message = self._client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}]
            )
            return self._parse_questions_response(message.content[0].text.strip())
        except anthropic.RateLimitError:
            if _retry >= 4:
                raise
            wait = (2 ** _retry) * 15  # 15s, 30s, 60s, 120s
            time.sleep(wait)
            return self._generate_batch(exam, subject, topic, q_type, difficulty, bloom, count, _retry + 1)

    @staticmethod
    def _parse_questions_response(raw: str) -> list:
        # Strip markdown code fences
        if raw.startswith("```"):
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1:
                raw = raw[start:end + 1]
        elif not raw.startswith("["):
            # Find the JSON array anywhere in the response
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1:
                raw = raw[start:end + 1]
        return json.loads(raw)

    def _mock_questions(self, exam: str, subject: str, topic: str, q_type: str,
                        difficulty: str, bloom: str, count: int) -> list:
        questions = []
        for i in range(count):
            q = {
                "exam": exam,
                "subject": subject,
                "topic": topic or "General",
                "q_type": q_type,
                "difficulty": difficulty if difficulty != "Mixed" else "Medium",
                "bloom": bloom if bloom != "Mixed" else "Apply",
                "marks": 4,
                "text": f"[{subject}] Sample {q_type} question {i + 1} for {exam}.",
                "options": None,
                "explanation": "Sample explanation.",
            }
            if q_type == "MCQ":
                q["options"] = [
                    {"text": "Option A", "correct": True},
                    {"text": "Option B", "correct": False},
                    {"text": "Option C", "correct": False},
                    {"text": "Option D", "correct": False},
                ]
            questions.append(q)
        return questions

    def _mock_paper(self, exam_type: str, subjects: list, total_marks: int) -> dict:
        config = EXAM_CONFIGS.get(exam_type, EXAM_CONFIGS["NEET"])
        sections = []
        for sec_conf in config["sections"]:
            subject = sec_conf["subject"]
            if subjects and subject not in subjects:
                continue
            questions = []
            for i in range(1, sec_conf["questions"] + 1):
                questions.append({
                    "number": i,
                    "text": f"[{subject}] Sample question {i} for {exam_type}?",
                    "options": [
                        "A) Option A", "B) Option B", "C) Option C", "D) Option D"
                    ],
                    "correct_answer": "A",
                    "marks": sec_conf["marks_per_q"],
                    "negative_marks": sec_conf["negative"],
                    "topic": f"{subject} Topic {i}",
                    "explanation": "Sample explanation."
                })
            sections.append({"subject": subject, "questions": questions})
        return {"sections": sections, "total_marks": total_marks, "exam_type": exam_type}
