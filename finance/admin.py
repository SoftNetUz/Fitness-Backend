from django.contrib import admin
from .models import Payment, Debt, Costs


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "member", "amount", "date", "payment_type", "payment_method", "desc")
    list_filter = ("payment_type", "payment_method", "date", "state")
    search_fields = ("member__f_name", "member__l_name")
    ordering = ("-date",)


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ("id", "member", "amount", "due_date", "desc")
    list_filter = ("due_date", "state")
    search_fields = ("member__f_name", "member__l_name")
    ordering = ("-due_date",)


@admin.register(Costs)
class CostsAdmin(admin.ModelAdmin):
    list_display = ("id", "cost_name", "quantity", "date", "desc")
    list_filter = ("date", "state")
    search_fields = ("cost_name",)
    ordering = ("-date",)
