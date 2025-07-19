# reports/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from .models import MembershipSale, AttendanceReport, IncomeExpenseReport, Subscription, DailyReport, MonthlyReport


@admin.register(MembershipSale)
class MembershipSaleAdmin(admin.ModelAdmin):
    list_display = ('member', 'sale_date', 'amount', 'payment_type', 'formatted_amount')
    list_filter = ('sale_date', 'payment_type', 'state', 'created_at')
    search_fields = ('member__f_name', 'member__l_name', 'member__phone', 'notes')
    ordering = ('-sale_date',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'sale_date'
    
    fieldsets = (
        ('Member Information', {
            'fields': ('member', 'payment_type')
        }),
        ('Sale Details', {
            'fields': ('sale_date', 'amount', 'notes')
        }),
        ('System Information', {
            'fields': ('state', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_inactive', 'generate_sales_report']
    
    def formatted_amount(self, obj):
        return format_html('<span style="color: green; font-weight: bold;">${}</span>', obj.amount)
    formatted_amount.short_description = 'Amount'
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(state=False)
        self.message_user(request, f'{updated} sales marked as inactive.')
    mark_as_inactive.short_description = "Mark selected sales as inactive"
    
    def generate_sales_report(self, request, queryset):
        total_amount = queryset.aggregate(total=Sum('amount'))['total'] or 0
        total_count = queryset.count()
        self.message_user(
            request, 
            f'Sales Report: {total_count} sales totaling ${total_amount}'
        )
    generate_sales_report.short_description = "Generate sales report"


@admin.register(AttendanceReport)
class AttendanceReportAdmin(admin.ModelAdmin):
    list_display = ('member', 'date', 'branch', 'check_in_time', 'duration_display')
    list_filter = ('date', 'branch', 'state', 'created_at')
    search_fields = ('member__f_name', 'member__l_name', 'branch')
    ordering = ('-date', '-check_in_time')
    readonly_fields = ('created_at', 'updated_at', 'duration_minutes')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Member Information', {
            'fields': ('member', 'branch')
        }),
        ('Attendance Details', {
            'fields': ('date', 'check_in_time', 'check_out_time', 'duration_minutes')
        }),
        ('System Information', {
            'fields': ('state', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_inactive', 'generate_attendance_report']
    
    def duration_display(self, obj):
        if obj.duration_minutes:
            hours = obj.duration_minutes // 60
            minutes = obj.duration_minutes % 60
            return f"{hours}h {minutes}m"
        return "N/A"
    duration_display.short_description = 'Duration'
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(state=False)
        self.message_user(request, f'{updated} attendance records marked as inactive.')
    mark_as_inactive.short_description = "Mark selected records as inactive"
    
    def generate_attendance_report(self, request, queryset):
        total_visits = queryset.count()
        unique_members = queryset.values('member').distinct().count()
        avg_duration = queryset.aggregate(avg=Sum('duration_minutes') / Count('id'))['avg'] or 0
        self.message_user(
            request, 
            f'Attendance Report: {total_visits} visits by {unique_members} members. Avg duration: {avg_duration:.1f} minutes'
        )
    generate_attendance_report.short_description = "Generate attendance report"


@admin.register(IncomeExpenseReport)
class IncomeExpenseReportAdmin(admin.ModelAdmin):
    list_display = ('date', 'income', 'expenses', 'net_income_display', 'profit_margin_display')
    list_filter = ('date', 'state', 'created_at')
    search_fields = ('notes',)
    ordering = ('-date',)
    readonly_fields = ('created_at', 'updated_at', 'net_income', 'profit_margin')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Financial Information', {
            'fields': ('date', 'income', 'expenses', 'net_income', 'profit_margin')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('System Information', {
            'fields': ('state', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_inactive', 'generate_financial_report', 'auto_generate_today']
    
    def net_income_display(self, obj):
        color = 'green' if obj.net_income >= 0 else 'red'
        return format_html('<span style="color: {}; font-weight: bold;">${}</span>', color, obj.net_income)
    net_income_display.short_description = 'Net Income'
    
    def profit_margin_display(self, obj):
        color = 'green' if obj.profit_margin >= 0 else 'red'
        return format_html('<span style="color: {}; font-weight: bold;">{:.1f}%</span>', color, obj.profit_margin)
    profit_margin_display.short_description = 'Profit Margin'
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(state=False)
        self.message_user(request, f'{updated} reports marked as inactive.')
    mark_as_inactive.short_description = "Mark selected reports as inactive"
    
    def generate_financial_report(self, request, queryset):
        total_income = queryset.aggregate(total=Sum('income'))['total'] or 0
        total_expenses = queryset.aggregate(total=Sum('expenses'))['total'] or 0
        net_income = total_income - total_expenses
        profit_margin = (net_income / total_income * 100) if total_income > 0 else 0
        self.message_user(
            request, 
            f'Financial Report: Income: ${total_income}, Expenses: ${total_expenses}, Net: ${net_income}, Margin: {profit_margin:.1f}%'
        )
    generate_financial_report.short_description = "Generate financial report"
    
    def auto_generate_today(self, request, queryset):
        from .models import IncomeExpenseReport
        report = IncomeExpenseReport.generate_daily_report()
        self.message_user(request, f'Generated report for {report.date}: Income: ${report.income}, Expenses: ${report.expenses}')
    auto_generate_today.short_description = "Auto-generate today's report"


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('member', 'start_date', 'end_date', 'subscription_type', 'status_display', 'days_remaining_display')
    list_filter = ('start_date', 'end_date', 'subscription_type', 'is_active', 'state')
    search_fields = ('member__f_name', 'member__l_name', 'member__phone', 'notes')
    ordering = ('-end_date',)
    readonly_fields = ('created_at', 'updated_at', 'is_active', 'is_expired', 'days_remaining')
    date_hierarchy = 'end_date'
    
    fieldsets = (
        ('Member Information', {
            'fields': ('member', 'subscription_type')
        }),
        ('Subscription Period', {
            'fields': ('start_date', 'end_date')
        }),
        ('Status Information', {
            'fields': ('is_active', 'is_expired', 'days_remaining')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('System Information', {
            'fields': ('state', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_inactive', 'generate_subscription_report', 'extend_subscriptions']
    
    def status_display(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.is_active:
            return format_html('<span style="color: green;">Active</span>')
        else:
            return format_html('<span style="color: orange;">Pending</span>')
    status_display.short_description = 'Status'
    
    def days_remaining_display(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        else:
            return format_html('<span style="color: green;">{} days</span>', obj.days_remaining)
    days_remaining_display.short_description = 'Days Remaining'
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(state=False)
        self.message_user(request, f'{updated} subscriptions marked as inactive.')
    mark_as_inactive.short_description = "Mark selected subscriptions as inactive"
    
    def generate_subscription_report(self, request, queryset):
        active_count = queryset.filter(is_active=True).count()
        expired_count = queryset.filter(is_expired=True).count()
        expiring_soon = queryset.filter(
            end_date__gte=timezone.now().date(),
            end_date__lte=timezone.now().date() + timedelta(days=7)
        ).count()
        self.message_user(
            request, 
            f'Subscription Report: {active_count} active, {expired_count} expired, {expiring_soon} expiring soon'
        )
    generate_subscription_report.short_description = "Generate subscription report"
    
    def extend_subscriptions(self, request, queryset):
        # Extend subscriptions by 30 days
        for subscription in queryset:
            subscription.end_date += timedelta(days=30)
            subscription.save()
        self.message_user(request, f'Extended {queryset.count()} subscriptions by 30 days.')
    extend_subscriptions.short_description = "Extend subscriptions by 30 days"


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ('date', 'income', 'expense', 'new_members', 'renewals', 'total_members', 'check_ins', 'expiring_soon', 'active_members')
    search_fields = ('date',)
    list_filter = ('date',)
    ordering = ('-date',)

@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = ('month', 'income', 'expense', 'new_members', 'renewals', 'total_members', 'check_ins', 'expiring_soon', 'active_members')
    search_fields = ('month',)
    list_filter = ('month',)
    ordering = ('-month',)
