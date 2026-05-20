from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from users.processor.userprocessor import (
    register_req_schema, login_req_schema,
    update_profile_req_schema, change_password_req_schema,
)
from users.service.userservice import UserService
from utility.decorator.auth import auth_required
from utility.utilityobj import ErrorResponse


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    obj = register_req_schema.load(request.data)
    service = UserService()
    resp = service.register(obj)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    obj = login_req_schema.load(request.data)
    service = UserService()
    resp = service.login(obj)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    token_str = request.data.get('refresh')
    if not token_str:
        return HttpResponse(
            ErrorResponse(status=400, message='refresh token required').to_json(),
            status=400, content_type='application/json'
        )
    try:
        token = RefreshToken(token_str)
        return HttpResponse(
            f'{{"access":"{str(token.access_token)}"}}',
            content_type='application/json'
        )
    except TokenError:
        return HttpResponse(
            ErrorResponse(status=401, message='Invalid or expired refresh token').to_json(),
            status=401, content_type='application/json'
        )


@csrf_exempt
@api_view(['GET'])
@auth_required
def me(request):
    service = UserService()
    resp = service.me(request.auth_user)
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['PATCH'])
@auth_required
def update_profile(request):
    obj = update_profile_req_schema.load(request.data, partial=True)
    service = UserService()
    resp = service.update_profile(request.auth_user, obj)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')


@csrf_exempt
@api_view(['POST'])
@auth_required
def change_password(request):
    obj = change_password_req_schema.load(request.data)
    service = UserService()
    resp = service.change_password(request.auth_user, obj)
    if isinstance(resp, ErrorResponse):
        return HttpResponse(resp.to_json(), status=resp.status, content_type='application/json')
    return HttpResponse(resp.to_json(), content_type='application/json')
