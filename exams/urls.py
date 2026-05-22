from django.urls import path
from exams.controller.examcontroller import exam_templates, exam_authorities

urlpatterns = [
    path('', exam_templates),
    path('authorities/', exam_authorities),
]