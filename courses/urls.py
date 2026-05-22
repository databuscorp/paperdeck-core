from django.urls import path
from courses.controller.coursecontroller import courses, subscription, dashboard_stats

urlpatterns = [
    path('', courses),
    path('subscribe/', subscription),
    path('stats/', dashboard_stats),
]
