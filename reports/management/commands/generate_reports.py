from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from reports.models import DailyReport, MonthlyReport
from members.models import Member
from attendance.models import Attendance
from finance.models import Payment, Costs
from django.db.models import Sum, Count, Q

class Command(BaseCommand):
    help = 'Generate daily and monthly reports for a given date/month (default: today/this month)'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Date for daily report (YYYY-MM-DD)')
        parser.add_argument('--month', type=str, help='Month for monthly report (YYYY-MM)')

    def handle(self, *args, **options):
        today = timezone.now().date()
        # Daily report
        date_str = options.get('date')
        if date_str:
            try:
                report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                self.stderr.write(self.style.ERROR('Invalid date format. Use YYYY-MM-DD.'))
                return
        else:
            report_date = today
        self.generate_daily_report(report_date)

        # Monthly report
        month_str = options.get('month')
        if month_str:
            try:
                report_month = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
            except ValueError:
                self.stderr.write(self.style.ERROR('Invalid month format. Use YYYY-MM.'))
                return
        else:
            report_month = today.replace(day=1)
        self.generate_monthly_report(report_month)

    def generate_daily_report(self, date):
        # Income and payment breakdown
        income = Payment.objects.filter(date=date, state=True).aggregate(total=Sum('amount'))['total'] or 0
        cash_income = Payment.objects.filter(date=date, state=True, payment_type='cash').aggregate(total=Sum('amount'))['total'] or 0
        card_income = Payment.objects.filter(date=date, state=True, payment_type='card').aggregate(total=Sum('amount'))['total'] or 0
        expense = Costs.objects.filter(date=date, state=True).aggregate(total=Sum('quantity'))['total'] or 0
        # Members
        new_members = Member.objects.filter(created_at__date=date, state=True).count()
        renewals = Payment.objects.filter(date=date, state=True, payment_type='renewal').count()
        total_members = Member.objects.filter(state=True).count()
        # Attendance
        check_ins = Attendance.objects.filter(attended_at=date, state=True).count()
        # Expiring soon (next 3 days)
        expiring_soon = Member.objects.filter(state=True, subscriptions__end_date__range=[date, date+timedelta(days=3)]).distinct().count()
        # Active members (checked in at least once today)
        active_members = Attendance.objects.filter(attended_at=date, state=True).values('member').distinct().count()
        # Gender breakdown
        male_members = Member.objects.filter(state=True, gender='male').count()
        female_members = Member.objects.filter(state=True, gender='female').count()
        # Save or update
        obj, created = DailyReport.objects.update_or_create(
            date=date,
            defaults={
                'income': income,
                'expense': expense,
                'new_members': new_members,
                'renewals': renewals,
                'total_members': total_members,
                'check_ins': check_ins,
                'expiring_soon': expiring_soon,
                'active_members': active_members,
                'male_members': male_members,
                'female_members': female_members,
                'cash_income': cash_income,
                'card_income': card_income,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'Daily report for {date} generated.'))

    def generate_monthly_report(self, month):
        # Calculate first and last day of the month
        first_day = month
        if month.month == 12:
            next_month = month.replace(year=month.year+1, month=1, day=1)
        else:
            next_month = month.replace(month=month.month+1, day=1)
        last_day = next_month - timedelta(days=1)
        # Income and payment breakdown
        income = Payment.objects.filter(date__gte=first_day, date__lte=last_day, state=True).aggregate(total=Sum('amount'))['total'] or 0
        cash_income = Payment.objects.filter(date__gte=first_day, date__lte=last_day, state=True, payment_type='cash').aggregate(total=Sum('amount'))['total'] or 0
        card_income = Payment.objects.filter(date__gte=first_day, date__lte=last_day, state=True, payment_type='card').aggregate(total=Sum('amount'))['total'] or 0
        expense = Costs.objects.filter(date__gte=first_day, date__lte=last_day, state=True).aggregate(total=Sum('quantity'))['total'] or 0
        # Members
        new_members = Member.objects.filter(created_at__date__gte=first_day, created_at__date__lte=last_day, state=True).count()
        renewals = Payment.objects.filter(date__gte=first_day, date__lte=last_day, state=True, payment_type='renewal').count()
        total_members = Member.objects.filter(state=True).count()
        # Attendance
        check_ins = Attendance.objects.filter(attended_at__gte=first_day, attended_at__lte=last_day, state=True).count()
        # Expiring soon (next 3 days from last day of month)
        expiring_soon = Member.objects.filter(state=True, subscriptions__end_date__range=[last_day, last_day+timedelta(days=3)]).distinct().count()
        # Active members (checked in at least once this month)
        active_members = Attendance.objects.filter(attended_at__gte=first_day, attended_at__lte=last_day, state=True).values('member').distinct().count()
        # Gender breakdown
        male_members = Member.objects.filter(state=True, gender='male').count()
        female_members = Member.objects.filter(state=True, gender='female').count()
        # Save or update
        obj, created = MonthlyReport.objects.update_or_create(
            month=month,
            defaults={
                'income': income,
                'expense': expense,
                'new_members': new_members,
                'renewals': renewals,
                'total_members': total_members,
                'check_ins': check_ins,
                'expiring_soon': expiring_soon,
                'active_members': active_members,
                'male_members': male_members,
                'female_members': female_members,
                'cash_income': cash_income,
                'card_income': card_income,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'Monthly report for {month.strftime("%Y-%m")} generated.')) 