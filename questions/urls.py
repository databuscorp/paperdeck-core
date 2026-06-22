from django.urls import path
from questions.controller.questioncontroller import question, generate_questions, import_paper

urlpatterns = [
    path('', question),
    path('generate/', generate_questions),
    path('import/', import_paper),
]
