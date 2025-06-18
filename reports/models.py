from django.db import models
from utils.models import BaseModel
from members.models import Member
from django.utils.timezone import now


class ActiveManager(models.Manager):
    """Only return rows where state=True by default."""
    def get_queryset(self):
        return super().get_queryset().filter(state=True)


class MembershipSale(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="membership_sales")
    sale_date = models.DateField(default=now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    objects = ActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"A'zolik narxi – {self.member} – {self.amount}"


class AttendanceReport(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="attendance_reports")
    date = models.DateField(default=now)
    branch = models.CharField(max_length=100)

    objects = ActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"Davomat – {self.member} – {self.date}"


class IncomeExpenseReport(BaseModel):
    date = models.DateField(default=now)
    income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    objects = ActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"Income vs Expenses – {self.date}"


class Subscription(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="subscriptions")
    start_date = models.DateField()
    end_date = models.DateField()

    objects = ActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"Subscription – {self.member} – {self.end_date}"
