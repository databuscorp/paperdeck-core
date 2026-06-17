from django.urls import path
from printtemplates.controller.printtemplatecontroller import print_templates

urlpatterns = [
    path('', print_templates),
]
