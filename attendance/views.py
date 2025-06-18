# attendance/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import date

from .models import Attendance
from .serializers import AttendanceSerializer
from members.models import Member

# Import our shared expiry logic:
from utils.payments import is_expired, get_expiry_date

class AttendanceViewSet(viewsets.ModelViewSet):
    """
    Allows CRUD on attendance records—but in practice, creation of a record
    should only happen via CheckInAPIView. This ViewSet is primarily for
    admins/managers to browse or delete records.
    """
    permission_classes = [permissions.IsAuthenticated]  # Only authenticated users
    queryset = Attendance.objects.select_related('member').all()
    serializer_class = AttendanceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['member', 'attended_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Month/year filtering for list endpoint
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')

        if month and year:
            try:
                month = int(month)
                year = int(year)
                queryset = queryset.filter(
                    attended_at__month=month,
                    attended_at__year=year
                )
            except ValueError:
                pass  # Ignore invalid month/year

        return queryset


class CheckInAPIView(APIView):
    """
    Endpoint that the kiosk/tablet posts to, e.g. POST /api/attendance/check-in/
    Body: { "pin_code": "1234" }
    """
    permission_classes = [permissions.AllowAny]  # Adjust if you want a kiosk JWT

    def post(self, request):
        code = request.data.get('pin_code')
        if not code or len(code) != 4:
            return Response(
                {'error': "PIN kod 4 raqamli bo'lishi shart"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Find an active member with that PIN
        try:
            member = Member.objects.get(pin_code=code, state=True)
        except Member.DoesNotExist:
            return Response(
                {'error': "Bunday a'zo topilmadi yoki faol emas"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Check if member is expired
        if is_expired(member, as_of_date=date.today()):
            return Response(
                {'error': "A'zolik muddati tugagan"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Prevent duplicate check-in for today
        today = timezone.now().date()
        already_checked_in = Attendance.all_objects.filter(
            member=member,
            attended_at__date=today,
            state=True
        ).exists()
        if already_checked_in:
            return Response(
                {'error': "Bugun allaqachon kirilgan"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Create the attendance record
        attendance = Attendance.objects.create(member=member, code_used=code)

        # 5. Return both member basic info and the newly created attendance
        #    (If you want to minimize payload, you can return only attendance ID and date.)
        return Response({
            'member': {
                'id': member.id,
                'f_name': member.f_name,
                'l_name': member.l_name,
                'payment_type': member.payment_type,
                'expiry_date': get_expiry_date(member),      # optionally include it
                'is_expired': is_expired(member),
            },
            'attendance': AttendanceSerializer(attendance).data
        }, status=status.HTTP_201_CREATED)


class TodayAttendanceListAPIView(ListAPIView):
    """
    GET /api/attendance/today/  → Returns all attendance records for today (state=True)
    """
    permission_classes = [permissions.IsAuthenticated]  # Only staff/managers can view
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        today = timezone.now().date()
        return Attendance.objects.filter(attended_at__date=today, state=True)
