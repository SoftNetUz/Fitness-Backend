import json
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io
import calendar
from django.utils import timezone

from .models import FitnessClub, Member, AttendedTime, PAYMENT_TYPE
from .serializers import FitnessClubSerializer, MemberSerializer, AttendanceSerializer, MemberStatsSerializer
from utils.payments import get_expiry_date, is_expired, is_expiring_soon

User = get_user_model()


def create_test_image():
    """Helper function to create a test image for logo uploads"""
    file = io.BytesIO()
    image = Image.new('RGBA', size=(100, 100), color=(155, 0, 0))
    image.save(file, 'png')
    file.name = 'test.png'
    file.seek(0)
    return SimpleUploadedFile('test.png', file.getvalue(), content_type='image/png')


def create_test_user():
    """Helper function to create a test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


def create_test_admin_user():
    """Helper function to create a test admin user"""
    return User.objects.create_user(
        username='adminuser',
        email='admin@example.com',
        password='adminpass123',
        is_staff=True,
        is_superuser=True
    )


class FitnessClubModelTest(TestCase):
    """Test cases for FitnessClub model"""

    def setUp(self):
        self.user = create_test_user()
        self.fitness_club_data = {
            'name': 'Test Fitness Club',
            'daily': Decimal('50.00'),
            'monthly': Decimal('500.00'),
            'vip': False,
            'created_by': self.user
        }

    def test_fitness_club_creation(self):
        """Test creating a fitness club"""
        fitness_club = FitnessClub.objects.create(**self.fitness_club_data)
        self.assertEqual(fitness_club.name, 'Test Fitness Club')
        self.assertEqual(fitness_club.daily, Decimal('50.00'))
        self.assertEqual(fitness_club.monthly, Decimal('500.00'))
        self.assertFalse(fitness_club.vip)
        self.assertTrue(fitness_club.state)

    def test_fitness_club_str_representation(self):
        """Test string representation of fitness club"""
        fitness_club = FitnessClub.objects.create(**self.fitness_club_data)
        self.assertEqual(str(fitness_club), 'Test Fitness Club')

    def test_singleton_pattern(self):
        """Test that only one fitness club instance can exist"""
        club1 = FitnessClub.get_instance()
        club2 = FitnessClub.get_instance()
        self.assertEqual(club1.id, club2.id)
        self.assertEqual(FitnessClub.objects.count(), 1)


class MemberModelTest(TestCase):
    """Test cases for Member model"""

    def setUp(self):
        self.user = create_test_user()
        self.member_data = {
            'f_name': 'John',
            'l_name': 'Doe',
            'phone': '+998901234567',
            'gender': 'E',
            'pin_code': '1234',
            'payment_amount': Decimal('500.00'),
            'payment_type': 'Oylik',
            'branch': 'Main Branch',
            'created_by': self.user
        }

    def test_member_creation(self):
        """Test creating a member"""
        member = Member.objects.create(**self.member_data)
        self.assertEqual(member.f_name, 'John')
        self.assertEqual(member.l_name, 'Doe')
        self.assertEqual(member.phone, '+998901234567')
        self.assertEqual(member.gender, 'E')
        self.assertEqual(member.pin_code, '1234')
        self.assertEqual(member.payment_amount, Decimal('500.00'))
        self.assertEqual(member.payment_type, 'Oylik')
        self.assertEqual(member.branch, 'Main Branch')
        self.assertTrue(member.state)

    def test_member_str_representation(self):
        """Test string representation of member"""
        member = Member.objects.create(**self.member_data)
        self.assertEqual(str(member), 'John Doe')

    def test_member_pin_code_uniqueness(self):
        """Test that PIN codes must be unique"""
        Member.objects.create(**self.member_data)
        duplicate_data = self.member_data.copy()
        duplicate_data['phone'] = '+998901234568'  # Different phone
        
        with self.assertRaises(Exception):
            Member.objects.create(**duplicate_data)

    def test_member_gender_choices(self):
        """Test member gender choices"""
        member = Member.objects.create(**self.member_data)
        self.assertIn(member.gender, [choice[0] for choice in Member.Gender.choices])

    def test_member_payment_type_choices(self):
        """Test member payment type choices"""
        for payment_type, _ in PAYMENT_TYPE:
            member_data = self.member_data.copy()
            member_data['payment_type'] = payment_type
            member_data['pin_code'] = f'123{payment_type[0]}'  # Unique PIN
            member = Member.objects.create(**member_data)
            self.assertEqual(member.payment_type, payment_type)


class AttendedTimeModelTest(TestCase):
    """Test cases for AttendedTime model"""

    def setUp(self):
        self.user = create_test_user()
        self.member = Member.objects.create(
            f_name='Jane',
            l_name='Smith',
            phone='+998901234568',
            gender='A',
            pin_code='5678',
            payment_amount=Decimal('300.00'),
            payment_type='Kunlik',
            created_by=self.user
        )

    def test_attended_time_creation(self):
        """Test creating attendance record"""
        attendance = AttendedTime.objects.create(
            member=self.member,
            attended_at=date.today()
        )
        self.assertEqual(attendance.member, self.member)
        self.assertEqual(attendance.attended_at, date.today())

    def test_attended_time_uniqueness(self):
        """Test that same member cannot have multiple attendance records for same date"""
        AttendedTime.objects.create(
            member=self.member,
            attended_at=date.today()
        )
        
        with self.assertRaises(Exception):
            AttendedTime.objects.create(
                member=self.member,
                attended_at=date.today()
            )


class FitnessClubSerializerTest(TestCase):
    """Test cases for FitnessClubSerializer"""

    def setUp(self):
        self.user = create_test_user()
        self.fitness_club = FitnessClub.objects.create(
            name='Test Club',
            daily=Decimal('50.00'),
            monthly=Decimal('500.00'),
            vip=True,
            created_by=self.user
        )
        self.serializer = FitnessClubSerializer(instance=self.fitness_club)

    def test_fitness_club_serializer_fields(self):
        """Test that serializer contains expected fields"""
        data = self.serializer.data
        expected_fields = {
            'id', 'name', 'logo', 'logo_url', 'daily', 'monthly', 'vip',
            'created_at', 'created_by', 'updated_at', 'updated_by', 'state'
        }
        self.assertEqual(set(data.keys()), expected_fields)

    def test_fitness_club_serializer_data(self):
        """Test serializer data accuracy"""
        data = self.serializer.data
        self.assertEqual(data['name'], 'Test Club')
        self.assertEqual(Decimal(data['daily']), Decimal('50.00'))
        self.assertEqual(Decimal(data['monthly']), Decimal('500.00'))
        self.assertTrue(data['vip'])

    def test_fitness_club_serializer_validation(self):
        """Test serializer validation"""
        valid_data = {
            'name': 'New Club',
            'daily': '75.00',
            'monthly': '750.00',
            'vip': False
        }
        serializer = FitnessClubSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())

    def test_fitness_club_serializer_invalid_data(self):
        """Test serializer with invalid data"""
        invalid_data = {
            'name': '',  # Empty name
            'daily': 'invalid_decimal',  # Still required, even if invalid
            'monthly': '750.00'
        }
        serializer = FitnessClubSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())


class MemberSerializerTest(TestCase):
    """Test cases for MemberSerializer"""

    def setUp(self):
        self.user = create_test_user()
        self.member = Member.objects.create(
            f_name='John',
            l_name='Doe',
            phone='+998901234567',
            gender='E',
            pin_code='1234',
            payment_amount=Decimal('500.00'),
            payment_type='Oylik',
            branch='Main Branch',
            created_by=self.user
        )
        self.serializer = MemberSerializer(instance=self.member)

    def test_member_serializer_fields(self):
        """Test that serializer contains expected fields"""
        data = self.serializer.data
        expected_fields = {
            'id', 'f_name', 'l_name', 'phone', 'gender', 'pin_code',
            'payment_amount', 'payment_type', 'branch', 'gender_display',
            'payment_display', 'expiry_date', 'is_expiring', 'is_expired',
            'created_at', 'created_by', 'updated_at', 'updated_by', 'state'
        }
        self.assertEqual(set(data.keys()), expected_fields)

    def test_member_serializer_data(self):
        """Test serializer data accuracy"""
        data = self.serializer.data
        self.assertEqual(data['f_name'], 'John')
        self.assertEqual(data['l_name'], 'Doe')
        self.assertEqual(data['phone'], '+998901234567')
        self.assertEqual(data['gender'], 'E')
        self.assertEqual(data['pin_code'], '1234')
        self.assertEqual(Decimal(data['payment_amount']), Decimal('500.00'))
        self.assertEqual(data['payment_type'], 'Oylik')
        self.assertEqual(data['branch'], 'Main Branch')

    def test_member_serializer_gender_display(self):
        """Test gender display field"""
        data = self.serializer.data
        self.assertEqual(data['gender_display'], 'Erkak')

    def test_member_serializer_payment_display(self):
        """Test payment type display field"""
        data = self.serializer.data
        self.assertEqual(data['payment_display'], 'Oylik')

    def test_member_serializer_validation(self):
        """Test serializer validation"""
        valid_data = {
            'f_name': 'New',
            'l_name': 'Member',
            'phone': '+998901234569',
            'gender': 'E',
            'pin_code': '9999',
            'payment_amount': '600.00',
            'payment_type': 'Premium',
            'branch': 'Branch 2'
        }
        serializer = MemberSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())


class FitnessClubViewSetTest(APITestCase):
    """Test cases for FitnessClubViewSet"""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = create_test_admin_user()
        self.regular_user = create_test_user()
        self.fitness_club = FitnessClub.objects.create(
            name='Test Club',
            daily=Decimal('50.00'),
            monthly=Decimal('500.00'),
            vip=True,
            created_by=self.admin_user
        )

    def get_auth_headers(self, user):
        """Helper method to get authentication headers"""
        refresh = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def test_fitness_club_list_requires_authentication(self):
        """Test that fitness club list requires authentication"""
        url = reverse('fitnessclub-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_fitness_club_list_requires_admin(self):
        """Test that fitness club list requires admin permissions"""
        url = reverse('fitnessclub-list')
        headers = self.get_auth_headers(self.regular_user)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_fitness_club_list_admin_access(self):
        """Test that admin can access fitness club list"""
        url = reverse('fitnessclub-list')
        headers = self.get_auth_headers(self.admin_user)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_fitness_club_create_admin_access(self):
        """Test that admin can create fitness club"""
        url = reverse('fitnessclub-list')
        headers = self.get_auth_headers(self.admin_user)
        data = {
            'name': 'New Club',
            'daily': '75.00',
            'monthly': '750.00',
            'vip': False
        }
        response = self.client.post(url, json.dumps(data), content_type='application/json', **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Club')

    def test_fitness_club_update_admin_access(self):
        """Test that admin can update fitness club"""
        url = reverse('fitnessclub-detail', args=[self.fitness_club.id])
        headers = self.get_auth_headers(self.admin_user)
        data = {
            'name': 'Updated Club',
            'daily': '60.00',
            'monthly': '600.00',
            'vip': False
        }
        response = self.client.put(url, json.dumps(data), content_type='application/json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Club')


class MemberViewSetTest(APITestCase):
    """Test cases for MemberViewSet"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.member = Member.objects.create(
            f_name='John',
            l_name='Doe',
            phone='+998901234567',
            gender='E',
            pin_code='1234',
            payment_amount=Decimal('500.00'),
            payment_type='Oylik',
            branch='Main Branch',
            created_by=self.user
        )

    def get_auth_headers(self, user):
        """Helper method to get authentication headers"""
        refresh = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def test_member_list_requires_authentication(self):
        """Test that member list requires authentication"""
        url = reverse('members-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_member_list_authenticated_access(self):
        """Test that authenticated users can access member list"""
        url = reverse('members-list')
        headers = self.get_auth_headers(self.user)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_member_create_authenticated_access(self):
        """Test that authenticated users can create members"""
        url = reverse('members-list')
        headers = self.get_auth_headers(self.user)
        data = {
            'f_name': 'Jane',
            'l_name': 'Smith',
            'phone': '+998901234568',
            'gender': 'A',
            'pin_code': '5678',
            'payment_amount': '300.00',
            'payment_type': 'Kunlik',
            'branch': 'Branch 2'
        }
        response = self.client.post(url, json.dumps(data), content_type='application/json', **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['f_name'], 'Jane')

    def test_member_search_functionality(self):
        """Test member search functionality"""
        url = reverse('members-list')
        headers = self.get_auth_headers(self.user)
        response = self.client.get(url, {'search': 'John'}, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_member_invalid_data_creation(self):
        """Test member creation with invalid data"""
        url = reverse('members-list')
        headers = self.get_auth_headers(self.user)
        invalid_data = {
            'f_name': '',  # Empty name
            'l_name': 'Doe',
            'phone': 'invalid_phone',
            'gender': 'X',  # Invalid gender
            'pin_code': '123',  # Too short
            'payment_amount': 'invalid_amount',
            'payment_type': 'Invalid'
        }
        response = self.client.post(url, json.dumps(invalid_data), content_type='application/json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_member_update_authenticated_access(self):
        """Test that authenticated users can update members"""
        url = reverse('members-detail', args=[self.member.id])
        headers = self.get_auth_headers(self.user)
        data = {
            'f_name': 'Johnny',
            'l_name': 'Doe',
            'phone': '+998901234567',
            'gender': 'E',
            'pin_code': '1234',
            'payment_amount': '600.00',
            'payment_type': 'Premium',
            'branch': 'Updated Branch'
        }
        response = self.client.put(url, json.dumps(data), content_type='application/json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['f_name'], 'Johnny')


class AttendanceViewSetTest(APITestCase):
    """Test cases for AttendanceViewSet"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.member = Member.objects.create(
            f_name='John',
            l_name='Doe',
            phone='+998901234567',
            gender='E',
            pin_code='1234',
            payment_amount=Decimal('500.00'),
            payment_type='Oylik',
            created_by=self.user
        )
        self.attendance = AttendedTime.objects.create(
            member=self.member,
            attended_at=date.today()
        )

    def get_auth_headers(self, user):
        """Helper method to get authentication headers"""
        refresh = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def test_attendance_list_requires_authentication(self):
        """Test that attendance list requires authentication"""
        url = reverse('attended-time-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_attendance_list_authenticated_access(self):
        """Test that authenticated users can access attendance list"""
        url = reverse('attended-time-list')
        headers = self.get_auth_headers(self.user)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_attendance_create_authenticated_access(self):
        """Test that authenticated users can create attendance records"""
        url = reverse('attended-time-list')
        headers = self.get_auth_headers(self.user)
        data = {
            'member': self.member.id,
            'attended_at': (date.today() + timedelta(days=1)).isoformat()
        }
        response = self.client.post(url, json.dumps(data), content_type='application/json', **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_attendance_duplicate_date_validation(self):
        """Test that duplicate attendance records for same date are not allowed"""
        url = reverse('attended-time-list')
        headers = self.get_auth_headers(self.user)
        data = {
            'member': self.member.id,
            'attended_at': date.today().isoformat()  # Same date as existing
        }
        response = self.client.post(url, json.dumps(data), content_type='application/json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MemberStatsAPIViewTest(APITestCase):
    """Test cases for MemberStatsAPIView"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        
        # Create test members
        self.monthly_member = Member.objects.create(
            f_name='John',
            l_name='Doe',
            phone='+998901234567',
            gender='E',
            pin_code='1234',
            payment_amount=Decimal('500.00'),
            payment_type='Oylik',
            created_by=self.user
        )
        
        self.premium_member = Member.objects.create(
            f_name='Jane',
            l_name='Smith',
            phone='+998901234568',
            gender='A',
            pin_code='5678',
            payment_amount=Decimal('1000.00'),
            payment_type='Premium',
            created_by=self.user
        )
        
        self.daily_member = Member.objects.create(
            f_name='Bob',
            l_name='Johnson',
            phone='+998901234569',
            gender='E',
            pin_code='9999',
            payment_amount=Decimal('50.00'),
            payment_type='Kunlik',
            created_by=self.user
        )

    def get_auth_headers(self, user):
        """Helper method to get authentication headers"""
        refresh = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def test_member_stats_requires_authentication(self):
        """Test that member stats requires authentication"""
        url = reverse('member-stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_member_stats_authenticated_access(self):
        """Test that authenticated users can access member stats"""
        url = reverse('member-stats')
        headers = self.get_auth_headers(self.user)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        self.assertEqual(data['total_members'], 3)
        self.assertEqual(data['monthly_members'], 1)
        self.assertEqual(data['vip_members'], 1)
        self.assertEqual(data['daily_members'], 1)
        self.assertIn('expiring_members', data)
        self.assertIn('expired_members', data)

    def test_member_stats_with_inactive_members(self):
        """Test that inactive members are not counted in stats"""
        # Create an inactive member
        inactive_member = Member.objects.create(
            f_name='Inactive',
            l_name='User',
            phone='+998901234570',
            gender='E',
            pin_code='0000',
            payment_amount=Decimal('300.00'),
            payment_type='Oylik',
            state=False,  # Inactive
            created_by=self.user
        )
        
        url = reverse('member-stats')
        headers = self.get_auth_headers(self.user)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        self.assertEqual(data['total_members'], 3)  # Should not include inactive member


class PaymentUtilsTest(TestCase):
    """Test cases for payment utility functions"""

    def setUp(self):
        self.user = create_test_user()
        self.monthly_member = Member.objects.create(
            f_name='John',
            l_name='Doe',
            phone='+998901234567',
            gender='E',
            pin_code='1234',
            payment_amount=Decimal('500.00'),
            payment_type='Oylik',
            created_by=self.user
        )
        
        self.premium_member = Member.objects.create(
            f_name='Jane',
            l_name='Smith',
            phone='+998901234568',
            gender='A',
            pin_code='5678',
            payment_amount=Decimal('1000.00'),
            payment_type='Premium',
            created_by=self.user
        )
        
        self.daily_member = Member.objects.create(
            f_name='Bob',
            l_name='Johnson',
            phone='+998901234569',
            gender='E',
            pin_code='9999',
            payment_amount=Decimal('50.00'),
            payment_type='Kunlik',
            created_by=self.user
        )

    def test_get_expiry_date_monthly(self):
        """Test expiry date calculation for monthly members"""
        expiry_date = get_expiry_date(self.monthly_member)
        expected_date = self.monthly_member.created_at.date() + timedelta(days=30)
        self.assertEqual(expiry_date, expected_date)

    def test_get_expiry_date_premium(self):
        """Test expiry date calculation for premium members"""
        expiry_date = get_expiry_date(self.premium_member)
        # Premium expires at end of month
        expected_date = date(
            self.premium_member.created_at.year,
            self.premium_member.created_at.month,
            calendar.monthrange(self.premium_member.created_at.year, self.premium_member.created_at.month)[1]
        )
        self.assertEqual(expiry_date, expected_date)

    def test_get_expiry_date_daily(self):
        """Test expiry date calculation for daily members"""
        expiry_date = get_expiry_date(self.daily_member)
        expected_date = self.daily_member.created_at.date()
        self.assertEqual(expiry_date, expected_date)

    def test_is_expired_monthly_not_expired(self):
        """Test monthly member not expired"""
        result = is_expired(self.monthly_member)
        self.assertFalse(result)

    def test_is_expired_monthly_expired(self):
        """Test monthly member expired"""
        # Set created_at to 31 days ago
        self.monthly_member.created_at = timezone.now() - timedelta(days=31)
        self.monthly_member.save()
        result = is_expired(self.monthly_member)
        self.assertTrue(result)

    def test_is_expired_premium_not_expired(self):
        """Test premium member not expired"""
        result = is_expired(self.premium_member)
        self.assertFalse(result)

    def test_is_expired_daily_expired(self):
        """Test daily member expired"""
        # Set created_at to yesterday
        self.daily_member.created_at = timezone.now() - timedelta(days=1)
        self.daily_member.save()
        result = is_expired(self.daily_member)
        self.assertTrue(result)

    def test_is_expiring_soon_monthly(self):
        """Test monthly member expiring soon"""
        # Set created_at to 28 days ago (expires in 2 days)
        self.monthly_member.created_at = timezone.now() - timedelta(days=28)
        self.monthly_member.save()
        result = is_expiring_soon(self.monthly_member, threshold_days=3)
        self.assertTrue(result)

    def test_is_expiring_soon_daily(self):
        """Test daily member expiring soon"""
        result = is_expiring_soon(self.daily_member, threshold_days=3)
        # Daily members expire same day, so should be True
        self.assertTrue(result)


class IntegrationTest(APITestCase):
    """Integration tests for the complete member management flow"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()

    def get_auth_headers(self, user):
        """Helper method to get authentication headers"""
        refresh = RefreshToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def test_complete_member_management_flow(self):
        """Test complete member management flow"""
        headers = self.get_auth_headers(self.user)
        
        # 1. Create a member
        member_data = {
            'f_name': 'Integration',
            'l_name': 'Test',
            'phone': '+998901234571',
            'gender': 'E',
            'pin_code': '1111',
            'payment_amount': '500.00',
            'payment_type': 'Oylik',
            'branch': 'Test Branch'
        }
        
        create_response = self.client.post(reverse('members-list'), json.dumps(member_data), content_type='application/json', **headers)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        member_id = create_response.data['id']
        
        # 2. Get member details
        detail_response = self.client.get(reverse('members-detail', args=[member_id]), **headers)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['f_name'], 'Integration')
        
        # 3. Create attendance record
        attendance_data = {
            'member': member_id,
            'attended_at': date.today().isoformat()
        }
        attendance_response = self.client.post(reverse('attended-time-list'), json.dumps(attendance_data), content_type='application/json', **headers)
        self.assertEqual(attendance_response.status_code, status.HTTP_201_CREATED)
        
        # 4. Update member
        update_data = member_data.copy()
        update_data['f_name'] = 'Updated Integration'
        update_response = self.client.put(reverse('members-detail', args=[member_id]), json.dumps(update_data), content_type='application/json', **headers)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['f_name'], 'Updated Integration')
        
        # 5. Check member stats
        stats_response = self.client.get(reverse('member-stats'), **headers)
        self.assertEqual(stats_response.status_code, status.HTTP_200_OK)
        self.assertEqual(stats_response.data['total_members'], 1)
        
        # 6. Delete member
        delete_response = self.client.delete(reverse('members-detail', args=[member_id]), **headers)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 7. Verify member is deleted
        detail_response = self.client.get(reverse('members-detail', args=[member_id]), **headers)
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_error_handling_scenarios(self):
        """Test various error handling scenarios"""
        headers = self.get_auth_headers(self.user)
        
        # Test invalid member creation
        invalid_data = {
            'f_name': '',  # Empty name
            'l_name': 'Test',
            'phone': 'invalid_phone',
            'gender': 'X',  # Invalid gender
            'pin_code': '123',  # Too short
            'payment_amount': 'invalid_amount',
            'payment_type': 'Invalid'
        }
        
        response = self.client.post(reverse('members-list'), json.dumps(invalid_data), content_type='application/json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test accessing non-existent member
        response = self.client.get(reverse('members-detail', args=[99999]), **headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Test duplicate PIN code
        member1_data = {
            'f_name': 'Test1',
            'l_name': 'User',
            'phone': '+998901234572',
            'gender': 'E',
            'pin_code': '2222',
            'payment_amount': '300.00',
            'payment_type': 'Kunlik'
        }
        
        member2_data = {
            'f_name': 'Test2',
            'l_name': 'User',
            'phone': '+998901234573',
            'gender': 'E',
            'pin_code': '2222',  # Same PIN
            'payment_amount': '400.00',
            'payment_type': 'Oylik'
        }
        
        # Create first member
        response1 = self.client.post(reverse('members-list'), json.dumps(member1_data), content_type='application/json', **headers)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Try to create second member with same PIN
        response2 = self.client.post(reverse('members-list'), json.dumps(member2_data), content_type='application/json', **headers)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
