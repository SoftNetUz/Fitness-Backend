from django.utils import timezone
from reports.models import DailyReport, MonthlyReport
from members.models import FitnessClub


def get_fitness_statistics():
    """
    Returns a comprehensive statistics dictionary for the fitness club,
    using the latest DailyReport and MonthlyReport for performance and consistency.
    """
    stats = {}

    # Get today's and this month's reports
    today = timezone.localdate()
    first_of_month = today.replace(day=1)

    daily_report = DailyReport.objects.order_by('-date').first()
    monthly_report = MonthlyReport.objects.order_by('-month').first()

    # Helper to serialize report objects
    def serialize_report(report, period_label):
        if not report:
            return {"message": f"No {period_label} report available."}
        return {
            'date': getattr(report, 'date', None) or getattr(report, 'month', None),
            'income': report.income,
            'expense': report.expense,
            'new_members': report.new_members,
            'renewals': report.renewals,
            'total_members': report.total_members,
            'check_ins': report.check_ins,
            'expiring_soon': report.expiring_soon,
            'active_members': report.active_members,
            'male_members': report.male_members,
            'female_members': report.female_members,
            'cash_income': report.cash_income,
            'card_income': report.card_income,
        }

    stats['daily'] = serialize_report(daily_report, 'daily')
    stats['monthly'] = serialize_report(monthly_report, 'monthly')

    # Club statistics (assuming singleton)
    club = FitnessClub.get_instance()
    stats['club'] = {
        'name': club.name,
        'vip': club.vip,
        'daily_price': float(club.daily),
        'monthly_price': float(club.monthly),
    }

    return stats

