from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'attendance'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='attendance/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='attendance:login'), name='logout'),
    path('check-in/', views.check_in, name='check_in'),  # ลบ path ที่ซ้ำกัน
    path('check-out/', views.check_out, name='check_out'),
    path('leave-request/', views.leave_request, name='leave_request'),
    path('export-attendance/', views.export_attendance, name='export_attendance'),  # ย้ายมาก่อน manager/dashboard
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('cookie-policy/', views.cookie_policy, name='cookie_policy'),
    path('add-location/', views.add_location, name='add_location'),
    path('api/locations/', views.get_locations, name='get_locations'),
    path('api/locations/<int:location_id>/', views.get_location, name='get_location'),
    path('api/locations/add/', views.add_location, name='add_location'),
    path('api/locations/<int:location_id>/delete/', views.delete_location, name='delete_location'),
]