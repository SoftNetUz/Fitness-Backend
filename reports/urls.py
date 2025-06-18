from django.urls import path
from .views import (
    IncomeReportView,
    AttendanceReportView,
    ExpiringMembershipsView,
    UnpaidMembersView,
)

urlpatterns = [
    path('income/', IncomeReportView.as_view(), name='income-report'),
    path('attendance/', AttendanceReportView.as_view(), name='attendance-report'),
    path('expiring-memberships/', ExpiringMembershipsView.as_view(), name='expiring-memberships'),
    path('unpaid-members/', UnpaidMembersView.as_view(), name='unpaid-members'),
]
