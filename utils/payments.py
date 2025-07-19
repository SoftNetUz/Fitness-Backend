# utils/payments.py
import calendar
from datetime import timedelta, date
from django.utils import timezone
from members.models import Member

PT = Member.PaymentType

def today():
    return timezone.localdate()

def _get_base_date(member):
    last = member.payments.order_by('-date').values_list('date', flat=True).first()
    return last or member.created_at.date()

def _expiry_for(payment_type, base_date):
    if payment_type == PT.MONTHLY:
        return base_date + timedelta(days=30)
    if payment_type == PT.PREMIUM:
        y, m = base_date.year, base_date.month
        last_day = calendar.monthrange(y, m)[1]
        return date(y, m, last_day)
    return base_date  # daily or fallback

def get_expiry_date(member):
    """
    Compute the plan’s expiry date from the last payment or creation.
    """
    return _expiry_for(member.payment_type, _get_base_date(member))

def is_expired(member, as_of_date=None):
    """
    True if the member has used up all visits (monthly) or 
    as_of_date is past the expiry.
    """
    as_of = as_of_date or today()
    base  = _get_base_date(member)
    expiry = _expiry_for(member.payment_type, base)

    if member.payment_type == PT.MONTHLY:
        visits = member.attendances.filter(
            attended_at__date__gte=base,
            attended_at__date__lte=expiry
        ).count()
        return visits >= 12 or as_of > expiry

    return as_of > expiry

def is_expiring_soon(member, threshold_days=3, as_of_date=None):
    """
    True if expiry is within threshold_days or, for monthly,
    visits remaining ≤3.
    """
    as_of = as_of_date or today()
    if is_expired(member, as_of):
        return False

    base   = _get_base_date(member)
    expiry = _expiry_for(member.payment_type, base)
    days_left = (expiry - as_of).days

    if member.payment_type == PT.MONTHLY:
        visits = member.attendances.filter(
            attended_at__date__gte=base,
            attended_at__date__lte=expiry
        ).count()
        return days_left <= threshold_days or (12 - visits) <= 3

    return days_left <= threshold_days
