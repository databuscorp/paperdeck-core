from staff.models import Staff
from staff.processor.staffprocessor import StaffResponse
from utility.dbservice import DBService
from utility.utilityobj import SuccessResponse, ErrorResponse


def _fmt_date(d):
    if d is None:
        return None
    if isinstance(d, str):
        return d
    return d.strftime('%Y-%m-%d')


def _build_staff_response(s: Staff, course_name: str = None) -> StaffResponse:
    return StaffResponse(
        id=s.id,
        course_id=s.course_id,
        name=s.name,
        email=s.email,
        phone=s.phone,
        subject=s.subject,
        role=s.role,
        joined_date=_fmt_date(s.joined_date),
        created_at=s.created_at.isoformat(),
        course_name=course_name,
    )


class StaffService(DBService):
    def __init__(self, scope):
        super().__init__(scope)

    def fetch_staff(self, course_id):
        members = Staff.objects.filter(course_id=course_id)
        return [_build_staff_response(s) for s in members]

    def fetch_all_staff(self, user_id):
        members = Staff.objects.filter(course__owner_id=user_id).select_related('course').order_by('course__name', 'name')
        return [_build_staff_response(s, course_name=s.course.name) for s in members]

    def fetch_one_staff(self, staff_id):
        try:
            s = Staff.objects.select_related('course').get(id=staff_id)
            return _build_staff_response(s, course_name=s.course.name)
        except Staff.DoesNotExist:
            return ErrorResponse(status=404, message='Staff not found')

    def create_or_update_staff(self, req):
        if req.id is None:
            member = Staff.objects.create(
                course_id=req.course_id,
                name=req.name,
                email=req.email,
                phone=req.phone,
                subject=req.subject,
                role=req.role,
                joined_date=req.joined_date or None,
            )
        else:
            try:
                member = Staff.objects.get(id=req.id)
            except Staff.DoesNotExist:
                return ErrorResponse(status=404, message='Staff not found')
            member.name = req.name
            member.email = req.email
            member.phone = req.phone
            member.subject = req.subject
            member.role = req.role
            member.joined_date = req.joined_date or None
            member.save()
        return _build_staff_response(member)

    def delete_staff(self, staff_id):
        deleted, _ = Staff.objects.filter(id=staff_id).delete()
        if not deleted:
            return ErrorResponse(status=404, message='Staff not found')
        return SuccessResponse(status=200, message='Staff deleted')
