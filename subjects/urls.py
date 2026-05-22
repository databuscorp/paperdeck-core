from django.urls import path
from subjects.controller.subjectcontroller import subject, syllabus, topic, chapter

urlpatterns = [
    path('', subject),
    path('syllabus/', syllabus),
    path('topics/', topic),
    path('chapters/', chapter),
]
