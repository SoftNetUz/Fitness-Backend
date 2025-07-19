from rest_framework import serializers
from members.serializers import MemberSerializer
from .models import Attendance, Member


class AttendanceSerializer(serializers.ModelSerializer):
    member = MemberSerializer(read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(
        queryset=Member.objects.all(), write_only=True, required=True
    )

    class Meta:
        model = Attendance
        exclude = ['state']
        depth = 1

    def create(self, validated_data):
        member = validated_data.pop('member_id')
        attendance = Attendance.objects.create(member=member, **validated_data)
        return attendance

    def update(self, instance, validated_data):
        if 'member_id' in validated_data:
            instance.member = validated_data.pop('member_id')
        return super().update(instance, validated_data)
