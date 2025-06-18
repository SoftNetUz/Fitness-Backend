# reports/admin.py

from django.contrib import admin
from .models import MembershipSale, AttendanceReport, IncomeExpenseReport, Subscription


@admin.register(MembershipSale)
class MembershipSaleAdmin(admin.ModelAdmin):
    list_display = ('member', 'sale_date', 'amount')
    search_fields = ('member__f_name', 'member__l_name', 'sale_date')
    list_filter = ('sale_date', 'state')
    ordering = ('-sale_date',)


@admin.register(AttendanceReport)
class AttendanceReportAdmin(admin.ModelAdmin):
    list_display = ('member', 'date', 'branch')
    search_fields = ('member__f_name', 'member__l_name', 'branch')
    list_filter = ('date', 'branch', 'state')
    ordering = ('-date',)


@admin.register(IncomeExpenseReport)
class IncomeExpenseReportAdmin(admin.ModelAdmin):
    list_display = ('date', 'income', 'expenses')
    search_fields = ('date',)
    list_filter = ('date', 'state')
    ordering = ('-date',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('member', 'start_date', 'end_date')
    search_fields = ('member__f_name', 'member__l_name', 'start_date', 'end_date')
    list_filter = ('start_date', 'end_date', 'state')
    ordering = ('-end_date',)
