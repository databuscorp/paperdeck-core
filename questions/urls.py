from django.urls import path
from questions.controller.questioncontroller import question

urlpatterns = [
    path('', question),
]
