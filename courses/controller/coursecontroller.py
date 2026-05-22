import json
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view

from courses.models import Course
from courses.processor.courseprocessor import course_req_schema
from courses.service.courseservice import CourseService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


@csrf_exempt
@api_view(['GET', 'POST', 'DELETE'])
@auth_required
@transaction.atomic
def courses(request):
    if request.method == 'GET':
        return _fetch_courses(request)
    elif request.method == 'POST':
        return _post_course(request)
    elif request.method == 'DELETE':
        return _delete_course(request)


def _fetch_courses(request):
    scope = request.scope
    user_id = scope['user_id']
    org_id = scope.get('org_id')
    course_id = request.query_params.get('course_id')
    service = CourseService(scope)

    if course_id:
        resp = service.fetch_course(course_id, user_id, org_id=org_id)
        if isinstance(resp, ErrorResponse):
            return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
        return HttpResponse(resp.to_json(), content_type='application/json')

    resp_list = service.fetch_courses(user_id, org_id=org_id)
    return HttpResponse(json.dumps([c.to_dict() for c in resp_list]), content_type='application/json')


def _post_course(request):
    scope = request.scope
    if scope.get('role') != 1:
        return HttpResponse(
            ErrorResponse(status=403, message='Admin access required').to_json(),
            status=403, content_type='application/json'
        )
    user_id = scope['user_id']
    org_id = scope.get('org_id')
    obj = course_req_schema.load(request.data)
    service = CourseService(scope)
    resp = service.create_or_update_course(obj, user_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


def _delete_course(request):
    scope = request.scope
    if scope.get('role') != 1:
        return HttpResponse(
            ErrorResponse(status=403, message='Admin access required').to_json(),
            status=403, content_type='application/json'
        )
    user_id = scope['user_id']
    org_id = scope.get('org_id')
    course_id = request.query_params.get('course_id')
    if not course_id:
        return HttpResponse(
            ErrorResponse(status=400, message='course_id is required').to_json(),
            status=400, content_type='application/json'
        )
    service = CourseService(scope)
    resp = service.delete_course(course_id, user_id, org_id=org_id)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['POST', 'DELETE'])
@auth_required
@transaction.atomic
def subscription(request):
    scope = request.scope
    if scope.get('role') != 1:
        return HttpResponse(
            ErrorResponse(status=403, message='Admin access required').to_json(),
            status=403, content_type='application/json'
        )
    user_id = scope['user_id']
    org_id = scope.get('org_id')
    service = CourseService(scope)

    if request.method == 'POST':
        course_id = request.data.get('course_id')
        if not course_id:
            return HttpResponse(
                ErrorResponse(status=400, message='course_id is required').to_json(),
                status=400, content_type='application/json'
            )
        resp = service.subscribe(course_id, org_id=org_id, user_id=user_id)
    else:
        course_id = request.query_params.get('course_id')
        if not course_id:
            return HttpResponse(
                ErrorResponse(status=400, message='course_id is required').to_json(),
                status=400, content_type='application/json'
            )
        resp = service.unsubscribe(course_id, org_id=org_id, user_id=user_id)

    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['GET'])
@auth_required
def dashboard_stats(request):
    from subjects.models import Subject, Topic
    from questions.models import Question
    from papers.models import Paper
    from blueprints.models import Blueprint
    from staff.models import Staff
    from students.models import Student

    scope = request.scope
    org_id = scope.get('org_id')
    user_id = scope['user_id']

    service = CourseService(scope)
    subscribed_ids = service._subscribed_ids(org_id)
    subscribed_courses = Course.objects.filter(id__in=subscribed_ids).select_related('authority').order_by('name')

    today = timezone.now().date()
    week_ago = today - timedelta(days=6)

    # Scoped querysets
    if org_id:
        all_papers     = Paper.objects.filter(org_id=org_id)
        all_questions  = Question.objects.filter(org_id=org_id)
        all_staff      = Staff.objects.filter(org_id=org_id)
        all_students   = Student.objects.filter(org_id=org_id)
        all_blueprints = Blueprint.objects.filter(Q(org_id=org_id) | Q(is_sys=True, course_id__in=subscribed_ids))
    else:
        all_papers     = Paper.objects.filter(owner_id=user_id)
        all_questions  = Question.objects.filter(owner_id=user_id)
        all_staff      = Staff.objects.none()
        all_students   = Student.objects.none()
        all_blueprints = Blueprint.objects.filter(is_sys=True, course_id__in=subscribed_ids)

    # Per-course breakdown
    courses_data = []
    for course in subscribed_courses:
        courses_data.append({
            "id":              str(course.id),
            "name":            course.name,
            "authority_name":  course.authority.name if course.authority else None,
            "subjects_count":  Subject.objects.filter(course_id=course.id).count(),
            "topics_count":    Topic.objects.filter(subject__course_id=course.id).count(),
            "blueprints_count":all_blueprints.filter(course_id=course.id).count(),
            "students_count":  Student.objects.filter(courses__id=course.id).count(),
            "staff_count":     Staff.objects.filter(courses__id=course.id).count(),
            "papers_count":    all_papers.filter(course_id=course.id).count(),
            "questions_count": all_questions.filter(course_id=course.id).count(),
        })

    # Papers by course (for pie chart)
    papers_by_course = [
        {"name": r["course__name"] or "Uncategorized", "count": r["count"]}
        for r in (
            all_papers.filter(course_id__in=subscribed_ids)
            .values("course__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
    ]

    # Questions by subject (for bar chart)
    questions_by_subject = [
        {"subject": r["subject"], "count": r["count"]}
        for r in (
            all_questions.exclude(subject="")
            .values("subject")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
    ]

    # Papers trend — last 7 days
    trend_qs = (
        all_papers.filter(created_at__date__gte=week_ago)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )
    trend_map = {r["date"].isoformat(): r["count"] for r in trend_qs}
    papers_trend = [
        {"date": (week_ago + timedelta(days=i)).isoformat(),
         "count": trend_map.get((week_ago + timedelta(days=i)).isoformat(), 0)}
        for i in range(7)
    ]

    # Recent papers
    recent_papers = [
        {
            "id":               p.id,
            "title":            p.title,
            "course_name":      p.course.name if p.course else None,
            "total_marks":      p.total_marks,
            "duration_minutes": p.duration_minutes,
            "status":           p.status,
            "created_at":       p.created_at.isoformat(),
        }
        for p in all_papers.select_related("course").order_by("-created_at")[:8]
    ]

    result = {
        "totals": {
            "subscribed_courses": len(subscribed_ids),
            "subjects":           Subject.objects.filter(course_id__in=subscribed_ids).count(),
            "topics":             Topic.objects.filter(subject__course_id__in=subscribed_ids).count(),
            "blueprints":         all_blueprints.count(),
            "students":           all_students.count(),
            "staff":              all_staff.count(),
            "papers":             all_papers.count(),
            "questions":          all_questions.count(),
            "papers_today":       all_papers.filter(created_at__date=today).count(),
        },
        "courses":              courses_data,
        "papers_by_course":     papers_by_course,
        "questions_by_subject": questions_by_subject,
        "papers_trend":         papers_trend,
        "recent_papers":        recent_papers,
    }
    return HttpResponse(json.dumps(result), content_type='application/json')
