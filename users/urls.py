from django.urls import path
from users.controller.usercontroller import register, login, refresh_token, me, update_profile, change_password

urlpatterns = [
    path('register/', register),
    path('login/', login),
    path('refresh/', refresh_token),
    path('me/', me),
    path('profile/', update_profile),
    path('change-password/', change_password),
]
