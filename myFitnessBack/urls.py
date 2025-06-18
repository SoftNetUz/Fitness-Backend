from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.http import HttpResponse

def home_view(request):
    return HttpResponse( "Welcome to the API")

urlpatterns = [
    path("", home_view),
    path("admin/", admin.site.urls),
    
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # APP URLs
    path("api/", include("attendance.urls")),
    path("api/", include("members.urls")),
    path("api/", include("finance.urls")),
    path("api/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)