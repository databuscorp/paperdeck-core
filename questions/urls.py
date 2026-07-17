from django.urls import path
from questions.controller.questioncontroller import (
    question,
    generate_questions,
    generate_question_variants,
    import_paper,
    review,
    quality,
)

urlpatterns = [
    path('', question),
    path('generate/', generate_questions),
    path('variants/', generate_question_variants),   # POST: N parametric variants of one question
    path('import/', import_paper),
    path('review/', review),      # GET: the queue  |  POST: approve/reject/edit
    path('quality/', quality),    # GET: verification stats + drift series
]
