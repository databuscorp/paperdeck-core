from django.db import migrations

# Each entry: (name, slug, authority_short_name, course_type, grade_level, duration_minutes, total_marks, description)
SYS_COURSES = [
    (
        "NEET UG",
        "neet-ug",
        "NTA",
        "common",
        "Class 11–12",
        200,
        720,
        "National Eligibility cum Entrance Test for admission to MBBS, BDS, AYUSH, and allied undergraduate medical programmes across India.",
    ),
    (
        "JEE Mains",
        "jee-mains",
        "NTA",
        "common",
        "Class 11–12",
        180,
        300,
        "Joint Entrance Examination (Mains) for admission to NITs, IIITs, CFTIs, and as a qualifier for JEE Advanced.",
    ),
    (
        "JEE Advanced Paper 1",
        "jee-advanced-paper-1",
        "JAB",
        "common",
        "Class 11–12",
        180,
        180,
        "JEE Advanced Paper 1 — objective and numerical type questions for admission to IITs.",
    ),
    (
        "JEE Advanced Paper 2",
        "jee-advanced-paper-2",
        "JAB",
        "common",
        "Class 11–12",
        180,
        180,
        "JEE Advanced Paper 2 — includes matching and short-answer type questions for admission to IITs.",
    ),
    (
        "UPSC CSE Prelims Paper 1",
        "upsc-cse-prelims-paper-1",
        "UPSC",
        "common",
        "Graduate",
        120,
        200,
        "UPSC Civil Services Prelims — General Studies Paper 1 covering history, geography, polity, economy, environment, and science.",
    ),
    (
        "UPSC CSE Prelims Paper 2",
        "upsc-cse-prelims-paper-2",
        "UPSC",
        "common",
        "Graduate",
        120,
        200,
        "UPSC Civil Services Prelims — CSAT (Paper 2) covering comprehension, logical reasoning, and quantitative aptitude.",
    ),
    (
        "SSC CGL",
        "ssc-cgl",
        "SSC",
        "common",
        "Graduate",
        60,
        200,
        "SSC Combined Graduate Level Tier 1 — screening test for Group B and Group C posts in various government departments.",
    ),
    (
        "SSC CGL Tier 2",
        "ssc-cgl-tier-2",
        "SSC",
        "common",
        "Graduate",
        135,
        450,
        "SSC CGL Tier 2 — advanced examination covering quantitative abilities, English language, statistics, and general studies.",
    ),
    (
        "CAT",
        "cat",
        "IIMs",
        "common",
        "Graduate",
        120,
        198,
        "Common Admission Test — gateway to IIMs and 1000+ top MBA colleges across India covering VARC, DILR, and QA.",
    ),
    (
        "XAT",
        "xat",
        "XLRI",
        "common",
        "Graduate",
        210,
        100,
        "Xavier Aptitude Test — entrance exam for XLRI and 160+ B-schools, covering decision making, VALR, QA, and GK.",
    ),
    (
        "CLAT",
        "clat",
        "Consortium NLU",
        "common",
        "Class 12",
        120,
        150,
        "Common Law Admission Test (UG) — national entrance test for admission to LLB programmes at 24 National Law Universities.",
    ),
    (
        "CLAT PG",
        "clat-pg",
        "Consortium NLU",
        "common",
        "Graduate",
        120,
        150,
        "Common Law Admission Test (PG) — entrance test for LLM programmes at National Law Universities.",
    ),
    (
        "GATE CS",
        "gate-cs",
        "IIT/IISc",
        "common",
        "Graduate",
        180,
        100,
        "Graduate Aptitude Test in Engineering — Computer Science & Information Technology. Gateway to PSUs and M.Tech admissions.",
    ),
    (
        "GATE ECE",
        "gate-ece",
        "IIT/IISc",
        "common",
        "Graduate",
        180,
        100,
        "Graduate Aptitude Test in Engineering — Electronics & Communication Engineering.",
    ),
    (
        "GATE ME",
        "gate-me",
        "IIT/IISc",
        "common",
        "Graduate",
        180,
        100,
        "Graduate Aptitude Test in Engineering — Mechanical Engineering.",
    ),
    (
        "GATE Civil",
        "gate-civil",
        "IIT/IISc",
        "common",
        "Graduate",
        180,
        100,
        "Graduate Aptitude Test in Engineering — Civil Engineering.",
    ),
    (
        "GATE EE",
        "gate-ee",
        "IIT/IISc",
        "common",
        "Graduate",
        180,
        100,
        "Graduate Aptitude Test in Engineering — Electrical Engineering.",
    ),
    (
        "NEET PG",
        "neet-pg",
        "NBEMS",
        "common",
        "MBBS Graduate",
        210,
        800,
        "National Eligibility cum Entrance Test (PG) — qualifying and ranking exam for MD, MS, and PG Diploma admissions.",
    ),
    (
        "CUET UG",
        "cuet-ug",
        "NTA",
        "common",
        "Class 12",
        150,
        700,
        "Common University Entrance Test (UG) — central entrance exam for admissions to central, state, and private universities.",
    ),
    (
        "CUET PG",
        "cuet-pg",
        "NTA",
        "common",
        "Graduate",
        120,
        400,
        "Common University Entrance Test (PG) — entrance exam for postgraduate admissions to central and participating universities.",
    ),
    (
        "SNAP",
        "snap",
        "SIU",
        "common",
        "Graduate",
        60,
        90,
        "Symbiosis National Aptitude Test — gateway to MBA programmes at 16 Symbiosis institutes.",
    ),
    (
        "NMAT",
        "nmat",
        "GMAC",
        "common",
        "Graduate",
        108,
        108,
        "NMAT by GMAC — entrance exam for NMIMS and 30+ top B-schools, covering language skills, quantitative skills, and logical reasoning.",
    ),
    (
        "IIFT",
        "iift",
        "IIFT",
        "common",
        "Graduate",
        120,
        300,
        "IIFT MBA (International Business) entrance exam covering English, general awareness, logical reasoning, and quantitative analysis.",
    ),
    (
        "TISSNET",
        "tissnet",
        "TISS",
        "common",
        "Graduate",
        100,
        100,
        "TISS National Entrance Test — exam for admission to MA programmes at TISS Mumbai, Hyderabad, Tuljapur, and Guwahati.",
    ),
    (
        "CMAT",
        "cmat",
        "NTA",
        "common",
        "Graduate",
        180,
        400,
        "Common Management Admission Test — national MBA entrance exam for AICTE-approved institutions.",
    ),
    (
        "MAT",
        "mat",
        "AIMA",
        "common",
        "Graduate",
        150,
        200,
        "Management Aptitude Test — conducted four times a year for admission to over 600 B-schools across India.",
    ),
    (
        "GMAT",
        "gmat",
        "GMAC",
        "common",
        "Graduate",
        135,
        805,
        "Graduate Management Admission Test — globally recognised exam for MBA admissions at top business schools worldwide.",
    ),
    (
        "GRE",
        "gre",
        "ETS",
        "common",
        "Graduate",
        118,
        340,
        "Graduate Record Examination — widely accepted for MS, MBA, and PhD admissions at universities across the world.",
    ),
]


def seed_sys_courses(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    ExamAuthority = apps.get_model('exams', 'ExamAuthority')

    authority_map = {
        a.short_name: a
        for a in ExamAuthority.objects.filter(is_sys=True)
    }

    for (name, slug, auth_short, course_type, grade_level,
         duration_minutes, total_marks, description) in SYS_COURSES:

        authority = authority_map.get(auth_short)

        Course.objects.get_or_create(
            slug=slug,
            defaults={
                "name":             name,
                "authority":        authority,
                "org":              None,
                "created_by":       None,
                "course_type":      course_type,
                "grade_level":      grade_level,
                "duration_minutes": duration_minutes,
                "total_marks":      total_marks,
                "description":      description,
                "is_active":        True,
                "is_sys":           True,
            }
        )


def remove_sys_courses(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    Course.objects.filter(
        slug__in=[row[1] for row in SYS_COURSES],
        is_sys=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0005_add_org_to_course'),
        ('exams', '0019_add_is_sys'),
    ]

    operations = [
        migrations.RunPython(seed_sys_courses, remove_sys_courses),
    ]
