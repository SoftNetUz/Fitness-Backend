import pytest
from decimal import Decimal
from datetime import date, timedelta, time
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from model_bakery import baker
from reports.models import (
    MembershipSale, 
    AttendanceReport, 
    IncomeExpenseReport, 
    Subscription
)
from reports.serializers import (
    MembershipSaleSerializer,
    AttendanceReportSerializer,
    IncomeExpenseReportSerializer,
    SubscriptionSerializer,
    DashboardStatsSerializer,
)
from members.models import Member
from finance.models import Payment, Costs, Debt
from attendance.models import Attendance
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def user(db):
    return User.objects.create_user(username='user', password='pass1234')

@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(username='admin', password='adminpass')

@pytest.fixture
def member(db):
    return baker.make(Member, 
        f_name='John',
        l_name='Doe',
        pin_code='1234',
        payment_type='Oylik',
        payment_amount=Decimal('500.00'),
        state=True
    )

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def auth_client(user, api_client):
    api_client.force_authenticate(user=user)
    return api_client

@pytest.fixture
def admin_client(admin_user, api_client):
    api_client.force_authenticate(user=admin_user)
    return api_client

# ------------------ Model Tests ------------------

def test_membership_sale_str(db, member):
    sale = MembershipSale.objects.create(
        member=member, 
        amount=Decimal('500.00'),
        payment_type='Oylik',
        sale_date=timezone.now().date()  # Ensure this is a date, not datetime
    )
    assert str(sale).startswith(f"{member}")
    assert sale.state is True

def test_membership_sale_validation_negative_amount(db, member):
    with pytest.raises(ValidationError, match="Sale amount must be greater than zero"):
        sale = MembershipSale(
            member=member,
            amount=Decimal('-100.00'),
            payment_type='Oylik',
            sale_date=timezone.now().date()
        )
        sale.full_clean()

def test_membership_sale_validation_future_date(db, member):
    future_date = timezone.now().date() + timedelta(days=1)
    with pytest.raises(ValidationError, match="Sale date cannot be in the future"):
        sale = MembershipSale(
            member=member,
            amount=Decimal('500.00'),
            sale_date=future_date,
            payment_type='Oylik'
        )
        sale.full_clean()

def test_membership_sale_get_total_sales(db, member):
    # Create sales for different dates
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    MembershipSale.objects.create(
        member=member, 
        amount=Decimal('500.00'),
        sale_date=today,
        payment_type='Oylik'
    )
    MembershipSale.objects.create(
        member=member, 
        amount=Decimal('300.00'),
        sale_date=yesterday,
        payment_type='Kunlik'
    )
    
    # Test total sales
    total = MembershipSale.get_total_sales()
    assert total == Decimal('800.00')
    
    # Test filtered sales
    today_total = MembershipSale.get_total_sales(start_date=today)
    assert today_total == Decimal('500.00')

def test_attendance_report_str(db, member):
    report = AttendanceReport.objects.create(
        member=member,
        date=timezone.now().date(),
        branch='Main',
        check_in_time=time(9, 0)
    )
    assert str(report).startswith(f"{member}")
    assert report.state is True

def test_attendance_report_duration_calculation(db, member):
    report = AttendanceReport.objects.create(
        member=member,
        date=timezone.now().date(),
        branch='Main',
        check_in_time=time(9, 0),
        check_out_time=time(11, 30)  # 2.5 hours
    )
    assert report.duration_minutes == 150  # 2.5 hours = 150 minutes

def test_attendance_report_validation_invalid_times(db, member):
    with pytest.raises(ValidationError, match="Check-out time must be after check-in time"):
        report = AttendanceReport(
            member=member,
            date=timezone.now().date(),
            branch='Main',
            check_in_time=time(11, 0),
            check_out_time=time(9, 0)  # Invalid: checkout before checkin
        )
        report.full_clean()

def test_attendance_report_get_stats(db, member):
    # Create attendance reports
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    AttendanceReport.objects.create(
        member=member,
        date=today,
        branch='Main',
        check_in_time=time(9, 0),
        check_out_time=time(11, 0)
    )
    
    member2 = baker.make(Member, state=True)
    AttendanceReport.objects.create(
        member=member2,
        date=today,
        branch='Main',
        check_in_time=time(10, 0),
        check_out_time=time(12, 0)
    )
    
    stats = AttendanceReport.get_attendance_stats(start_date=today)
    assert stats['total_visits'] == 2
    assert stats['unique_members'] == 2
    assert stats['avg_duration'] == 120  # Average of 120 and 120 minutes

def test_income_expense_report_str(db):
    report = IncomeExpenseReport.objects.create(
        date=timezone.now().date(),
        income=Decimal('1000.00'),
        expenses=Decimal('600.00')
    )
    assert "Income: 1000.00" in str(report)
    assert report.state is True

def test_income_expense_report_properties(db):
    report = IncomeExpenseReport.objects.create(
        date=timezone.now().date(),
        income=Decimal('1000.00'),
        expenses=Decimal('600.00')
    )
    assert report.net_income == Decimal('400.00')
    assert report.profit_margin == Decimal('40.00')  # 40%

def test_income_expense_report_validation_negative_income(db):
    with pytest.raises(ValidationError, match="Income cannot be negative"):
        report = IncomeExpenseReport(
            date=timezone.now().date(),
            income=Decimal('-100.00'),
            expenses=Decimal('50.00')
        )
        report.full_clean()

def test_income_expense_report_generate_daily_report(db, member):
    # Create payments and costs for today
    today = timezone.now().date()
    
    Payment.objects.create(
        member=member,
        amount=Decimal('500.00'),
        date=today,
        payment_type='Oylik',
        payment_method='cash'
    )
    
    Costs.objects.create(
        cost_name='Rent',  # Use correct field name
        quantity=Decimal('200.00'),
        date=today
    )
    
    # Generate daily report
    report = IncomeExpenseReport.generate_daily_report(today)
    assert report.income == Decimal('500.00')
    assert report.expenses == Decimal('200.00')
    assert report.net_income == Decimal('300.00')

def test_subscription_str(db, member):
    subscription = Subscription.objects.create(
        member=member,
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=30),
        subscription_type='Oylik'
    )
    assert str(subscription).startswith(f"{member}")
    assert subscription.state is True

def test_subscription_properties(db, member):
    start_date = timezone.now().date()
    end_date = start_date + timedelta(days=30)
    
    subscription = Subscription.objects.create(
        member=member,
        start_date=start_date,
        end_date=end_date,
        subscription_type='Oylik'
    )
    
    assert subscription.is_active is True
    assert subscription.days_remaining > 0
    assert subscription.days_remaining <= 30

def test_subscription_validation_invalid_dates(db, member):
    start_date = timezone.now().date()
    end_date = start_date - timedelta(days=1)  # End before start
    
    with pytest.raises(ValidationError, match="End date must be after start date"):
        subscription = Subscription(
            member=member,
            start_date=start_date,
            end_date=end_date,
            subscription_type='Oylik'
        )
        subscription.full_clean()

def test_subscription_get_expiring_soon(db, member):
    # Create subscription expiring in 5 days
    start_date = timezone.now().date()
    end_date = start_date + timedelta(days=5)
    
    subscription = Subscription.objects.create(
        member=member,
        start_date=start_date,
        end_date=end_date,
        subscription_type='Oylik'
    )
    
    expiring = Subscription.get_expiring_soon(days=7)
    assert subscription in expiring

# ------------------ Serializer Tests ------------------

def test_membership_sale_serializer_fields(db, member):
    sale = MembershipSale.objects.create(
        member=member,
        amount=Decimal('500.00'),
        payment_type='Oylik',
        sale_date=timezone.now().date()  # Ensure this is a date
    )
    data = MembershipSaleSerializer(sale).data
    assert 'member' in data
    assert 'amount' in data
    assert 'payment_type' in data
    assert data['amount'] == '500.00'
    # Ensure sale_date is a string in 'YYYY-MM-DD' format
    assert data['sale_date'] == sale.sale_date.isoformat()

def test_membership_sale_serializer_validation(db, member):
    data = {
        'member_id': member.id,
        'amount': '-100.00',  # Invalid negative amount
        'payment_type': 'Oylik'
    }
    serializer = MembershipSaleSerializer(data=data)
    assert not serializer.is_valid()
    assert 'amount' in serializer.errors

def test_attendance_report_serializer_fields(db, member):
    report = AttendanceReport.objects.create(
        member=member,
        date=timezone.now().date(),
        branch='Main',
        check_in_time=time(9, 0)
    )
    data = AttendanceReportSerializer(report).data
    assert 'member' in data
    assert 'date' in data
    assert 'branch' in data
    assert 'check_in_time' in data

def test_income_expense_report_serializer_fields(db):
    report = IncomeExpenseReport.objects.create(
        date=timezone.now().date(),
        income=Decimal('1000.00'),
        expenses=Decimal('600.00')
    )
    data = IncomeExpenseReportSerializer(report).data
    assert 'income' in data
    assert 'expenses' in data
    assert 'net_income' in data
    assert 'profit_margin' in data
    assert data['net_income'] == '400.00'

def test_subscription_serializer_fields(db, member):
    subscription = Subscription.objects.create(
        member=member,
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=30),
        subscription_type='Oylik'
    )
    data = SubscriptionSerializer(subscription).data
    assert 'member' in data
    assert 'start_date' in data
    assert 'end_date' in data
    assert 'is_active' in data
    assert 'days_remaining' in data

# ------------------ API Tests ------------------

@pytest.mark.django_db
def test_dashboard_stats_view(admin_client, member):
    # Create some test data
    Payment.objects.create(
        member=member,
        amount=Decimal('500.00'),
        date=timezone.now().date(),
        payment_type='Oylik',
        payment_method='cash'
    )
    
    Attendance.objects.create(
        member=member,
        code_used='1234'
    )
    
    url = reverse('dashboard-stats')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert 'total_members' in response.data
    assert 'today_income' in response.data
    assert 'today_attendance' in response.data

@pytest.mark.django_db
def test_income_report_view(admin_client, member):
    # Create payments
    Payment.objects.create(
        member=member,
        amount=Decimal('500.00'),
        date=timezone.now().date(),
        payment_type='Oylik',
        payment_method='cash'
    )
    
    url = reverse('income-report')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data
    assert len(response.data['results']) >= 1

@pytest.mark.django_db
def test_income_report_view_with_filters(admin_client, member):
    # Create payments
    Payment.objects.create(
        member=member,
        amount=Decimal('500.00'),
        date=timezone.now().date(),
        payment_type='Oylik',
        payment_method='cash'
    )
    
    url = reverse('income-report')
    response = admin_client.get(url, {
        'payment_type': 'Oylik',
        'start_date': (timezone.now().date() - timedelta(days=1)).isoformat()
    })
    assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
def test_attendance_report_view(admin_client, member):
    # Create attendance
    Attendance.objects.create(
        member=member,
        code_used='1234'
    )
    
    url = reverse('attendance-report')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    # Accept either 'results' or 'attendance' in response for flexibility
    assert 'results' in response.data or 'attendance' in response.data

@pytest.mark.django_db
def test_expiring_memberships_view(admin_client, member):
    url = reverse('expiring-memberships')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data

@pytest.mark.django_db
def test_expiring_memberships_view_with_days_param(admin_client, member):
    url = reverse('expiring-memberships')
    response = admin_client.get(url, {'days': 14})
    assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
def test_unpaid_members_view(admin_client, member):
    url = reverse('unpaid-members')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data

@pytest.mark.django_db
def test_unpaid_members_view_with_days_param(admin_client, member):
    url = reverse('unpaid-members')
    response = admin_client.get(url, {'days': 60})
    assert response.status_code == status.HTTP_200_OK

# ------------------ ViewSet Tests ------------------

@pytest.mark.django_db
def test_membership_sale_viewset_list(admin_client, member):
    MembershipSale.objects.create(
        member=member,
        amount=Decimal('500.00'),
        payment_type='Oylik',
        sale_date=timezone.now().date()
    )
    
    url = reverse('membership-sale-list')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data

@pytest.mark.django_db
def test_membership_sale_viewset_create(admin_client, member):
    url = reverse('membership-sale-list')
    data = {
        'member_id': member.id,
        'amount': '500.00',
        'payment_type': 'Oylik',
        'notes': 'Test sale',
        'sale_date': timezone.now().date().isoformat()  # Ensure correct type
    }
    response = admin_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_attendance_report_viewset_list(admin_client, member):
    AttendanceReport.objects.create(
        member=member,
        date=timezone.now().date(),
        branch='Main',
        check_in_time=time(9, 0)
    )
    
    url = reverse('attendance-report-list')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data

@pytest.mark.django_db
def test_income_expense_report_viewset_list(admin_client):
    IncomeExpenseReport.objects.create(
        date=timezone.now().date(),
        income=Decimal('1000.00'),
        expenses=Decimal('600.00')
    )
    
    url = reverse('income-expense-report-list')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data

@pytest.mark.django_db
def test_subscription_viewset_list(admin_client, member):
    Subscription.objects.create(
        member=member,
        start_date=timezone.now().date(),
        end_date=timezone.now().date() + timedelta(days=30),
        subscription_type='Oylik'
    )
    
    url = reverse('subscription-list')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data

# ------------------ Permission Tests ------------------

@pytest.mark.django_db
def test_dashboard_stats_requires_auth(api_client):
    url = reverse('dashboard-stats')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_income_report_requires_auth(api_client):
    url = reverse('income-report')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_membership_sale_viewset_requires_auth(api_client):
    url = reverse('membership-sale-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

# ------------------ Error Handling Tests ------------------

@pytest.mark.django_db
def test_expiring_memberships_invalid_days_param(admin_client):
    url = reverse('expiring-memberships')
    response = admin_client.get(url, {'days': 'invalid'})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_unpaid_members_invalid_days_param(admin_client):
    url = reverse('unpaid-members')
    response = admin_client.get(url, {'days': 'invalid'})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

# ------------------ Cache Tests ------------------

@pytest.mark.django_db
def test_dashboard_stats_caching(admin_client, member):
    # Clear cache
    cache.clear()
    
    url = reverse('dashboard-stats')
    response1 = admin_client.get(url)
    assert response1.status_code == status.HTTP_200_OK
    
    # Second request should use cache
    response2 = admin_client.get(url)
    assert response2.status_code == status.HTTP_200_OK
    # Check that both responses have the same structure
    assert set(response1.data.keys()) == set(response2.data.keys())
    # Compare profit_margin as '0.00'
    pm1 = f"{Decimal(str(response1.data.get('profit_margin'))):.2f}"
    pm2 = f"{Decimal(str(response2.data.get('profit_margin'))):.2f}"
    assert pm1 == pm2 == '0.00'
