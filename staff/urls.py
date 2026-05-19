from django.urls import path
from staff.controller.staffcontroller import staff

urlpatterns = [
    path('', staff),
]
