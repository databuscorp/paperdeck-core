from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/courses/', include('courses.urls')),
    path('api/subjects/', include('subjects.urls')),
    path('api/staff/', include('staff.urls')),
    path('api/students/', include('students.urls')),
    path('api/papers/', include('papers.urls')),
    path('api/questions/', include('questions.urls')),
    path('api/mocktests/', include('mocktests.urls')),
    path('api/blueprints/', include('blueprints.urls')),
    path('api/exams/', include('exams.urls')),
    path('api/diagrams/', include('diagrams.urls')),
    path('api/health/', include('diagrams.urls_health')),
    path('api/latex/', include('latex.urls')),
    path('api/printtemplates/', include('printtemplates.urls')),
    path('api/billing/', include('billing.urls')),
    path('api/attempts/', include('attempts.urls')),
    path('api/omr/', include('omr.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
