# reports/serializers.py
from rest_framework import serializers

class IncomeReportSerializer(serializers.Serializer):
    date = serializers.DateField()
    total_income = serializers.DecimalField(max_digits=10, decimal_places=2)

class AttendanceReportSerializer(serializers.Serializer):
    date = serializers.DateField()
    total_check_ins = serializers.IntegerField()

class ExpiringMembershipSerializer(serializers.Serializer):
    member_name = serializers.CharField()
    phone = serializers.CharField()
    expiry_date = serializers.DateField()

class UnpaidMemberSerializer(serializers.Serializer):
    member_name = serializers.CharField()
    phone = serializers.CharField()
    last_payment_date = serializers.DateField()
