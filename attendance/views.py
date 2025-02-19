from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.utils import timezone
from datetime import datetime, time, timedelta
from .models import User, Attendance, LocationSettings, LeaveRequest
from .forms import EmployeeRegistrationForm, LeaveRequestForm
from django.contrib import messages
from django.conf import settings
from math import radians, sin, cos, sqrt, atan2
from decimal import Decimal
import csv
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_protect
import base64
from django.core.files.base import ContentFile
from django.views.decorators.http import require_http_methods
import json

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
        'punctuality_rate': punctuality_rate,
        'today_attendance': today_attendance
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
    
    # กำหนดเวลาเริ่มงาน
    start_time = time(9, 0)  # 9:00 น.
    
    # ข้อมูลพนักงานและการเข้างาน
    employees = User.objects.filter(role='employee')
    total_employees = employees.count()
    
    # การเข้างานตามวันที่เลือก
    attendances = Attendance.objects.filter(date=selected_date).order_by('-check_in')
    
    # นับจำนวนคนมาทำงาน สาย และลา
    present_today = 0
    late_today = 0
    
    for attendance in attendances:
        if attendance.check_in:
            check_in_time = attendance.check_in
            if isinstance(check_in_time, datetime):
                check_in_time = check_in_time.time()
            if check_in_time <= start_time:
                present_today += 1
            else:
                late_today += 1
    
    # แก้ไขการนับจำนวนคนลาวันนี้
    leave_today = LeaveRequest.objects.filter(
        date=selected_date,
        status='approved'
    ).count()
    
    absent_today = total_employees - (present_today + late_today + leave_today)
    
    # คำนวณสถิติประจำเดือน
    current_month = selected_date.month
    current_year = selected_date.year
    first_day = selected_date.replace(day=1)
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    # ดึงข้อมูลการเข้างานทั้งเดือน
    month_attendances = Attendance.objects.filter(
        date__range=[first_day, last_day]
    ).select_related('employee')
    
    # จำนวนวันทำงานทั้งหมดในเดือน (ไม่รวมเสาร์-อาทิตย์)
    total_workdays = sum(1 for day in (first_day + timedelta(n) for n in range((last_day - first_day).days + 1))
                        if day.weekday() < 5)  # 0-4 คือ จันทร์-ศุกร์
    
    # จำนวนพนักงานทั้งหมด
    total_emp = User.objects.filter(role='employee').count()
    
    # จำนวนการเข้างานที่เป็นไปได้ทั้งหมด
    total_possible_attendance = total_emp * total_workdays
    
    if total_possible_attendance > 0:
        # แก้ไขการนับจำนวนการเข้างานแต่ละประเภท
        on_time_count = 0
        late_count = 0
        
        for attendance in month_attendances:
            if attendance.check_in:
                check_in_time = attendance.check_in
                if isinstance(check_in_time, datetime):
                    check_in_time = check_in_time.time()
                if check_in_time <= time(9, 0):
                    on_time_count += 1
                else:
                    late_count += 1
        
        # คำนวณอัตราส่วนเป็นเปอร์เซ็นต์
        on_time_rate = round((on_time_count / total_possible_attendance) * 100)
        late_rate = round((late_count / total_possible_attendance) * 100)
        absent_rate = 100 - (on_time_rate + late_rate)
    else:
        on_time_rate = late_rate = absent_rate = 0
    
    # คำขอลาล่าสุด
    leave_requests = LeaveRequest.objects.filter(
        status='pending'
    ).select_related('employee').order_by('-created_at')[:5]
    
    # เพิ่มข้อมูลเวลาที่ผ่านมาสำหรับคำขอลา
    for request in leave_requests:
        time_diff = timezone.now() - request.created_at
        if time_diff.days > 0:
            request.time_ago = f"{time_diff.days} วันที่แล้ว"
        elif time_diff.seconds // 3600 > 0:
            request.time_ago = f"{time_diff.seconds // 3600} ชั่วโมงที่แล้ว"
        else:
            request.time_ago = f"{time_diff.seconds // 60} นาทีที่แล้ว"

    # ดึงข้อมูลพื้นที่เช็คอินและเพิ่มสถานะการใช้งาน
    locations = LocationSettings.objects.all()
    active_location = LocationSettings.objects.filter(is_active=True).first()
    
    for location in locations:
        location.is_active = (active_location and location.id == active_location.id)
    
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
        'locations': locations,
        'start_time': start_time,
    }
    
    return render(request, 'attendance/manager_dashboard.html', context)

@login_required
def location_detail(request, location_id):
    location = get_object_or_404(LocationSettings, id=location_id)
    data = {
        'id': location.id,
        'name': location.name,
        'latitude': str(location.latitude),
        'longitude': str(location.longitude),
        'radius': location.radius,
        'is_active': location.is_active
    }
    return JsonResponse(data)

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
        photo_data = request.POST.get('photo')
        
        if not latitude or not longitude:
            messages.error(request, 'กรุณาอนุญาตการเข้าถึงตำแหน่งที่ตั้ง')
            return redirect('dashboard')
            
        if not photo_data:
            messages.error(request, 'กรุณาถ่ายรูปก่อนเช็คอิน')
            return redirect('dashboard')

        # แปลง base64 เป็นไฟล์รูปภาพ
        format, imgstr = photo_data.split(';base64,')
        ext = format.split('/')[-1]
        photo_file = ContentFile(base64.b64decode(imgstr), name=f'check_in_{request.user.id}_{timezone.now()}.{ext}')
        
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
            
        # สร้าง attendance record พร้อมรูปภาพ
        attendance = Attendance.objects.create(
            employee=request.user,
            date=current_date,
            check_in=current_time,
            status=status,
            latitude=Decimal(latitude),
            longitude=Decimal(longitude),
            check_in_photo=photo_file
        )
        
        messages.success(request, 'เช็คอินสำเร็จ')
        return redirect('attendance:dashboard')
    
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
    return redirect('attendance:privacy_policy')

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
@require_http_methods(["POST"])
def add_location(request):
    if request.user.role != 'manager':
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        # ตรวจสอบข้อมูลที่จำเป็น
        required_fields = ['name', 'latitude', 'longitude', 'radius']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False, 
                    'error': f'กรุณากรอก {field}'
                }, status=400)
        
        # สร้างพื้นที่เช็คอินใหม่
        location = LocationSettings.objects.create(
            name=data['name'],
            latitude=Decimal(data['latitude']),
            longitude=Decimal(data['longitude']),
            radius=int(data['radius'])
        )
        
        return JsonResponse({
            'success': True,
            'message': 'เพิ่มพื้นที่เช็คอินสำเร็จ',
            'location': {
                'id': location.id,
                'name': location.name,
                'latitude': str(location.latitude),
                'longitude': str(location.longitude),
                'radius': location.radius
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False, 
            'error': 'รูปแบบข้อมูลไม่ถูกต้อง'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)

@login_required
def get_location(request, location_id):
    try:
        location = LocationSettings.objects.get(id=location_id)
        return JsonResponse({
            'id': location.id,
            'name': location.name,
            'latitude': float(location.latitude),
            'longitude': float(location.longitude),
            'radius': location.radius
        })
    except LocationSettings.DoesNotExist:
        return JsonResponse({'error': 'Location not found'}, status=404)
    
# เพิ่มฟังก์ชันใหม่สำหรับดึงข้อมูล locations ทั้งหมด
@login_required
def get_locations(request):
    locations = LocationSettings.objects.all()
    return JsonResponse([{
        'id': location.id,
        'name': location.name,
        'latitude': float(location.latitude),
        'longitude': float(location.longitude),
        'radius': location.radius
    } for location in locations], safe=False)

@login_required
@require_http_methods(["POST"])
def delete_location(request, location_id):
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        location = LocationSettings.objects.get(id=location_id)
        location.delete()
        return JsonResponse({'message': 'Location deleted successfully'})
    except LocationSettings.DoesNotExist:
        return JsonResponse({'error': 'Location not found'}, status=404)

# Views สำหรับการจัดการคำขอลา
@login_required
@require_http_methods(["GET"])
def get_leave_requests(request):
    """ดึงรายการคำขอลาทั้งหมดที่รอการอนุมัติ"""
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)
        
    leave_requests = LeaveRequest.objects.filter(
        status='pending'
    ).select_related('employee').order_by('-created_at')
    
    requests_data = []
    for leave_request in leave_requests:
        time_diff = timezone.now() - leave_request.created_at
        if time_diff.days > 0:
            time_ago = f"{time_diff.days} วันที่แล้ว"
        elif time_diff.seconds // 3600 > 0:
            time_ago = f"{time_diff.seconds // 3600} ชั่วโมงที่แล้ว"
        else:
            time_ago = f"{time_diff.seconds // 60} นาทีที่แล้ว"
            
        requests_data.append({
            'id': leave_request.id,
            'employee_name': leave_request.employee.get_full_name(),
            'leave_type': leave_request.get_leave_type_display(),
            'start_date': leave_request.start_date.strftime('%Y-%m-%d'),
            'end_date': leave_request.end_date.strftime('%Y-%m-%d'),
            'reason': leave_request.reason,
            'time_ago': time_ago,
            'duration': (leave_request.end_date - leave_request.start_date).days + 1
        })
    
    return JsonResponse({'leave_requests': requests_data})

@login_required
@require_http_methods(["POST"])
def approve_leave_request(request, request_id):
    """อนุมัติคำขอลา"""
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)
        
    leave_request = get_object_or_404(LeaveRequest, id=request_id)
    leave_request.status = 'approved'
    leave_request.approved_by = request.user
    leave_request.approved_at = timezone.now()
    leave_request.save()
    
    return JsonResponse({'message': 'Leave request approved successfully'})

@login_required
@require_http_methods(["POST"])
def reject_leave_request(request, request_id):
    """ปฏิเสธคำขอลา"""
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)
        
    leave_request = get_object_or_404(LeaveRequest, id=request_id)
    leave_request.status = 'rejected'
    leave_request.approved_by = request.user
    leave_request.approved_at = timezone.now()
    leave_request.save()
    
    return JsonResponse({'message': 'Leave request rejected successfully'})

# Views สำหรับการดึงข้อมูลการเข้างาน
@login_required
@require_http_methods(["GET"])
def get_today_attendance(request):
    """ดึงข้อมูลการเข้างานวันนี้"""
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)
        
    today = timezone.localtime().date()
    start_time = time(9, 0)  # 9:00 น.
    
    attendances = Attendance.objects.filter(
        date=today
    ).select_related('employee').order_by('-check_in')
    
    attendance_data = []
    for attendance in attendances:
        check_in_time = attendance.check_in
        if isinstance(check_in_time, datetime):
            check_in_time = check_in_time.time()
            
        attendance_data.append({
            'employee_name': attendance.employee.get_full_name(),
            'department': attendance.employee.department,
            'check_in': attendance.check_in.strftime('%H:%M') if attendance.check_in else None,
            'check_out': attendance.check_out.strftime('%H:%M') if attendance.check_out else None,
            'status': 'ตรงเวลา' if check_in_time <= start_time else 'มาสาย',
            'location': {
                'latitude': str(attendance.latitude),
                'longitude': str(attendance.longitude)
            }
        })
    
    return JsonResponse({'attendances': attendance_data})

@login_required
@require_http_methods(["GET"])
def get_attendance_stats(request):
    """ดึงสถิติการเข้างานประจำเดือน"""
    if request.user.role != 'manager':
        return JsonResponse({'error': 'Permission denied'}, status=403)
        
    today = timezone.localtime().date()
    first_day = today.replace(day=1)
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    start_time = time(9, 0)
    
    month_attendances = Attendance.objects.filter(
        date__range=[first_day, last_day]
    ).select_related('employee')
    
    total_days = (last_day - first_day).days + 1
    on_time_count = late_count = 0
    
    for attendance in month_attendances:
        check_in_time = attendance.check_in
        if isinstance(check_in_time, datetime):
            check_in_time = check_in_time.time()
        if check_in_time <= start_time:
            on_time_count += 1
        else:
            late_count += 1
    
    stats = {
        'on_time_rate': round((on_time_count / total_days) * 100) if total_days > 0 else 0,
        'late_rate': round((late_count / total_days) * 100) if total_days > 0 else 0,
        'absent_rate': round(((total_days - (on_time_count + late_count)) / total_days) * 100) if total_days > 0 else 0
    }
    
    return JsonResponse(stats)