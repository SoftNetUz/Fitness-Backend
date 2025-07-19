from rest_framework import viewsets, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from .models import FitnessClub, Member
from attendance.models import Attendance
from utils.payments import is_expired, is_expiring_soon

from .serializers import (
    FitnessClubSerializer, MemberSerializer,
    AttendanceSerializer
)

class FitnessClubViewSet(viewsets.ModelViewSet):
    queryset = FitnessClub.objects.all()
    serializer_class = FitnessClubSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.filter(state=True).order_by('-created_at')
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['f_name', 'l_name', 'phone', 'payment_type', 'branch']
    ordering_fields = ['created_at', 'f_name', 'l_name', 'payment_type']

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

class MemberStatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        members = Member.objects.filter(state=True)

        total   = members.count()
        monthly = members.filter(payment_type=Member.PaymentType.MONTHLY).count()
        vip     = members.filter(payment_type=Member.PaymentType.PREMIUM).count()
        daily   = members.filter(payment_type=Member.PaymentType.DAILY).count()

        expiring = 0
        expired  = 0
        for m in members:
            if is_expired(m, as_of_date=today):
                expired += 1
            elif is_expiring_soon(m, as_of_date=today):
                expiring += 1

        data = {
            'total_members': total,
            'monthly_members': monthly,
            'vip_members': vip,
            'daily_members': daily,
            'expiring_members': expiring,
            'expired_members': expired,
        }
        return Response(data)
