# reports/serializers.py
from rest_framework import serializers
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import (
    MembershipSale, 
    AttendanceReport, 
    IncomeExpenseReport, 
    Subscription,
    DailyReport,
    MonthlyReport
)
from members.serializers import MemberSerializer


class MembershipSaleSerializer(serializers.ModelSerializer):
    """Serializer for MembershipSale model."""
    
    member = MemberSerializer(read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(
        queryset=MembershipSale.member.field.related_model.objects.all(),
        write_only=True,
        source='member'
    )
    
    class Meta:
        model = MembershipSale
        fields = [
            'id', 'member', 'member_id', 'sale_date', 'amount', 
            'payment_type', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Sale amount must be greater than zero.")
        return value

    def validate_sale_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Sale date cannot be in the future.")
        return value


class AttendanceReportSerializer(serializers.ModelSerializer):
    """Serializer for AttendanceReport model."""
    
    member = MemberSerializer(read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(
        queryset=AttendanceReport.member.field.related_model.objects.all(),
        write_only=True,
        source='member'
    )
    
    class Meta:
        model = AttendanceReport
        fields = [
            'id', 'member', 'member_id', 'date', 'branch', 
            'check_in_time', 'check_out_time', 'duration_minutes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'duration_minutes']

    def validate(self, data):
        if 'check_out_time' in data and 'check_in_time' in data:
            if data['check_in_time'] >= data['check_out_time']:
                raise serializers.ValidationError(
                    "Check-out time must be after check-in time."
                )
        return data


class IncomeExpenseReportSerializer(serializers.ModelSerializer):
    """Serializer for IncomeExpenseReport model."""
    
    net_income = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        read_only=True
    )
    profit_margin = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = IncomeExpenseReport
        fields = [
            'id', 'date', 'income', 'expenses', 'net_income', 
            'profit_margin', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'net_income', 'profit_margin']

    def validate_income(self, value):
        if value < 0:
            raise serializers.ValidationError("Income cannot be negative.")
        return value

    def validate_expenses(self, value):
        if value < 0:
            raise serializers.ValidationError("Expenses cannot be negative.")
        return value


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscription model."""
    
    member = MemberSerializer(read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(
        queryset=Subscription.member.field.related_model.objects.all(),
        write_only=True,
        source='member'
    )
    is_expired = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'member', 'member_id', 'start_date', 'end_date',
            'subscription_type', 'is_active', 'is_expired', 
            'days_remaining', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'is_active', 
            'is_expired', 'days_remaining'
        ]

    def validate(self, data):
        if 'start_date' in data and 'end_date' in data:
            if data['start_date'] >= data['end_date']:
                raise serializers.ValidationError(
                    "End date must be after start date."
                )
        return data


# Report-specific serializers for API responses
class IncomeReportSerializer(serializers.Serializer):
    """Serializer for income report data."""
    
    date = serializers.DateField()
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_count = serializers.IntegerField()
    avg_payment = serializers.DecimalField(max_digits=10, decimal_places=2)


class AttendanceReportDataSerializer(serializers.Serializer):
    """Serializer for attendance report data."""
    
    date = serializers.DateField()
    total_check_ins = serializers.IntegerField()
    unique_members = serializers.IntegerField()
    avg_duration = serializers.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        allow_null=True
    )


class ExpiringMembershipSerializer(serializers.Serializer):
    """Serializer for expiring membership data."""
    
    member_name = serializers.CharField()
    phone = serializers.CharField()
    expiry_date = serializers.DateField()
    days_remaining = serializers.IntegerField()
    subscription_type = serializers.CharField()


class UnpaidMemberSerializer(serializers.Serializer):
    """Serializer for unpaid member data."""
    
    member_name = serializers.CharField()
    phone = serializers.CharField()
    last_payment_date = serializers.DateField(allow_null=True)
    days_since_last_payment = serializers.IntegerField()
    total_debt = serializers.DecimalField(max_digits=10, decimal_places=2)


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics."""
    
    total_members = serializers.IntegerField()
    active_members = serializers.IntegerField()
    expiring_soon = serializers.IntegerField()
    today_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    today_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    today_attendance = serializers.IntegerField()
    monthly_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)


class DailyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyReport
        fields = '__all__'

class MonthlyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyReport
        fields = '__all__'
