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
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
