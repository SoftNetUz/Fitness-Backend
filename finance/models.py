from django.db import models
from django.utils import timezone
from utils.models import BaseModel
from members.models import Member


class ActiveManager(models.Manager):
    """Only return rows where state=True by default."""
    def get_queryset(self):
        return super().get_queryset().filter(state=True)


class Costs(BaseModel):
    cost_name = models.CharField(max_length=100, verbose_name="Chiqim nomi")
    quantity = models.FloatField(default=0, verbose_name="Miqdor")
    desc = models.CharField(max_length=200, blank=True, null=True, verbose_name="Izoh")
    date = models.DateTimeField(default=timezone.now, verbose_name="Sana")

    objects = ActiveManager()       # state=True only
    all_objects = models.Manager() # if you ever need soft-deleted rows

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.cost_name} ({self.date.strftime('%d-%m-%Y')})"


class Payment(BaseModel):
    PAYMENT_TYPE = (
        ('Oylik', "Oylik"),
        ('Premium', "Premium"),
        ('Kunlik', "Kunlik"),
    )

    PAYMENT_METHOD = [
        ("cash", "Naqd"),
        ("card", "Karta"),
        ("transfer", "O'tkazma"),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="payments")
    # Switch to DecimalField for exact money amounts:
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="To'lov Miqdori")
    date = models.DateTimeField(default=timezone.now, verbose_name="To'lov sanasi")
    payment_type = models.CharField(
        max_length=50,
        choices=PAYMENT_TYPE,
        default="Oylik",  # was "monthly", which did not match any choice
        verbose_name="To'lov turi"
    )
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD,
        default="cash",
        verbose_name="To'lov usuli"
    )
    desc = models.CharField(max_length=200, blank=True, null=True, verbose_name="Izoh")

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Payment of {self.amount} – {self.member.l_name} {self.member.f_name}"


class Debt(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="debts")
    # Switch to DecimalField for exact money amounts:
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Qarz miqdori")
    due_date = models.DateTimeField(default=timezone.now, verbose_name="To'lov sanasi")
    desc = models.CharField(max_length=200, blank=True, null=True, verbose_name="Izoh")

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-due_date']

    def __str__(self):
        return f"Debt of {self.amount} – {self.member.l_name} {self.member.f_name}"
