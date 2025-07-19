from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    IncomeReportView,
    AttendanceReportView,
    ExpiringMembershipsView,
    UnpaidMembersView,
    DashboardStatsView,
    MembershipSaleViewSet,
    AttendanceReportViewSet,
    IncomeExpenseReportViewSet,
    SubscriptionViewSet,
    DailyReportViewSet,
    MonthlyReportViewSet,
)

# Create router for ViewSets
router = DefaultRouter()
router.register('membership-sales', MembershipSaleViewSet, basename='membership-sale')
router.register('attendance-reports', AttendanceReportViewSet, basename='attendance-report')
router.register('income-expense-reports', IncomeExpenseReportViewSet, basename='income-expense-report')
router.register('subscriptions', SubscriptionViewSet, basename='subscription')
router.register('daily-reports', DailyReportViewSet, basename='daily-report')
router.register('monthly-reports', MonthlyReportViewSet, basename='monthly-report')

urlpatterns = [
    # Dashboard and analytics endpoints
    path('dashboard-stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('income/', IncomeReportView.as_view(), name='income-report'),
    path('attendance/', AttendanceReportView.as_view(), name='attendance-report'),
    path('expiring-memberships/', ExpiringMembershipsView.as_view(), name='expiring-memberships'),
    path('unpaid-members/', UnpaidMembersView.as_view(), name='unpaid-members'),
    
    # Include ViewSet URLs
    path('', include(router.urls)),
]
