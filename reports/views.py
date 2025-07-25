from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework import status, viewsets
from django.utils.timezone import now
from django.core.cache import cache
from django.db.models import Sum, Count, Avg, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from datetime import timedelta, date
from decimal import Decimal
from rest_framework import filters

from members.models import Member
from attendance.models import Attendance
from finance.models import Payment, Costs, Debt
from utils.payments import get_expiry_date, is_expired
from .models import (
    MembershipSale, 
    AttendanceReport, 
    IncomeExpenseReport, 
    Subscription,
    DailyReport,
    MonthlyReport
)
from .serializers import (
    IncomeReportSerializer,
    AttendanceReportDataSerializer,
    ExpiringMembershipSerializer,
    UnpaidMemberSerializer,
    DashboardStatsSerializer,
    MembershipSaleSerializer,
    AttendanceReportSerializer,
    IncomeExpenseReportSerializer,
    SubscriptionSerializer,
    DailyReportSerializer,
    MonthlyReportSerializer
)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for report endpoints."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000


class DashboardStatsView(APIView):
    """
    GET /api/reports/dashboard-stats/
    Returns comprehensive dashboard statistics for the fitness center.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Use cache to improve performance
        cache_key = f"dashboard_stats_{request.user.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        today = now().date()
        month_start = today.replace(day=1)
        
        try:
            # Member statistics
            total_members = Member.objects.filter(state=True).count()
            active_members = Member.objects.filter(state=True).count()  # All active members
            
            # Expiring members (next 7 days)
            expiring_soon = 0
            for member in Member.objects.filter(state=True):
                if not is_expired(member) and get_expiry_date(member) <= today + timedelta(days=3):
                    expiring_soon += 1
            
            # Today's financial data
            today_income = Payment.objects.filter(
                date=today, 
                state=True
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            today_expenses = Costs.objects.filter(
                date=today, 
                state=True
            ).aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')
            
            # Today's attendance
            today_attendance = Attendance.objects.filter(
                attended_at__date=today, 
                state=True
            ).count()
            
            # Monthly financial data
            monthly_income = Payment.objects.filter(
                date__gte=month_start, 
                state=True
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            monthly_expenses = Costs.objects.filter(
                date__gte=month_start, 
                state=True
            ).aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')
            
            # Calculate profit margin
            profit_margin = 0
            if monthly_income > 0:
                profit_margin = ((monthly_income - monthly_expenses) / monthly_income) * 100
            
            stats = {
                'total_members': total_members,
                'active_members': active_members,
                'expiring_soon': expiring_soon,
                'today_income': today_income,
                'today_expenses': today_expenses,
                'today_attendance': today_attendance,
                'monthly_income': monthly_income,
                'monthly_expenses': monthly_expenses,
                'profit_margin': round(profit_margin, 2),
            }
            
            # Cache for 5 minutes
            cache.set(cache_key, stats, 300)
            
            serializer = DashboardStatsSerializer(stats)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': f'Error generating dashboard stats: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
)


class IncomeReportView(APIView):
    """
    GET /api/reports/income/
    Returns income data with filtering options.
    Query params: start_date, end_date, payment_type
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        try:
            # Get query parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            payment_type = request.query_params.get('payment_type')
            
            # Build query
            queryset = Payment.objects.filter(state=True)
            
            if start_date:
                queryset = queryset.filter(date__gte=start_date)
            if end_date:
                queryset = queryset.filter(date__lte=end_date)
            if payment_type:
                queryset = queryset.filter(payment_type=payment_type)
            
            # Default to last 30 days if no date range specified
            if not start_date and not end_date:
                last_30_days = now().date() - timedelta(days=30)
                queryset = queryset.filter(date__gte=last_30_days)
            
            # Aggregate data by date
            data = (
                queryset
            .values('date')
                .annotate(
                    total_income=Sum('amount'),
                    payment_count=Count('id'),
                    avg_payment=Avg('amount')
                )
            .order_by('date')
        )

            # Paginate results
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(data, request)
            
            serializer = IncomeReportSerializer(paginated_data, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': f'Error generating income report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AttendanceReportView(APIView):
    """
    GET /api/reports/attendance/
    Returns attendance data with filtering options.
    Query params: start_date, end_date, branch
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        try:
            # Get query parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            branch = request.query_params.get('branch')
            
            # Build query
            queryset = Attendance.objects.filter(state=True)
            
            if start_date:
                queryset = queryset.filter(attended_at__date__gte=start_date)
            if end_date:
                queryset = queryset.filter(attended_at__date__lte=end_date)
            if branch:
                queryset = queryset.filter(member__branch=branch)
            
            # Aggregate data by date
            data = (
                queryset
            .values('attended_at__date')
                .annotate(
                    total_check_ins=Count('id'),
                    unique_members=Count('member', distinct=True),
                    avg_duration=Avg('duration_minutes')
                )
            .order_by('attended_at__date')
        )

            # Format data for serializer
            formatted_data = []
            for entry in data:
                formatted_data.append({
                    'date': entry['attended_at__date'],
                    'total_check_ins': entry['total_check_ins'],
                    'unique_members': entry['unique_members'],
                    'avg_duration': entry['avg_duration'],
                })
            
            # Paginate results
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(formatted_data, request)
            
            serializer = AttendanceReportDataSerializer(paginated_data, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': f'Error generating attendance report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExpiringMembershipsView(APIView):
    """
    GET /api/reports/expiring-memberships/
    Returns members whose memberships are expiring soon.
    Query params: days (default: 7)
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = ExpiringMembershipSerializer

    def get(self, request):
        try:
            days = int(request.query_params.get('days', 7))
            today = now().date()
            soon = today + timedelta(days=days)

            results = []
            for member in Member.objects.filter(state=True).select_related():
                expiry = get_expiry_date(member)
                if today <= expiry <= soon:
                    results.append({
                        'member_name': f"{member.f_name} {member.l_name}",
                        'phone': member.phone,
                        'expiry_date': expiry,
                        'days_remaining': (expiry - today).days,
                        'subscription_type': member.payment_type,
                    })

            # Sort by days remaining
            results.sort(key=lambda x: x['days_remaining'])

            # Paginate results
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(results, request)

            serializer = ExpiringMembershipSerializer(paginated_data, many=True)
            return paginator.get_paginated_response(serializer.data)

        except ValueError:
            return Response(
                {'error': 'Invalid days parameter. Must be a number.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error generating expiring memberships report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UnpaidMembersView(APIView):
    """
    GET /api/reports/unpaid-members/
    Returns members who haven't paid recently.
    Query params: days (default: 30)
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = UnpaidMemberSerializer

    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
            today = now().date()
            cutoff = today - timedelta(days=days)

            # Find members who have paid recently
            recent_paid_member_ids = set(
                Payment.objects
                .filter(date__gte=cutoff, state=True)
                .values_list('member_id', flat=True)
            )

            results = []
            for member in Member.objects.filter(state=True).select_related():
                if member.id not in recent_paid_member_ids:
                    # Find last payment
                    last_payment = (
                        Payment.objects
                        .filter(member=member, state=True)
                        .order_by('-date')
                        .first()
                    )

                    last_date = last_payment.date if last_payment else None
                    days_since = (today - last_date).days if last_date else None

                    # Calculate total debt
                    total_debt = Debt.objects.filter(
                        member=member,
                        state=True
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

                    results.append({
                        'member_name': f"{member.f_name} {member.l_name}",
                        'phone': member.phone,
                        'last_payment_date': last_date,
                        'days_since_last_payment': days_since,
                        'total_debt': total_debt,
                    })

            # Sort by days since last payment (most recent first)
            results.sort(key=lambda x: x['days_since_last_payment'] or float('inf'))

            # Paginate results
            paginator = self.pagination_class()
            paginated_data = paginator.paginate_queryset(results, request)

            serializer = UnpaidMemberSerializer(paginated_data, many=True)
            return paginator.get_paginated_response(serializer.data)

        except ValueError:
            return Response(
                {'error': 'Invalid days parameter. Must be a number.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error generating unpaid members report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Model ViewSets for CRUD operations

class MembershipSaleViewSet(viewsets.ModelViewSet):
    """ViewSet for MembershipSale model."""
    queryset = MembershipSale.objects.select_related('member').all()
    serializer_class = MembershipSaleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['sale_date', 'payment_type', 'member']
    search_fields = ['member__f_name', 'member__l_name', 'notes']
    ordering_fields = ['sale_date', 'amount']
    ordering = ['-sale_date']


class AttendanceReportViewSet(viewsets.ModelViewSet):
    """ViewSet for AttendanceReport model."""
    queryset = AttendanceReport.objects.select_related('member').all()
    serializer_class = AttendanceReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['date', 'branch', 'member']
    search_fields = ['member__f_name', 'member__l_name', 'branch']
    ordering_fields = ['date', 'check_in_time']
    ordering = ['-date', '-check_in_time']


class IncomeExpenseReportViewSet(viewsets.ModelViewSet):
    """ViewSet for IncomeExpenseReport model."""
    queryset = IncomeExpenseReport.objects.all()
    serializer_class = IncomeExpenseReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['date']
    ordering_fields = ['date', 'income', 'expenses']
    ordering = ['-date']


class SubscriptionViewSet(viewsets.ModelViewSet):
    """ViewSet for Subscription model."""
    queryset = Subscription.objects.select_related('member').all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['start_date', 'end_date', 'subscription_type', 'is_active', 'member']
    search_fields = ['member__f_name', 'member__l_name', 'notes']
    ordering_fields = ['start_date', 'end_date']
    ordering = ['-end_date']


class DailyReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DailyReport.objects.all()
    serializer_class = DailyReportSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['date']
    ordering_fields = ['date']
    ordering = ['-date']

class MonthlyReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MonthlyReport.objects.all()
    serializer_class = MonthlyReportSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['month']
    ordering_fields = ['month']
    ordering = ['-month']
