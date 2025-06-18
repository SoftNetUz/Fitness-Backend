from django.contrib import admin
from .models import Attendance

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('member', 'attended_at', 'code_used')
    list_filter = ('attended_at', 'member')
    search_fields = ('member__f_name', 'member__l_name', 'member__pin_code', 'code_used')
    ordering = ('-attended_at',)
