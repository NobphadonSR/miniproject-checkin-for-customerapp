from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static

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
    path('api/locations/', views.get_locations, name='get_locations'),
    path('api/locations/add/', views.add_location, name='add_location'),
    path('api/locations/<int:location_id>/', views.get_location, name='get_location'),
    path('api/locations/<int:location_id>/delete/', views.delete_location, name='delete_location'),
    
    # เพิ่ม URLs สำหรับการจัดการคำขอลา
    path('api/leave-requests/', views.get_leave_requests, name='get_leave_requests'),
    path('api/leave-requests/<int:request_id>/approve/', views.approve_leave_request, name='approve_leave_request'),
    path('api/leave-requests/<int:request_id>/reject/', views.reject_leave_request, name='reject_leave_request'),
    
    # เพิ่ม URLs สำหรับการจัดการการเข้างาน
    path('api/attendance/today/', views.get_today_attendance, name='get_today_attendance'),
    path('api/attendance/stats/', views.get_attendance_stats, name='get_attendance_stats'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)