"""Data migration: normalize existing AI-generated papers' `content` into the
builder's {meta, sections} shape so they round-trip cleanly through the Paper
Builder (Edit), exactly like manually-built and imported papers.

The transformation logic is inlined (not imported from the service) so this
migration stays frozen and independent of future code changes.
"""
import re

from django.db import migrations

_OPT_PREFIX_RE = re.compile(r'^\s*\(?[A-Da-d][\)\.\]]\s*')


def _normalize_options(q):
    raw = q.get('options') or []
    corr = (str(q.get('correct_answer') or '')).strip().upper()[:1]
    out = []
    for oi, o in enumerate(raw):
        letter = chr(65 + oi)
        if isinstance(o, dict):
            text = o.get('text') or o.get('label') or ''
            is_correct = bool(o.get('correct')) or (corr == letter)
        else:
            text = _OPT_PREFIX_RE.sub('', str(o)).strip()
            is_correct = (corr == letter)
        out.append({'id': oi + 1, 'text': text, 'correct': is_correct})
    return out


def _normalize_ai_content(content, paper):
    if not isinstance(content, dict):
        return None
    exam_type = paper.exam_type or ''
    raw_sections = content.get('sections') or []
    sections = []
    for idx, sec in enumerate(raw_sections):
        subject = sec.get('subject') or sec.get('name') or f'Section {idx + 1}'
        questions = []
        for qi, q in enumerate(sec.get('questions') or []):
            questions.append({
                'id':         f'ai-{idx}-{qi}',
                'uid':        f'ai-{idx}-{qi}',
                'exam':       exam_type,
                'subject':    subject,
                'topic':      q.get('topic') or '',
                'type':       q.get('type') or q.get('q_type') or 'MCQ',
                'difficulty': (paper.difficulty or 'medium').capitalize(),
                'bloom':      q.get('bloom') or '',
                'marks':      q.get('marks') or 1,
                'text':       q.get('text') or q.get('question') or '',
                'explanation': q.get('explanation'),
                'diagram':    q.get('diagram') or q.get('image_svg'),
                'images':     q.get('images'),
                'options':    _normalize_options(q),
            })
        sections.append({
            'id':           f'ai-sec-{idx}',
            'name':         subject,
            'instructions': '',
            'markLimit':    sum((qq.get('marks') or 0) for qq in questions),
            'questions':    questions,
        })
    total_marks = content.get('total_marks') or paper.total_marks or sum(s['markLimit'] for s in sections)
    neg = next((q.get('negative_marks') for s in raw_sections
                for q in (s.get('questions') or []) if q.get('negative_marks')), None)
    meta = {
        'title':        paper.title,
        'exam':         exam_type,
        'duration':     f'{paper.duration_minutes or 180} min',
        'totalMarks':   total_marks,
        'date':         '',
        'negMarking':   f'{neg} for each wrong answer' if neg else '',
        'instructions': paper.instructions or '',
    }
    return {'meta': meta, 'sections': sections}


def normalize_ai_papers(apps, schema_editor):
    Paper = apps.get_model('papers', 'Paper')
    for paper in Paper.objects.filter(source='ai'):
        content = paper.content
        # Skip papers that are not raw AI content (already normalized, or empty).
        if not isinstance(content, dict) or 'meta' in content or not content.get('sections'):
            continue
        normalized = _normalize_ai_content(content, paper)
        if normalized:
            paper.content = normalized
            paper.save(update_fields=['content'])


def noop_reverse(apps, schema_editor):
    # Irreversible: the original raw AI shape is not retained. Reverse is a no-op
    # so the migration can still be unapplied without error.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('papers', '0004_fix_course_id_uuid'),
    ]

    operations = [
        migrations.RunPython(normalize_ai_papers, noop_reverse),
    ]
