# finance/views.py

from rest_framework import viewsets, permissions
from .models import Costs, Payment, Debt
from .serializers import CostsSerializer, PaymentSerializer, DebtSerializer


class CostsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for gym expenses (rent, utilities, etc.).
    Only active (state=True) costs are returned by default.
    """
    queryset = Costs.objects.all()
    serializer_class = CostsSerializer
    permission_classes = [permissions.IsAuthenticated]
    # If you want only staff to create/update/delete:
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for member payments. Only active payments are returned.
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Optional staff-only writes:
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]


class DebtViewSet(viewsets.ModelViewSet):
    """
    ViewSet for member debts. Only active debts are returned.
    """
    queryset = Debt.objects.all()
    serializer_class = DebtSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Optional staff-only writes:
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]
