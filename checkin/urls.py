from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from attendance.views import index

urlpatterns = [
    path('admin/', admin.site.urls),
    path('attendance/', include('attendance.urls')),
    path('', index, name='index'),
]
