from django.urls import path
from subjects.controller.subjectcontroller import subject, syllabus

urlpatterns = [
    path('', subject),
    path('syllabus/', syllabus),
]
