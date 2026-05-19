from django.urls import path
from exams.controller.examcontroller import exam_templates

urlpatterns = [
    path('', exam_templates),
]
