from django.urls import path
from courses.controller.coursecontroller import courses

urlpatterns = [
    path('', courses),
]
