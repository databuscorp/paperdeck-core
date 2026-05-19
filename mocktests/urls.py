from django.urls import path
from mocktests.controller.mocktestcontroller import mocktest

urlpatterns = [
    path('', mocktest),
]
