from functools import wraps
from django.http import JsonResponse
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import get_user_model


def auth_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Authorization header missing'}, status=401)

        token_str = auth_header.split(' ')[1]
        try:
            token = AccessToken(token_str)
            user_id = token['user_id']
        except (TokenError, InvalidToken) as e:
            return JsonResponse({'error': 'Invalid or expired token'}, status=401)

        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=401)

        request.scope = {'scope': 'default', 'user_id': user_id}
        request.auth_user = user
        return view_func(request, *args, **kwargs)

    return _wrapped
