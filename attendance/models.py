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
    attended_at = models.DateField(auto_now_add=True, db_index=True)
    # Optionally, store the code used for audit
    code_used = models.CharField(max_length=4, blank=True, null=True)

    objects = AttendanceManager()
    all_objects = models.Manager()

    class Meta:
        constraints = [
            # Ensure one record per member per calendar day (using TruncDate)
            UniqueConstraint(
                fields=['member'],
                name='unique_attendance_member_per_day',
                condition=Q(state=True),
                violation_error_message="A member can only check in once per day.",
                # Use TruncDate for attended_at
                include=['attended_at'],
                # The following is not standard, so we use a workaround below
            )
        ]
        ordering = ['-attended_at']

    def save(self, *args, **kwargs):
        # Only check uniqueness if member is set
        if self.state and self.member_id:
            qs = Attendance.all_objects.filter(
                member=self.member,
                attended_at__date=self.attended_at.date() if self.attended_at else None,
                state=True
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                from django.core.exceptions import ValidationError
                raise ValidationError("A member can only check in once per day.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member} - {self.attended_at}"