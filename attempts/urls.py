from django.urls import path

from attempts.controller.attemptcontroller import (adaptive_practice, analysis,
                                                   attempt, cohort_summary,
                                                   student_summary)

urlpatterns = [
    path('', attempt),
    path('analysis/', analysis),
    path('student/', student_summary),
    path('cohort/', cohort_summary),
    path('adaptive-practice/', adaptive_practice),
]
