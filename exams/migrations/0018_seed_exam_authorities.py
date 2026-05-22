from django.db import migrations

AUTHORITIES = [
    {
        "name": "National Testing Agency",
        "short_name": "NTA",
        "authority_type": "govt",
        "description": "Central government agency that conducts entrance examinations for admission to higher educational institutions.",
        "website": "https://nta.ac.in",
    },
    {
        "name": "Joint Admission Board",
        "short_name": "JAB",
        "authority_type": "institution",
        "description": "Governing body of the IITs responsible for conducting JEE Advanced for admission to IITs.",
        "website": "https://jeeadv.ac.in",
    },
    {
        "name": "Union Public Service Commission",
        "short_name": "UPSC",
        "authority_type": "govt",
        "description": "Constitutional body of India responsible for civil services examinations including IAS, IPS, and IFS.",
        "website": "https://upsc.gov.in",
    },
    {
        "name": "Staff Selection Commission",
        "short_name": "SSC",
        "authority_type": "govt",
        "description": "Government organisation that recruits staff for various posts in ministries, departments, and organisations under the Government of India.",
        "website": "https://ssc.nic.in",
    },
    {
        "name": "Consortium of National Law Universities",
        "short_name": "Consortium NLU",
        "authority_type": "institution",
        "description": "Body comprising all National Law Universities that conducts CLAT for admission to undergraduate and postgraduate law programmes.",
        "website": "https://consortiumofnlus.ac.in",
    },
    {
        "name": "Indian Institutes of Management",
        "short_name": "IIMs",
        "authority_type": "institution",
        "description": "Premier management institutions that jointly conduct CAT for admission to MBA and other management programmes.",
        "website": "https://iimcat.ac.in",
    },
    {
        "name": "IITs & IISc",
        "short_name": "IIT/IISc",
        "authority_type": "institution",
        "description": "Indian Institutes of Technology and Indian Institute of Science jointly conduct GATE for engineering and science graduates.",
        "website": "https://gate.iitb.ac.in",
    },
    {
        "name": "XLRI – Xavier School of Management",
        "short_name": "XLRI",
        "authority_type": "institution",
        "description": "Premier management institution that conducts XAT for admission to its management programmes.",
        "website": "https://xlri.ac.in",
    },
    {
        "name": "Graduate Management Admission Council",
        "short_name": "GMAC",
        "authority_type": "institution",
        "description": "International organisation that owns and administers the GMAT and NMAT exams for business school admissions.",
        "website": "https://gmac.com",
    },
    {
        "name": "Symbiosis International University",
        "short_name": "SIU",
        "authority_type": "university",
        "description": "Deemed university that conducts SNAP for admission to Symbiosis institutes' MBA programmes.",
        "website": "https://www.snaptest.org",
    },
    {
        "name": "Indian Institute of Foreign Trade",
        "short_name": "IIFT",
        "authority_type": "institution",
        "description": "Autonomous institution under the Ministry of Commerce that conducts the IIFT entrance exam for MBA in International Business.",
        "website": "https://iift.edu",
    },
    {
        "name": "Tata Institute of Social Sciences",
        "short_name": "TISS",
        "authority_type": "institution",
        "description": "Deemed university that conducts TISSNET for admission to its social sciences and management programmes.",
        "website": "https://tiss.edu",
    },
    {
        "name": "All India Management Association",
        "short_name": "AIMA",
        "authority_type": "institution",
        "description": "Apex body of management profession in India that conducts the MAT (Management Aptitude Test) four times a year.",
        "website": "https://aima.in",
    },
    {
        "name": "National Board of Examinations in Medical Sciences",
        "short_name": "NBEMS",
        "authority_type": "govt",
        "description": "Autonomous body under Ministry of Health that conducts NEET PG and other postgraduate medical entrance examinations.",
        "website": "https://natboard.edu.in",
    },
    {
        "name": "Educational Testing Service",
        "short_name": "ETS",
        "authority_type": "institution",
        "description": "US-based non-profit organisation that develops and administers the GRE for graduate school admissions worldwide.",
        "website": "https://ets.org",
    },
]


def seed_authorities(apps, schema_editor):
    ExamAuthority = apps.get_model('exams', 'ExamAuthority')
    for data in AUTHORITIES:
        ExamAuthority.objects.get_or_create(
            short_name=data["short_name"],
            defaults={
                "name":           data["name"],
                "authority_type": data["authority_type"],
                "description":    data["description"],
                "website":        data["website"],
                "is_active":      True,
            }
        )


def remove_authorities(apps, schema_editor):
    ExamAuthority = apps.get_model('exams', 'ExamAuthority')
    ExamAuthority.objects.filter(
        short_name__in=[a["short_name"] for a in AUTHORITIES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0017_add_exam_authority'),
    ]

    operations = [
        migrations.RunPython(seed_authorities, remove_authorities),
    ]
