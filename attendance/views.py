from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.utils import timezone
from datetime import datetime, time, timedelta
from .models import User, Attendance, LocationSettings
from .forms import EmployeeRegistrationForm, LeaveRequestForm
from django.contrib import messages
from django.conf import settings
from math import radians, sin, cos, sqrt, atan2
from decimal import Decimal
import csv
from django.http import HttpResponse, JsonResponse

def index(request):
    return render(request, 'attendance/index.html')

def register(request):
    if request.method == 'POST':
        form = EmployeeRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'employee'
            user.save()
            login(request, user)
            return redirect('attendance:dashboard')
    else:
        form = EmployeeRegistrationForm()
    return render(request, 'attendance/register.html', {'form': form})

@login_required
def dashboard(request):
    if request.user.role == 'manager':
        return redirect('attendance:manager_dashboard')
    
    # เพิ่มการคำนวณสถิติ
    user_attendance = Attendance.objects.filter(employee=request.user).order_by('-date')
    
    # คำนวณเวลาทำงานวันนี้
    today_attendance = user_attendance.filter(date=timezone.localtime().date()).first()
    working_hours = 0
    if today_attendance and today_attendance.check_in:
        if today_attendance.check_out:
            time_diff = datetime.combine(today_attendance.date, today_attendance.check_out) - \
                       datetime.combine(today_attendance.date, today_attendance.check_in)
            working_hours = round(time_diff.total_seconds() / 3600, 1)
    
    # คำนวณอัตราการมาตรงเวลา
    total_days = user_attendance.count()
    on_time_days = user_attendance.filter(status='present').count()
    punctuality_rate = round((on_time_days / total_days * 100) if total_days > 0 else 0)
    
    # คำนวณวันลาคงเหลือ (สมมติว่ามีสิทธิ์ลา 10 วันต่อปี)
    leave_taken = user_attendance.filter(status='leave').count()
    leave_remaining = 10 - leave_taken
    
    context = {
        'attendances': user_attendance,
        'working_hours': working_hours,
        'leave_remaining': leave_remaining,
        'punctuality_rate': punctuality_rate
    }
    return render(request, 'attendance/employee_dashboard.html', context)

@login_required
def manager_dashboard(request):
    if request.user.role != 'manager':
        return redirect('attendance:dashboard')
    
    # รับค่าวันที่จาก request
    selected_date = request.GET.get('date')
    try:
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date() if selected_date else timezone.localtime().date()
    except ValueError:
        selected_date = timezone.localtime().date()
    
    # ข้อมูลพนักงานและการเข้างาน
    employees = User.objects.filter(role='employee')
    total_employees = employees.count()
    
    # การเข้างานตามวันที่เลือก
    attendances = Attendance.objects.filter(date=selected_date).order_by('-check_in')
    present_today = attendances.filter(status='present').count()
    late_today = attendances.filter(status='late').count()
    leave_today = attendances.filter(status='leave').count()
    absent_today = total_employees - (present_today + late_today + leave_today)
    
    # สถิติประจำเดือน
    current_month = selected_date.month
    current_year = selected_date.year
    month_attendances = Attendance.objects.filter(
        date__month=current_month,
        date__year=current_year
    )
    
    total_days = month_attendances.count()
    if total_days > 0:
        on_time_rate = round((month_attendances.filter(status='present').count() / total_days) * 100)
        late_rate = round((month_attendances.filter(status='late').count() / total_days) * 100)
        absent_rate = round((month_attendances.filter(status='absent').count() / total_days) * 100)
    else:
        on_time_rate = late_rate = absent_rate = 0
    
    # คำขอลาล่าสุด
    leave_requests = Attendance.objects.filter(
        status='leave'
    ).order_by('-date')[:5]
    
    context = {
        'selected_date': selected_date,
        'total_employees': total_employees,
        'present_today': present_today,
        'late_today': late_today,
        'leave_today': leave_today,
        'absent_today': absent_today,
        'on_time_rate': on_time_rate,
        'late_rate': late_rate,
        'absent_rate': absent_rate,
        'leave_requests': leave_requests,
        'attendances': attendances,
        'employees': employees,
    }
    
    return render(request, 'attendance/manager_dashboard.html', context)

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # รัศมีของโลกในเมตร
    
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance

@login_required
def check_in(request):
    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        if not latitude or not longitude:
            messages.error(request, 'กรุณาอนุญาตการเข้าถึงตำแหน่งที่ตั้ง')
            return redirect('dashboard')
            
        # ตรวจสอบว่าอยู่ในพื้นที่ที่กำหนดหรือไม่
        location_settings = LocationSettings.objects.first()
        if location_settings:
            distance = calculate_distance(
                latitude, 
                longitude,
                location_settings.latitude,
                location_settings.longitude
            )
            
            if distance > location_settings.radius:
                messages.error(request, 'คุณอยู่นอกพื้นที่ที่กำหนด ไม่สามารถเช็คอินได้')
                return redirect('dashboard')
        
        current_time = timezone.localtime().time()
        current_date = timezone.localtime().date()
        
        existing_attendance = Attendance.objects.filter(
            employee=request.user,
            date=current_date
        ).first()
        
        if existing_attendance:
            messages.error(request, 'คุณได้เช็คอินไปแล้วในวันนี้')
            return redirect('attendance:dashboard')
        
        status = 'present'
        if current_time > time(8, 0):
            status = 'late'
            
        Attendance.objects.create(
            employee=request.user,
            date=current_date,
            check_in=current_time,
            status=status,
            latitude=Decimal(latitude),
            longitude=Decimal(longitude)
        )
        messages.success(request, 'เช็คอินสำเร็จ')
        return redirect('dashboard')
    
    return render(request, 'attendance/check_in.html')

@login_required
def check_out(request):
    current_time = timezone.localtime().time()
    current_date = timezone.localtime().date()
    
    attendance = Attendance.objects.filter(
        employee=request.user,
        date=current_date
    ).first()
    
    if not attendance:
        messages.error(request, 'ไม่พบข้อมูลการเช็คอินวันนี้')
        return redirect('dashboard')
    
    if current_time < time(17, 0):
        messages.error(request, 'ยังไม่ถึงเวลาเลิกงาน')
        return redirect('dashboard')
    
    attendance.check_out = current_time
    attendance.save()
    messages.success(request, 'เช็คเอาท์สำเร็จ')
    return redirect('dashboard')

@login_required
def leave_request(request):
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = request.user
            leave.status = 'leave'
            leave.save()
            messages.success(request, 'ส่งคำขอลาสำเร็จ')
            return redirect('dashboard')
    else:
        form = LeaveRequestForm()
    return render(request, 'attendance/leave_request.html', {'form': form})

def privacy_policy(request):
    """
    แสดงหน้านโยบายความเป็นส่วนตัวและนโยบายคุกกี้
    """
    return render(request, 'attendance/privacy_policy.html')

def cookie_policy(request):
    """
    Redirect ไปยังส่วนคุกกี้ในหน้านโยบายความเป็นส่วนตัว
    """
    return redirect('privacy_policy')

@login_required
def export_attendance(request):
    if request.user.role != 'manager':
        return redirect('dashboard')
    
    selected_date = request.GET.get('date')
    period = request.GET.get('period', 'day')
    
    try:
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        selected_date = timezone.localtime().date()
    
    # กำหนดช่วงวันที่ตามประเภทที่เลือก
    if period == 'week':
        start_date = selected_date - timedelta(days=selected_date.weekday())
        end_date = start_date + timedelta(days=6)
        filename = f"attendance_week_{start_date}_to_{end_date}.csv"
    elif period == 'month':
        start_date = selected_date.replace(day=1)
        next_month = start_date.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day)
        filename = f"attendance_month_{start_date.strftime('%Y-%m')}.csv"
    elif period == 'year':
        start_date = selected_date.replace(month=1, day=1)
        end_date = selected_date.replace(month=12, day=31)
        filename = f"attendance_year_{start_date.year}.csv"
    else:  # day
        start_date = end_date = selected_date
        filename = f"attendance_{selected_date}.csv"
    
    # ดึงข้อมูลการเข้างานและเรียงลำดับตามวันที่
    attendances = Attendance.objects.filter(
        date__range=[start_date, end_date]
    ).order_by('date', 'employee__first_name')  # เรียงตามวันที่ก่อน แล้วค่อยเรียงตามชื่อ
    
    # สร้างไฟล์ CSV
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
    
    # เพิ่ม BOM สำหรับ Excel ภาษาไทย
    response.write(u'\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response)
    writer.writerow([
        'ลำดับ',
        'วันที่',
        'ชื่อ-นามสกุล',
        'อีเมล', 
        'แผนก',
        'เวลาเข้า',
        'เวลาออก',
        'สถานะ',
        'พิกัด'
    ])
    
    # เพิ่มลำดับและจัดรูปแบบวันที่เป็นไทย
    for index, attendance in enumerate(attendances, 1):
        # แปลงวันที่เป็นรูปแบบไทย
        thai_date = attendance.date.strftime('%d/%m/%Y')
        
        # จัดรูปแบบเวลา
        check_in_time = attendance.check_in.strftime('%H:%M:%S') if attendance.check_in else '-'
        check_out_time = attendance.check_out.strftime('%H:%M:%S') if attendance.check_out else '-'
        
        # จัดรูปแบบพิกัด
        location = f"{attendance.latitude},{attendance.longitude}" if attendance.latitude and attendance.longitude else "-"
        
        # แปลงสถานะเป็นภาษาไทย
        status_mapping = {
            'present': 'มาทำงาน',
            'late': 'มาสาย',
            'absent': 'ขาดงาน',
            'leave': 'ลา'
        }
        thai_status = status_mapping.get(attendance.status, attendance.get_status_display())
        
        writer.writerow([
            index,  # ลำดับ
            thai_date,  # วันที่แบบไทย
            f"{attendance.employee.first_name} {attendance.employee.last_name}",
            attendance.employee.email,
            attendance.employee.get_department_display(),
            check_in_time,
            check_out_time,
            thai_status,
            location
        ])
    
    return response

@login_required
def add_location(request):
    if request.method == 'POST':
        location_id = request.POST.get('location_id')
        if location_id:
            location = LocationSettings.objects.get(id=location_id)
        else:
            location = LocationSettings()
        
        location.name = request.POST.get('name')
        location.latitude = request.POST.get('latitude')
        location.longitude = request.POST.get('longitude')
        location.radius = request.POST.get('radius')
        location.save()
        
        return redirect('attendance:manager_dashboard')

@login_required
def get_location(request, location_id):
    locations = LocationSettings.objects.get(id=location_id)
    return JsonResponse([{
        'id': location.id,
        'name': location.name,
        'latitude': float(location.latitude),
        'longitude': float(location.longitude),
        'radius': location.radius
    } for location in locations], safe=False)

@login_required
def delete_location(request, location_id):
    if request.method == 'DELETE':
        LocationSettings.objects.get(id=location_id).delete()
        return JsonResponse({'status': 'success'})