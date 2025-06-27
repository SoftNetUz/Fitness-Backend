from django.db import models
from django.db.models import Q, UniqueConstraint, F
from django.db.models.functions import TruncDate
from utils.models import BaseModel
from members.models import Member


class AttendanceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(state=True)


class Attendance(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='attendances')
    attended_at = models.DateTimeField(auto_now_add=True,)
    # Optionally, store the code used for audit
    code_used = models.CharField(max_length=4, blank=True, null=True)

    # 1) “active only” manager
    objects = AttendanceManager()
    # 2) an explicit manager for everything
    all_objects = models.Manager()

    class Meta:
        constraints = [
            # Ensure one record per member per calendar day
            UniqueConstraint(
                fields=['member', 'attended_at'],
                name='unique_attendance_member_per_day',
                condition=Q(state=True),
            )
        ]
        ordering = ['-attended_at']

    def __str__(self):
        return f"{self.member} - {self.attended_at}"
