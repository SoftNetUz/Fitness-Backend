from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import FitnessClubViewSet, MemberViewSet, MemberStatsAPIView, AttendanceViewSet

router = DefaultRouter()
router.register('fitness-clubs', FitnessClubViewSet)
router.register('members', MemberViewSet, basename='member')
router.register('attended-time', AttendanceViewSet, basename='attended-time')

urlpatterns = router.urls + [
    path('member-stats/', MemberStatsAPIView.as_view(), name='member-stats'),
]