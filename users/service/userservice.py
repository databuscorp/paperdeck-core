from django.contrib.auth import authenticate

from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from users.processor.userprocessor import UserResponse, AuthResponse
from utility.utilityobj import ErrorResponse, SuccessResponse


def _build_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        institute_name=user.institute_name,
        phone=user.phone,
        role=user.role,
        plan=user.plan,
        papers_used=user.papers_used,
    )


class UserService:

    def register(self, req):
        if User.objects.filter(username=req.username).exists():
            return ErrorResponse(status=400, message='Username already taken')
        if User.objects.filter(email=req.email).exists():
            return ErrorResponse(status=400, message='Email already registered')

        user = User.objects.create_user(
            username=req.username,
            email=req.email,
            password=req.password,
            first_name=req.first_name or '',
            last_name=req.last_name or '',
            institute_name=req.institute_name,
            phone=req.phone,
        )

        refresh = RefreshToken.for_user(user)
        return AuthResponse(
            access=str(refresh.access_token),
            refresh=str(refresh),
            user=_build_user_response(user),
        )

    def login(self, req):
        user = authenticate(username=req.username, password=req.password)
        if not user:
            return ErrorResponse(status=401, message='Invalid credentials')

        refresh = RefreshToken.for_user(user)
        return AuthResponse(
            access=str(refresh.access_token),
            refresh=str(refresh),
            user=_build_user_response(user),
        )

    def me(self, user: User):
        return _build_user_response(user)
