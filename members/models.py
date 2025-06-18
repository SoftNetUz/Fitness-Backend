from utils.models import BaseModel
from django.db import models

PAYMENT_TYPE = (
        ('Oylik', "Oylik"),
        ('Premium', "Premium"),
        ('Kunlik', "Kunlik"),
    )

# Fitness club configuration section
class FitnessClub(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Nomi")
    logo = models.ImageField(upload_to='fitness_club_logos/', null=True, blank=True, verbose_name="Logo")
    daily = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Kunlik")
    monthly = models.DecimalField(max_digits=7, decimal_places=2, verbose_name="Oylik")
    vip = models.BooleanField(default=False, verbose_name="VIP")

    def __str__(self):
        return self.name
    
    # Singleton pattern
    @classmethod
    def get_instance(cls):
        instance, created = cls.objects.get_or_create(id=1)
        return instance
    
    def save(self, *args, **kwargs):
        if self.__class__.objects.exists() and not self.pk:
            return
        super(FitnessClub, self).save(*args, **kwargs)


# Memebers section
class Member(BaseModel):
    class Gender(models.TextChoices):
        MALE = 'E', 'Erkak'
        FEMALE = 'A', 'Ayol'

    f_name = models.CharField(max_length=255, verbose_name="Ism")
    l_name = models.CharField(max_length=255, verbose_name="Familiya")
    phone = models.CharField(max_length=20, verbose_name="Telefon", help_text="Telefon raqamingizni kiriting (masalan: +998...)")
    gender = models.CharField(max_length=1, choices=Gender.choices, verbose_name="Jins")
    pin_code = models.CharField(max_length=4, unique=True, verbose_name="PIN kod", help_text="PIN kodni kiriting (4 raqamli)")
    payment_amount = models.DecimalField(max_digits=50, decimal_places=2, verbose_name="Tolov miqdori")
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPE, default="Oylik")
    branch = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        return f"{self.f_name} {self.l_name}"
    
    
class AttendedTime(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='attended_times')
    attended_at = models.DateField()

    class Meta:
        unique_together = ('member', 'attended_at')

    def __str__(self):
        return f"{self.member} - {self.attended_at}"

