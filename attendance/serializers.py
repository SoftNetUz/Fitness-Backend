from rest_framework import serializers
from members.serializers import MemberSerializer
from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    member = MemberSerializer(read_only=True)
    class Meta:
        model = Attendance
        exclude = ['state']
        depth = 1
