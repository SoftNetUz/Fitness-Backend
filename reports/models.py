from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, Count, Q
from utils.models import BaseModel
from members.models import Member
from finance.models import Payment, Costs
from attendance.models import Attendance


class ActiveManager(models.Manager):
    """Only return rows where state=True by default."""
    def get_queryset(self):
        return super().get_queryset().filter(state=True)


class MembershipSale(BaseModel):
    """Track membership sales for reporting and analytics."""
    
    PAYMENT_TYPES = (
        ('Oylik', 'Oylik'),
        ('Premium', 'Premium'),
        ('Kunlik', 'Kunlik'),
    )
    
    member = models.ForeignKey(
        Member, 
        on_delete=models.CASCADE, 
        related_name="membership_sales",
        verbose_name="Member"
    )
    sale_date = models.DateField(
        default=timezone.now,
        verbose_name="Sale Date"
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Sale Amount"
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES,
        default='Oylik',
        verbose_name="Payment Type"
    )
    notes = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Notes"
    )

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-sale_date']
        verbose_name = "Membership Sale"
        verbose_name_plural = "Membership Sales"
        indexes = [
            models.Index(fields=['sale_date']),
            models.Index(fields=['member', 'sale_date']),
        ]

    def clean(self):
        if self.amount <= 0:
            raise ValidationError("Sale amount must be greater than zero.")
        if self.sale_date > timezone.now().date():
            raise ValidationError("Sale date cannot be in the future.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member} - {self.amount} ({self.sale_date})"

    @classmethod
    def get_total_sales(cls, start_date=None, end_date=None):
        """Get total sales for a date range."""
        queryset = cls.objects.all()
        if start_date:
            queryset = queryset.filter(sale_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(sale_date__lte=end_date)
        return queryset.aggregate(total=Sum('amount'))['total'] or 0


class AttendanceReport(BaseModel):
    """Track attendance reports for analytics."""
    
    member = models.ForeignKey(
        Member, 
        on_delete=models.CASCADE, 
        related_name="attendance_reports",
        verbose_name="Member"
    )
    date = models.DateField(
        default=timezone.now,
        verbose_name="Report Date"
    )
    branch = models.CharField(
        max_length=100,
        verbose_name="Branch"
    )
    check_in_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Check-in Time"
    )
    check_out_time = models.TimeField(
        null=True, 
        blank=True,
        verbose_name="Check-out Time"
    )
    duration_minutes = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name="Duration (minutes)"
    )

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-date', '-check_in_time']
        verbose_name = "Attendance Report"
        verbose_name_plural = "Attendance Reports"
        unique_together = ['member', 'date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['member', 'date']),
            models.Index(fields=['branch', 'date']),
        ]

    def clean(self):
        if self.check_out_time and self.check_in_time:
            if self.check_in_time >= self.check_out_time:
                raise ValidationError("Check-out time must be after check-in time.")
        if self.date > timezone.now().date():
            raise ValidationError("Report date cannot be in the future.")

    def save(self, *args, **kwargs):
        self.clean()
        if self.check_out_time and self.check_in_time:
            # Calculate duration in minutes
            from datetime import datetime
            check_in = datetime.combine(self.date, self.check_in_time)
            check_out = datetime.combine(self.date, self.check_out_time)
            self.duration_minutes = int((check_out - check_in).total_seconds() / 60)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member} - {self.date} ({self.branch})"

    @classmethod
    def get_attendance_stats(cls, start_date=None, end_date=None, branch=None):
        """Get attendance statistics for a date range."""
        queryset = cls.objects.all()
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        if branch:
            queryset = queryset.filter(branch=branch)
        
        return {
            'total_visits': queryset.count(),
            'unique_members': queryset.values('member').distinct().count(),
            'avg_duration': queryset.aggregate(
                avg_duration=models.Avg('duration_minutes')
            )['avg_duration'] or 0,
        }


class IncomeExpenseReport(BaseModel):
    """Track daily income vs expenses for financial reporting."""
    
    date = models.DateField(
        default=timezone.now,
        verbose_name="Report Date"
    )
    income = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Total Income"
    )
    expenses = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name="Total Expenses"
    )
    notes = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Notes"
    )

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-date']
        verbose_name = "Income Expense Report"
        verbose_name_plural = "Income Expense Reports"
        unique_together = ['date']
        indexes = [
            models.Index(fields=['date']),
        ]

    def clean(self):
        if self.income < 0:
            raise ValidationError("Income cannot be negative.")
        if self.expenses < 0:
            raise ValidationError("Expenses cannot be negative.")
        if self.date > timezone.now().date():
            raise ValidationError("Report date cannot be in the future.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Income: {self.income}, Expenses: {self.expenses} - {self.date}"

    @property
    def net_income(self):
        """Calculate net income (income - expenses)."""
        return self.income - self.expenses

    @property
    def profit_margin(self):
        """Calculate profit margin percentage as a Decimal."""
        from decimal import Decimal, ROUND_HALF_UP
        if self.income == 0:
            return Decimal('0.00')
        margin = (self.net_income / self.income) * Decimal('100')
        # Round to 2 decimal places for consistency
        return margin.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @classmethod
    def generate_daily_report(cls, date=None):
        """Generate a daily income/expense report from actual data."""
        if date is None:
            date = timezone.now().date()
        
        # Calculate income from payments
        income = Payment.objects.filter(
            date=date, 
            state=True
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate expenses from costs
        expenses = Costs.objects.filter(
            date=date, 
            state=True
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Create or update report
        report, created = cls.objects.get_or_create(
            date=date,
            defaults={
                'income': income,
                'expenses': expenses,
            }
        )
        
        if not created:
            report.income = income
            report.expenses = expenses
            report.save()
        
        return report


class Subscription(BaseModel):
    """Track member subscriptions and their validity periods."""
    
    member = models.ForeignKey(
        Member, 
        on_delete=models.CASCADE, 
        related_name="subscriptions",
        verbose_name="Member"
    )
    start_date = models.DateField(
        verbose_name="Start Date"
    )
    end_date = models.DateField(
        verbose_name="End Date"
    )
    subscription_type = models.CharField(
        max_length=20,
        choices=MembershipSale.PAYMENT_TYPES,
        default='Oylik',
        verbose_name="Subscription Type"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active"
    )
    notes = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Notes"
    )

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-end_date']
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['member', 'is_active']),
        ]

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date.")
        if self.start_date > timezone.now().date():
            raise ValidationError("Start date cannot be in the future.")

    def save(self, *args, **kwargs):
        self.clean()
        # Update is_active based on dates
        today = timezone.now().date()
        self.is_active = self.start_date <= today <= self.end_date
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member} - {self.start_date} to {self.end_date}"

    @property
    def is_expired(self):
        """Check if subscription is expired."""
        return timezone.now().date() > self.end_date

    @property
    def days_remaining(self):
        """Calculate days remaining in subscription."""
        today = timezone.now().date()
        if today > self.end_date:
            return 0
        return (self.end_date - today).days

    @classmethod
    def get_expiring_soon(cls, days=7):
        """Get subscriptions expiring within specified days."""
        today = timezone.now().date()
        end_date = today + timezone.timedelta(days=days)
        return cls.objects.filter(
            end_date__gte=today,
            end_date__lte=end_date,
            is_active=True
        )

class DailyReport(models.Model):
    date = models.DateField(unique=True, db_index=True)
    income = models.FloatField(default=0)
    expense = models.FloatField(default=0)
    new_members = models.PositiveIntegerField(default=0)
    renewals = models.PositiveIntegerField(default=0)
    total_members = models.PositiveIntegerField(default=0)
    check_ins = models.PositiveIntegerField(default=0)
    expiring_soon = models.PositiveIntegerField(default=0)
    active_members = models.PositiveIntegerField(default=0)
    male_members = models.PositiveIntegerField(default=0)
    female_members = models.PositiveIntegerField(default=0)
    cash_income = models.FloatField(default=0)
    card_income = models.FloatField(default=0)

    class Meta:
        ordering = ['-date']
        verbose_name = "Daily Report"
        verbose_name_plural = "Daily Reports"

    def __str__(self):
        return f"Daily Report: {self.date}"

class MonthlyReport(models.Model):
    month = models.DateField(unique=True, db_index=True)  # Use first day of month
    income = models.FloatField(default=0)
    expense = models.FloatField(default=0)
    new_members = models.PositiveIntegerField(default=0)
    renewals = models.PositiveIntegerField(default=0)
    total_members = models.PositiveIntegerField(default=0)
    check_ins = models.PositiveIntegerField(default=0)
    expiring_soon = models.PositiveIntegerField(default=0)
    active_members = models.PositiveIntegerField(default=0)
    male_members = models.PositiveIntegerField(default=0)
    female_members = models.PositiveIntegerField(default=0)
    cash_income = models.FloatField(default=0)
    card_income = models.FloatField(default=0)

    class Meta:
        ordering = ['-month']
        verbose_name = "Monthly Report"
        verbose_name_plural = "Monthly Reports"

    def __str__(self):
        return f"Monthly Report: {self.month.strftime('%Y-%m')}"
