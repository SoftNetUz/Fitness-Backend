from rest_framework import serializers
from .models import Costs, Payment, Debt


class CostsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Costs
        # Exclude state; we might want to expose created_at/created_by/etc., but clients won’t set them.
        exclude = ['state']  
        read_only_fields = ['created_at', 'created_by', 'updated_at', 'updated_by']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        exclude = ['state']
        read_only_fields = ['created_at', 'created_by', 'updated_at', 'updated_by']


class DebtSerializer(serializers.ModelSerializer):
    class Meta:
        model = Debt
        exclude = ['state']
        read_only_fields = ['created_at', 'created_by', 'updated_at', 'updated_by']
