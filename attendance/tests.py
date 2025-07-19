import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status
from model_bakery import baker
from attendance.models import Attendance
from attendance.serializers import AttendanceSerializer
from members.models import Member
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
def expired_member(db):
    return baker.make(Member,
        f_name='Expired',
        l_name='Member',
        pin_code='5678',
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

def test_attendance_str(db, member):
    attendance = Attendance.objects.create(member=member, code_used='1234')
    assert str(attendance).startswith(f"{member}")
    assert attendance.state is True

def test_attendance_manager_only_returns_active(db, member):
    attendance = Attendance.objects.create(member=member, code_used='1234')
    attendance.state = False
    attendance.save()
    assert Attendance.objects.count() == 0
    assert Attendance.all_objects.count() == 1

def test_attendance_uniqueness_constraint(db, member):
    # Create first attendance
    attendance1 = Attendance.objects.create(member=member, code_used='1234')
    
    # Try to create another attendance for the same member on the same day
    # We need to manually trigger the save method to test the validation
    attendance2 = Attendance(member=member, code_used='5678', state=True)
    # Ensure both are on the same day
    attendance2.attended_at = attendance1.attended_at
    with pytest.raises(ValidationError, match="A member can only check in once per day"):
        attendance2.save()

def test_attendance_allows_different_days(db, member):
    # Create attendance for today
    today = timezone.now().date()
    Attendance.objects.create(member=member, code_used='1234')
    
    # Create attendance for yesterday (should be allowed)
    yesterday = today - timedelta(days=1)
    attendance_yesterday = Attendance.objects.create(member=member, code_used='1234')
    attendance_yesterday.attended_at = timezone.make_aware(
        timezone.datetime.combine(yesterday, timezone.datetime.min.time())
    )
    attendance_yesterday.save()
    
    assert Attendance.objects.count() == 2

def test_attendance_allows_different_members_same_day(db, member):
    member2 = baker.make(Member, pin_code='5678', state=True)
    
    # Both members can check in on the same day
    Attendance.objects.create(member=member, code_used='1234')
    Attendance.objects.create(member=member2, code_used='5678')
    
    assert Attendance.objects.count() == 2

# ------------------ Serializer Tests ------------------

def test_attendance_serializer_fields(db, member):
    attendance = Attendance.objects.create(member=member, code_used='1234')
    data = AttendanceSerializer(attendance).data
    assert 'member' in data
    assert 'attended_at' in data
    assert 'code_used' in data
    assert data['code_used'] == '1234'

def test_attendance_serializer_nested_member(db, member):
    attendance = Attendance.objects.create(member=member, code_used='1234')
    data = AttendanceSerializer(attendance).data
    assert 'member' in data
    assert data['member']['f_name'] == 'John'
    assert data['member']['l_name'] == 'Doe'

def test_attendance_serializer_create(db, member):
    data = {
        'member_id': member.id,
        'code_used': '1234'
    }
    serializer = AttendanceSerializer(data=data)
    assert serializer.is_valid()
    attendance = serializer.save()
    assert attendance.member == member
    assert attendance.code_used == '1234'

# ------------------ API Tests ------------------

@pytest.mark.django_db
def test_attendance_list(admin_client, member):
    Attendance.objects.create(member=member, code_used='1234')
    url = reverse('attendance-list')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1

@pytest.mark.django_db
def test_attendance_create(admin_client, member):
    url = reverse('attendance-list')
    data = {
        'member_id': member.id,
        'code_used': '1234'
    }
    response = admin_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_attendance_create_invalid(admin_client):
    url = reverse('attendance-list')
    data = {
        'code_used': '1234'
        # Missing member_id
    }
    response = admin_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_attendance_filter_by_month_year(admin_client, member):
    # Create attendance for current month
    Attendance.objects.create(member=member, code_used='1234')
    
    current_month = timezone.now().month
    current_year = timezone.now().year
    
    url = reverse('attendance-list')
    response = admin_client.get(url, {
        'month': current_month,
        'year': current_year
    })
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1

@pytest.mark.django_db
def test_attendance_filter_invalid_month_year(admin_client, member):
    Attendance.objects.create(member=member, code_used='1234')
    
    url = reverse('attendance-list')
    response = admin_client.get(url, {
        'month': 'invalid',
        'year': 'invalid'
    })
    assert response.status_code == status.HTTP_200_OK
    # Should return all records when filter is invalid

# ------------------ CheckIn API Tests ------------------

@pytest.mark.django_db
def test_check_in_success(api_client, member):
    url = reverse('attendance-check-in')
    data = {'pin_code': '1234'}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    assert 'member' in response.data
    assert 'attendance' in response.data
    assert response.data['member']['f_name'] == 'John'

@pytest.mark.django_db
def test_check_in_invalid_pin_length(api_client):
    url = reverse('attendance-check-in')
    data = {'pin_code': '123'}  # Too short
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'PIN kod 4 raqamli' in response.data['error']

@pytest.mark.django_db
def test_check_in_invalid_pin_length_long(api_client):
    url = reverse('attendance-check-in')
    data = {'pin_code': '12345'}  # Too long
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'PIN kod 4 raqamli' in response.data['error']

@pytest.mark.django_db
def test_check_in_missing_pin(api_client):
    url = reverse('attendance-check-in')
    data = {}  # No pin_code
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'PIN kod 4 raqamli' in response.data['error']

@pytest.mark.django_db
def test_check_in_member_not_found(api_client):
    url = reverse('attendance-check-in')
    data = {'pin_code': '9999'}  # Non-existent PIN
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'Bunday a\'zo topilmadi' in response.data['error']

@pytest.mark.django_db
def test_check_in_inactive_member(api_client):
    # Create inactive member
    inactive_member = baker.make(Member, pin_code='9999', state=False)
    
    url = reverse('attendance-check-in')
    data = {'pin_code': '9999'}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'Bunday a\'zo topilmadi' in response.data['error']

@pytest.mark.django_db
def test_check_in_duplicate_same_day(api_client, member):
    url = reverse('attendance-check-in')
    data = {'pin_code': '1234'}
    
    # First check-in
    response1 = api_client.post(url, data, format='json')
    assert response1.status_code == status.HTTP_201_CREATED
    
    # Second check-in on same day
    response2 = api_client.post(url, data, format='json')
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert 'Bugun allaqachon kirilgan' in response2.data['error']

@pytest.mark.django_db
def test_check_in_expired_member(api_client, expired_member):
    # Mock the member as expired by creating a payment with old date
    from finance.models import Payment
    from django.utils import timezone
    
    # Create a payment with old date to make member expired
    old_date = timezone.now().date() - timedelta(days=35)  # More than 30 days ago
    Payment.objects.create(
        member=expired_member,
        amount=Decimal('500.00'),
        payment_type='Oylik',
        payment_method='cash',
        date=old_date
    )
    
    url = reverse('attendance-check-in')
    data = {'pin_code': '5678'}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'A\'zolik muddati tugagan' in response.data['error']

# ------------------ Today Attendance List Tests ------------------

@pytest.mark.django_db
def test_today_attendance_list(admin_client, member):
    # Create attendance for today
    Attendance.objects.create(member=member, code_used='1234')
    
    url = reverse('attendance-today')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1

@pytest.mark.django_db
def test_today_attendance_list_no_records(admin_client):
    url = reverse('attendance-today')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 0

@pytest.mark.django_db
def test_today_attendance_list_requires_auth(api_client, member):
    Attendance.objects.create(member=member, code_used='1234')
    
    url = reverse('attendance-today')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_today_attendance_list_only_today(admin_client, member):
    # Create attendance for today
    today_attendance = Attendance.objects.create(member=member, code_used='1234')
    
    # Create attendance for yesterday
    yesterday = timezone.now().date() - timedelta(days=1)
    yesterday_attendance = Attendance.objects.create(member=member, code_used='1234')
    yesterday_attendance.attended_at = timezone.make_aware(
        timezone.datetime.combine(yesterday, timezone.datetime.min.time())
    )
    yesterday_attendance.save()
    
    url = reverse('attendance-today')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1  # Only today's attendance

# ------------------ Permission Tests ------------------

@pytest.mark.django_db
def test_attendance_list_requires_auth(api_client, member):
    Attendance.objects.create(member=member, code_used='1234')
    
    url = reverse('attendance-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_attendance_create_requires_auth(api_client, member):
    url = reverse('attendance-list')
    data = {
        'member_id': member.id,
        'code_used': '1234'
    }
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_attendance_update(admin_client, member):
    attendance = Attendance.objects.create(member=member, code_used='1234')
    url = reverse('attendance-detail', args=[attendance.id])
    data = {
        'member_id': member.id,
        'code_used': '5678'
    }
    response = admin_client.put(url, data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['code_used'] == '5678'

@pytest.mark.django_db
def test_attendance_delete(admin_client, member):
    attendance = Attendance.objects.create(member=member, code_used='1234')
    url = reverse('attendance-detail', args=[attendance.id])
    response = admin_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT

# ------------------ Edge Cases ------------------

@pytest.mark.django_db
def test_check_in_with_empty_pin(api_client):
    url = reverse('attendance-check-in')
    data = {'pin_code': ''}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_check_in_with_none_pin(api_client):
    url = reverse('attendance-check-in')
    data = {'pin_code': None}
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_attendance_ordering(db, member):
    # Create attendances with different times on different days to avoid uniqueness constraint
    yesterday = timezone.now().date() - timedelta(days=1)
    
    # First attendance (yesterday)
    attendance1 = Attendance.objects.create(member=member, code_used='1234')
    attendance1.attended_at = timezone.make_aware(
        timezone.datetime.combine(yesterday, timezone.datetime.min.time())
    )
    attendance1.save()
    
    # Second attendance (today)
    attendance2 = Attendance.objects.create(member=member, code_used='5678')
    
    # Check ordering (should be newest first)
    attendances = Attendance.objects.all()
    assert attendances[0] == attendance2
    assert attendances[1] == attendance1

@pytest.mark.django_db
def test_attendance_with_code_used(db, member):
    attendance = Attendance.objects.create(member=member, code_used='1234')
    assert attendance.code_used == '1234'
    assert attendance.member == member
