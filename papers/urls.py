from django.urls import path
from papers.controller.papercontroller import papers, generate, generate_async, generation_job

urlpatterns = [
    path('', papers),
    path('generate/', generate),
    path('generate-async/', generate_async),
    path('job/', generation_job),
]
