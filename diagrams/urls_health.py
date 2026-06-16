from django.urls import path
from diagrams.controller.diagramcontroller import health_check

urlpatterns = [
    path("", health_check),
]
