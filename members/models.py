from django.db import models
from django.core.validators import RegexValidator
from utils.models import BaseModel

numeric_pin = RegexValidator(r'^\d{4}$', 'PIN kod faqat 4 ta raqamdan iborat bo‘lishi kerak.')

class FitnessClub(BaseModel):
    name    = models.CharField(max_length=255, verbose_name="Nomi")
    logo    = models.ImageField(upload_to='fitness_club_logos/', null=True, blank=True, verbose_name="Logo")
    daily   = models.FloatField(verbose_name="Kunlik narx")
    monthly = models.FloatField(verbose_name="Oylik narx")
    vip     = models.BooleanField(default=False, verbose_name="VIP")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Fitness klublar"


class Member(BaseModel):
    class Gender(models.TextChoices):
        MALE   = 'E', 'Erkak'
        FEMALE = 'A', 'Ayol'

    class PaymentType(models.TextChoices):
        DAILY   = 'Kunlik', 'Kunlik'
        MONTHLY = 'Oylik',   'Oylik'
        PREMIUM = 'Premium', 'Premium'

    f_name         = models.CharField(max_length=255, verbose_name="Ism")
    l_name         = models.CharField(max_length=255, verbose_name="Familiya")
    phone          = models.CharField(max_length=20, verbose_name="Telefon")
    gender         = models.CharField(max_length=1, choices=Gender.choices, verbose_name="Jins")
    pin_code       = models.CharField(max_length=4, unique=True, validators=[numeric_pin], verbose_name="PIN kod")
    payment_amount = models.FloatField(verbose_name="To‘lov miqdori")
    payment_type   = models.CharField(max_length=8, choices=PaymentType.choices, default=PaymentType.MONTHLY, verbose_name="To‘lov turi")

    def __str__(self):
        return f"{self.f_name} {self.l_name}"

    class Meta:
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['pin_code']),
        ]
        verbose_name_plural = "Aʼzolar"


