from rest_framework import viewsets, permissions, filters
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from datetime import timedelta
from django.utils import timezone
from .models import FitnessClub, Member
from .serializers import FitnessClubSerializer, MemberSerializer, AttendanceSerializer, PAYMENT_TYPE
from .models import AttendedTime
from rest_framework.response import Response
import calendar
from utils.payments import get_expiry_date, is_expired, is_expiring_soon


class FitnessClubViewSet(viewsets.ModelViewSet):
    queryset = FitnessClub.objects.all()
    serializer_class = FitnessClubSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]



class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.filter(state=True).order_by('-created_at')
    serializer_class = MemberSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['f_name', 'l_name', 'phone', 'payment_type', 'branch']
    ordering_fields = ['created_at', 'f_name', 'l_name', 'payment_type']


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = AttendedTime.objects.all()
    serializer_class = AttendanceSerializer
    

class MemberStatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        members = Member.objects.all().filter(state=True)
        today = timezone.now().date()

        total_members   = members.count()
        monthly_members = members.filter(payment_type='Oylik').count()
        vip_members     = members.filter(payment_type='Premium').count()
        daily_members   = members.filter(payment_type='Kunlik').count()

        expiring_members = 0
        expired_members = 0

        for member in members:
            if is_expired(member, as_of_date=today):
                expired_members += 1
            elif is_expiring_soon(member, as_of_date=today):
                expiring_members += 1

        return Response({
            "total_members":    total_members,
            "monthly_members":  monthly_members,
            "vip_members":      vip_members,
            "daily_members":    daily_members,
            "expiring_members": expiring_members,
            "expired_members":  expired_members,
        })
    