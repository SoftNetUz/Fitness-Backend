from django.contrib import admin
from .models import FitnessClub, Member
from attendance.models import Attendance
from django.utils.html import format_html

@admin.register(FitnessClub)
class FitnessClubAdmin(admin.ModelAdmin):
    list_display = ("name", "daily", "monthly", "vip")
    list_filter = ("name",)
    search_fields = ("name", "daily",)
    readonly_fields = ("logo_preview",)

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="100" style="object-fit: contain;" />', obj.logo.url)
        return 'No Logo'
    
    logo_preview.short_description = "Logo Preview"


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('f_name', 'l_name', 'phone', 'gender', 'payment_amount', 'payment_type')
    list_filter = ('gender', 'payment_type',)
    search_fields = ('f_name', 'l_name', 'phone',)
