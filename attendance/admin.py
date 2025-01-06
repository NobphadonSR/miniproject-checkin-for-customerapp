from django.contrib import admin
from .models import Attendance, User, LocationSettings
# Register your models here.
admin.site.register(Attendance)
admin.site.register(User)
@admin.register(LocationSettings)
class LocationSettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude', 'radius')
