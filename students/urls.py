from django.urls import path
from students.controller.studentcontroller import student

urlpatterns = [
    path('', student),
]
