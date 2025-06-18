from rest_framework import serializers
from .models import FitnessClub, Member, PAYMENT_TYPE, AttendedTime
from utils.payments import get_expiry_date, is_expired, is_expiring_soon

# Fitness Culb Serializer
class FitnessClubSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta: 
        model = FitnessClub
        fields = '__all__'


# Member serializer
class MemberSerializer(serializers.ModelSerializer):
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    payment_display = serializers.SerializerMethodField(method_name='get_payment_type_display')
    expiry_date = serializers.SerializerMethodField()
    is_expiring = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = '__all__'
        read_only_fields = ['gender_display', 'payment_display']

    def get_payment_type_display(self, obj):
        return dict(PAYMENT_TYPE).get(obj.payment_type, obj.payment_type)
    
    # def get_latest_payment_date(self, obj):
    #     latest_payment = obj.payments.order_by('-date').first()
    #     return latest_payment.date if latest_payment else None

    def get_expiry_date(self, obj):
        return get_expiry_date(obj)

    def get_is_expiring(self, obj):
        return is_expiring_soon(obj)

    def get_is_expired(self, obj):
        return is_expired(obj)


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendedTime
        fields = '__all__'


class MemberStatsSerializer(serializers.Serializer):
    total_members = serializers.IntegerField()
    monthly_members = serializers.IntegerField()
    vip_members = serializers.IntegerField()
    daily_members = serializers.IntegerField()
    expiring_members = serializers.IntegerField()
    expired_members = serializers.IntegerField()