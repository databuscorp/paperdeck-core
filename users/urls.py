from django.urls import path
from users.controller.usercontroller import register, login, refresh_token, me

urlpatterns = [
    path('register/', register),
    path('login/', login),
    path('refresh/', refresh_token),
    path('me/', me),
]
