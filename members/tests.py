import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from model_bakery import baker
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io
from members.models import FitnessClub, Member
from attendance.models import Attendance
from members.serializers import FitnessClubSerializer, MemberSerializer
from utils.payments import get_expiry_date, is_expired, is_expiring_soon

User = get_user_model()

@pytest.fixture
def user(db):
    return User.objects.create_user(username='user', email='user@example.com', password='pass1234')

@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(username='admin', email='admin@example.com', password='adminpass')

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

@pytest.fixture
def test_image():
    file = io.BytesIO()
    image = Image.new('RGBA', size=(100, 100), color=(155, 0, 0))
    image.save(file, 'png')
    file.name = 'test.png'
    file.seek(0)
    return SimpleUploadedFile('test.png', file.getvalue(), content_type='image/png')

# ------------------ Model Tests ------------------

def test_fitness_club_creation(db, user):
    club = FitnessClub.objects.create(
        name='Test Club', daily=50.0, monthly=500.0, vip=True, created_by=user
    )
    assert club.name == 'Test Club'
    assert club.daily == 50.0
    assert club.monthly == 500.0
    assert club.vip is True
    assert club.state is True
    assert str(club) == 'Test Club'


def test_fitness_club_singleton(db, user):
    club1 = FitnessClub.get_instance()
    club2 = FitnessClub.get_instance()
    assert club1.id == club2.id
    assert FitnessClub.objects.count() == 1


def test_member_creation(db, user):
    member = Member.objects.create(
        f_name='John', l_name='Doe', phone='+998901234567', gender='E', pin_code='1234',
        payment_amount=500.0, payment_type='Oylik', branch='Main', created_by=user
    )
    assert member.f_name == 'John'
    assert member.l_name == 'Doe'
    assert member.phone == '+998901234567'
    assert member.gender == 'E'
    assert member.pin_code == '1234'
    assert member.payment_amount == 500.0
    assert member.payment_type == 'Oylik'
    assert member.branch == 'Main'
    assert member.state is True
    assert str(member) == 'John Doe'


def test_member_pin_code_uniqueness(db, user):
    Member.objects.create(
        f_name='John', l_name='Doe', phone='+998901234567', gender='E', pin_code='1234',
        payment_amount=500.0, payment_type='Oylik', branch='Main', created_by=user
    )
    with pytest.raises(Exception):
        Member.objects.create(
            f_name='Jane', l_name='Smith', phone='+998901234568', gender='A', pin_code='1234',
            payment_amount=300.0, payment_type='Kunlik', branch='Main', created_by=user
        )


def test_attended_time_creation(db, user):
    member = baker.make(Member, created_by=user)
    attendance = Attendance.objects.create(member=member, attended_at=date.today())
    assert attendance.member == member
    assert attendance.attended_at == date.today()


def test_attended_time_uniqueness(db, user):
    member = baker.make(Member, created_by=user)
    Attendance.objects.create(member=member, attended_at=date.today())
    with pytest.raises(Exception):
        Attendance.objects.create(member=member, attended_at=date.today())

# ------------------ Serializer Tests ------------------

def test_fitness_club_serializer(db, user):
    club = FitnessClub.objects.create(
        name='Test Club', daily=50.0, monthly=500.0, vip=True, created_by=user
    )
    data = FitnessClubSerializer(club).data
    assert data['name'] == 'Test Club'
    assert float(data['daily']) == 50.0
    assert float(data['monthly']) == 500.0
    assert data['vip'] is True


def test_member_serializer(db, user):
    member = Member.objects.create(
        f_name='John', l_name='Doe', phone='+998901234567', gender='E', pin_code='1234',
        payment_amount=500.0, payment_type='Oylik', branch='Main', created_by=user
    )
    data = MemberSerializer(member).data
    assert data['f_name'] == 'John'
    assert data['l_name'] == 'Doe'
    assert data['gender'] == 'E'
    assert data['pin_code'] == '1234'
    assert float(data['payment_amount']) == 500.0
    assert data['payment_type'] == 'Oylik'
    assert data['branch'] == 'Main'

# ------------------ API Tests ------------------

def test_fitness_club_list_requires_authentication(api_client):
    url = reverse('fitnessclub-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_fitness_club_list_admin_access(admin_client):
    url = reverse('fitnessclub-list')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK


def test_fitness_club_create_admin_access(admin_client):
    url = reverse('fitnessclub-list')
    data = {
        'name': 'New Club',
        'daily': '60.00',
        'monthly': '600.00',
        'vip': True
    }
    response = admin_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['name'] == 'New Club'


def test_member_list_requires_authentication(api_client):
    url = reverse('member-list')
    response = api_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_member_list_authenticated_access(auth_client):
    url = reverse('member-list')
    response = auth_client.get(url)
    assert response.status_code == status.HTTP_200_OK


def test_member_create_authenticated_access(auth_client, user):
    url = reverse('member-list')
    data = {
        'f_name': 'Alice',
        'l_name': 'Wonder',
        'phone': '+998901234569',
        'gender': 'A',
        'pin_code': '5678',
        'payment_amount': '400.00',
        'payment_type': 'Kunlik',
        'branch': 'Branch 2'
    }
    response = auth_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['f_name'] == 'Alice'


def test_member_invalid_data_creation(auth_client):
    url = reverse('member-list')
    data = {
        'f_name': '',  # Invalid
        'l_name': 'Wonder',
        'phone': '+998901234569',
        'gender': 'A',
        'pin_code': '5678',
        'payment_amount': '400.00',
        'payment_type': 'Kunlik',
        'branch': 'Branch 2'
    }
    response = auth_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'f_name' in response.data

# ------------------ Business Logic Tests ------------------

def test_get_expiry_date_monthly(db, user):
    member = baker.make(Member, payment_type='Oylik', created_by=user)
    expiry = get_expiry_date(member)
    assert isinstance(expiry, date)


def test_is_expired_monthly_not_expired(db, user):
    member = baker.make(Member, payment_type='Oylik', created_by=user)
    assert is_expired(member) is False


def test_is_expiring_soon_monthly(db, user):
    member = baker.make(Member, payment_type='Oylik', created_by=user)
    soon = is_expiring_soon(member)
    assert isinstance(soon, bool)

# ------------------ Edge/Negative Cases ------------------

def test_member_search_functionality(auth_client, user):
    baker.make(Member, f_name='Bob', l_name='Builder', created_by=user)
    url = reverse('member-list') + '?search=Bob'
    response = auth_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert any('Bob' in m['f_name'] for m in response.data)


def test_member_update_authenticated_access(auth_client, user):
    member = baker.make(Member, created_by=user)
    url = reverse('member-detail', args=[member.id])
    data = {'f_name': 'Updated'}
    response = auth_client.patch(url, data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['f_name'] == 'Updated'


def test_member_update_invalid(auth_client, user):
    member = baker.make(Member, created_by=user)
    url = reverse('member-detail', args=[member.id])
    data = {'f_name': ''}  # Invalid
    response = auth_client.patch(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'f_name' in response.data
