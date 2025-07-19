from rest_framework import serializers
from .models import FitnessClub, Member
from attendance.models import Attendance
from utils.payments import get_expiry_date, is_expired, is_expiring_soon
from utils.serializers import BaseModelSerializer

# Fitness Culb Serializer
class FitnessClubSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta: 
        model = FitnessClub
        fields = '__all__'

    def get_logo_url(self, obj):
        request = self.context.get('request')
        if obj.logo and hasattr(obj.logo, 'url'):
            logo_url = obj.logo.url
            if request is not None:
                return request.build_absolute_uri(logo_url)
            return logo_url
        return None


# Member serializer
class MemberSerializer(BaseModelSerializer):
    gender_display  = serializers.CharField(source='get_gender_display', read_only=True)
    payment_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    expiry_date     = serializers.SerializerMethodField()
    is_expiring     = serializers.SerializerMethodField()
    is_expired      = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Member
        fields = '__all__'
        read_only_fields = [
            'created_at', 'updated_at', 'created_by', 'updated_by',
            'gender_display', 'payment_display',
            'expiry_date', 'is_expiring', 'is_expired'
        ]

    def get_expiry_date(self, obj):
        return get_expiry_date(obj)

    def get_is_expiring(self, obj):
        return is_expiring_soon(obj)

    def get_is_expired(self, obj):
        return is_expired(obj)
    
    # def get_latest_payment_date(self, obj):
    #     latest_payment = obj.payments.order_by('-date').first()
    #     return latest_payment.date if latest_payment else None

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'


class MemberStatsSerializer(serializers.Serializer):
    total_members = serializers.IntegerField()
    monthly_members = serializers.IntegerField()
    vip_members = serializers.IntegerField()
    daily_members = serializers.IntegerField()
    expiring_members = serializers.IntegerField()
    expired_members = serializers.IntegerField()