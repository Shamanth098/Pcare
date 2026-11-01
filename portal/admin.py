from django.contrib import admin
from .models import Clinic


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ('name', 'area', 'category', 'open_now', 'is_verified')
    search_fields = ('name', 'area')
    list_filter = ('category', 'open_now', 'is_verified')
