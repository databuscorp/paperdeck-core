from django.urls import path
from papers.controller.papercontroller import papers, generate

urlpatterns = [
    path('', papers),
    path('generate/', generate),
]
