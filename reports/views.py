from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Sum, Count
from members.models import Member
from attendance.models import Attendance
from finance.models import Payment
from utils.payments import get_expiry_date
from .serializers import (
    IncomeReportSerializer,
    AttendanceReportSerializer,
    ExpiringMembershipSerializer,
    UnpaidMemberSerializer,
)


class IncomeReportView(APIView):
    """
    GET /api/reports/income/
    Returns a list of { date, total_income } for each date in the last 30 days.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = now().date()
        last_30_days = today - timedelta(days=30)

        # Note: Payment model field is 'date', not 'payment_date'.
        payments = (
            Payment.objects
            .filter(date__gte=last_30_days, state=True)
            .values('date')
            .annotate(total_income=Sum('amount'))
            .order_by('date')
        )

        return Response(IncomeReportSerializer(payments, many=True).data)


class AttendanceReportView(APIView):
    """
    GET /api/reports/attendance/
    Returns a list of { date, total_check_ins } across all members.
    Groups by attended_at date.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Attendance model field is 'attended_at' (DateTimeField)
        data = (
            Attendance.objects
            .filter(state=True)
            .values('attended_at__date')
            .annotate(total_check_ins=Count('id'))
            .order_by('attended_at__date')
        )

        # Rename the key 'attended_at__date' to 'date' for the serializer
        formatted = [
            {'date': entry['attended_at__date'], 'total_check_ins': entry['total_check_ins']}
            for entry in data
        ]
        return Response(AttendanceReportSerializer(formatted, many=True).data)


class ExpiringMembershipsView(APIView):
    """
    GET /api/reports/expiring-memberships/
    Returns all members whose expiry date (computed via utils/payments.get_expiry_date)
    falls between today and 7 days from today.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = now().date()
        soon = today + timedelta(days=7)

        # We need to iterate over active members, check their expiry, and pick the ones in range
        results = []
        for m in Member.objects.filter(state=True):
            expiry = get_expiry_date(m)
            if today <= expiry <= soon:
                full_name = f"{m.f_name} {m.l_name}"
                results.append({
                    'member_name': full_name,
                    'phone': m.phone,
                    'expiry_date': expiry,
                })

        return Response(ExpiringMembershipSerializer(results, many=True).data)


class UnpaidMembersView(APIView):
    """
    GET /api/reports/unpaid-members/
    Returns all members who have NOT made a payment in the last 30 days.
    If a member has never made a payment, we include them as well (with last_payment_date=None).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = now().date()
        cutoff = today - timedelta(days=30)

        # 1) Find member IDs who have at least one payment on or after cutoff
        recent_paid_member_ids = set(
            Payment.objects
            .filter(date__gte=cutoff, state=True)
            .values_list('member_id', flat=True)
        )

        results = []
        # 2) All active members:
        for m in Member.objects.filter(state=True):
            # Find their last payment date (if any)
            last_payment = (
                Payment.objects
                .filter(member=m, state=True)
                .order_by('-date')
                .first()
            )
            last_date = last_payment.date if last_payment else None

            # If they either never paid or their last payment < cutoff, include
            if (last_date is None) or (last_date < cutoff):
                full_name = f"{m.f_name} {m.l_name}"
                # If they have never paid, we can leave last_payment_date as None
                results.append({
                    'member_name': full_name,
                    'phone': m.phone,
                    'last_payment_date': last_date,
                })

        return Response(UnpaidMemberSerializer(results, many=True).data)
