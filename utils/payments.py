import calendar
from datetime import timedelta, date

def get_expiry_date(member):
    """
    Returns the expiry date for a given Member, based on:
      1. Their most recent Payment.date (if any), else member.created_at
      2. The member.payment_type ('Oylik', 'Premium', 'Kunlik')
    """
    # 1. Look up the last payment (if it exists)
    last_payment = member.payments.order_by('-date').first()
    if last_payment:
        base_date = last_payment.date
    else:
        base_date = member.created_at.date()

    if member.payment_type == 'Oylik':
        return base_date + timedelta(days=30)

    elif member.payment_type == 'Premium':
        year = base_date.year
        month = base_date.month
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, last_day)

    elif member.payment_type == 'Kunlik':
        # Expires at the end of the same day
        return base_date

    # Fallback
    return base_date + timedelta(days=30)


def is_expired(member, as_of_date=None):
    if as_of_date is None:
        as_of_date = date.today()

    expiry = get_expiry_date(member)
    if member.payment_type == 'Oylik':
        # Count attendances from the last payment (or creation) up to expiry
        last_payment = member.payments.order_by('-date').first()
        start_date = last_payment.date if last_payment else member.created_at.date()

        attend_count = member.attendances.filter(
            attended_at__date__gte=start_date,
            attended_at__date__lte=expiry
        ).count()
        return (attend_count >= 12) or (as_of_date > expiry)

    elif member.payment_type == 'Premium':
        return as_of_date > expiry

    elif member.payment_type == 'Kunlik':
        return as_of_date > expiry

    return False


def is_expiring_soon(member, threshold_days=3, as_of_date=None):
    if as_of_date is None:
        as_of_date = date.today()

    expiry = get_expiry_date(member)
    days_left = (expiry - as_of_date).days

    if is_expired(member, as_of_date):
        return False

    if member.payment_type == 'Oylik':
        last_payment = member.payments.order_by('-date').first()
        start_date = last_payment.date if last_payment else member.created_at.date()

        attend_count = member.attendances.filter(
            attended_at__date__gte=start_date,
            attended_at__date__lte=expiry
        ).count()
        visits_left = 12 - attend_count
        return (0 <= days_left <= threshold_days) or (visits_left <= 3)

    elif member.payment_type == 'Premium':
        return 0 <= days_left <= threshold_days

    elif member.payment_type == 'Kunlik':
        return days_left == 0

    return False
