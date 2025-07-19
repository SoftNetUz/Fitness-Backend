import pytest
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from model_bakery import baker
from finance.models import Costs, Payment, Debt
from finance.serializers import CostsSerializer, PaymentSerializer, DebtSerializer
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
    return baker.make(Member)

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

def test_costs_str(db):
    cost = Costs.objects.create(cost_name="Rent", quantity=1000, date=timezone.now().date())
    assert "Rent" in str(cost)
    assert cost.state is True

def test_payment_str(db, member):
    payment = Payment.objects.create(member=member, amount=Decimal('100.00'), payment_type='Oylik', payment_method='cash', date=timezone.now().date())
    assert str(payment).startswith("Payment of")
    assert payment.state is True

def test_debt_str(db, member):
    debt = Debt.objects.create(member=member, amount=Decimal('50.00'), due_date=timezone.now().date())
    assert str(debt).startswith("Debt of")
    assert debt.state is True

def test_active_manager_only_returns_active(db):
    cost = Costs.objects.create(cost_name="Active", quantity=1)
    cost.state = False
    cost.save()
    assert Costs.objects.count() == 0
    assert Costs.all_objects.count() == 1

# ------------------ Serializer Tests ------------------

def test_costs_serializer_fields(db):
    cost = Costs.objects.create(cost_name="Utilities", quantity=200, date=timezone.now().date())
    data = CostsSerializer(cost).data
    assert "cost_name" in data
    assert "quantity" in data
    assert "date" in data

def test_payment_serializer_fields(db, member):
    payment = Payment.objects.create(member=member, amount=Decimal('100.00'), payment_type='Oylik', payment_method='cash', date=timezone.now().date())
    data = PaymentSerializer(payment).data
    assert "member" in data
    assert "amount" in data
    assert "payment_type" in data
    assert "payment_method" in data

def test_debt_serializer_fields(db, member):
    debt = Debt.objects.create(member=member, amount=Decimal('30.00'), due_date=timezone.now().date())
    data = DebtSerializer(debt).data
    assert "member" in data
    assert "amount" in data
    assert "due_date" in data

# ------------------ API Tests ------------------

@pytest.mark.django_db
def test_costs_list(admin_client):
    Costs.objects.create(cost_name="Rent", quantity=1000)
    url = reverse('costs-list')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1

@pytest.mark.django_db
def test_costs_create_admin(admin_client):
    url = reverse('costs-list')
    data = {'cost_name': 'Internet', 'quantity': 150, 'desc': 'Monthly internet', 'date': timezone.now().date().isoformat()}
    response = admin_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_costs_create_non_admin(auth_client):
    url = reverse('costs-list')
    data = {'cost_name': 'Internet', 'quantity': 150, 'desc': 'Monthly internet'}
    response = auth_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_costs_create_invalid(admin_client):
    url = reverse('costs-list')
    data = {'quantity': 150}  # Missing cost_name
    response = admin_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_payment_list(admin_client, member):
    Payment.objects.create(member=member, amount=Decimal('100.00'), payment_type='Oylik', payment_method='cash')
    url = reverse('payments-list')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1

@pytest.mark.django_db
def test_payment_create_admin(admin_client, member):
    url = reverse('payments-list')
    data = {
        'member': member.id,
        'amount': '120.00',
        'payment_type': 'Oylik',
        'payment_method': 'cash',
        'desc': 'Monthly',
        'date': timezone.now().date().isoformat(),
    }
    response = admin_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_payment_create_invalid(admin_client):
    url = reverse('payments-list')
    data = {
        'amount': '120.00',
        'payment_type': 'Oylik',
        'payment_method': 'cash'
    }  # Missing member
    response = admin_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_debt_list(admin_client, member):
    Debt.objects.create(member=member, amount=Decimal('50.00'), due_date=timezone.now().date())
    url = reverse('debts-list')
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1

@pytest.mark.django_db
def test_debt_create_admin(admin_client, member):
    url = reverse('debts-list')
    data = {
        'member': member.id,
        'amount': '60.00',
        'due_date': timezone.now().date().isoformat(),
        'desc': 'Late fee'
    }
    response = admin_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_debt_create_invalid(admin_client):
    url = reverse('debts-list')
    data = {
        'amount': '60.00',
        'due_date': timezone.now().date().isoformat()
    }  # Missing member
    response = admin_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST

# ------------------ Permission/Edge Case Tests ------------------

@pytest.mark.django_db
def test_payment_create_non_admin(auth_client, member):
    url = reverse('payments-list')
    data = {
        'member': member.id,
        'amount': '120.00',
        'payment_type': 'Oylik',
        'payment_method': 'cash',
        'desc': 'Monthly'
    }
    response = auth_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_debt_create_non_admin(auth_client, member):
    url = reverse('debts-list')
    data = {
        'member': member.id,
        'amount': '60.00',
        'due_date': timezone.now().date().isoformat(),
        'desc': 'Late fee'
    }
    response = auth_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_costs_update_admin(admin_client):
    cost = Costs.objects.create(cost_name="Rent", quantity=1000)
    url = reverse('costs-detail', args=[cost.id])
    data = {'cost_name': 'Updated Rent', 'quantity': 2000}
    response = admin_client.put(url, data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['cost_name'] == 'Updated Rent'

@pytest.mark.django_db
def test_costs_delete_admin(admin_client):
    cost = Costs.objects.create(cost_name="Rent", quantity=1000)
    url = reverse('costs-detail', args=[cost.id])
    response = admin_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT

@pytest.mark.django_db
def test_costs_delete_non_admin(auth_client):
    cost = Costs.objects.create(cost_name="Rent", quantity=1000)
    url = reverse('costs-detail', args=[cost.id])
    response = auth_client.delete(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
