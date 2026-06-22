from django.urls import path
from billing.controller.billingcontroller import status, charge, buy_credits

urlpatterns = [
    path('', status),
    path('charge/', charge),
    path('credits/', buy_credits),
]
