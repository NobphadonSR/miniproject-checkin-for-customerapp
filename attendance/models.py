from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class User(AbstractUser):
    ROLE_CHOICES = (
        ('manager', 'หัวหน้า'),
        ('employee', 'พนักงาน'),
    )
    DEPARTMENT_CHOICES = [
        ('purchasing', 'ฝ่ายจัดซื้อ'),
        ('sale_co', 'ฝ่ายSaleCo'),
        ('store', 'ฝ่ายสโตร์'),
        ('delivery', 'ฝ่ายจัดส่ง'),
        ('accounting', 'ฝ่ายบัญชี'),
        ('engineering', 'ฝ่ายวิศวะ'),
        ('it', 'ฝ่ายIT'),
        ('gps', 'ฝ่ายGPS'),
        ('production', 'ฝ่ายผลิต'),
        ('sales_project', 'ฝ่ายSales Project'),
        ('sales', 'ฝ่ายSales'),
        ('marketing', 'ฝ่ายการตลาด'),
        ('hr', 'ฝ่ายHR'),
        ('sales_solar', 'ฝ่ายSales Solar Project'),
        ('sales_plusclean', 'ฝ่ายSales Plusclean Project'),
    ]
    
    role = models.CharField('ตำแหน่ง', max_length=10, choices=ROLE_CHOICES)
    department = models.CharField('แผนก', max_length=20, choices=DEPARTMENT_CHOICES)
    phone = models.CharField('เบอร์โทรศัพท์', max_length=10)
    address = models.TextField('ที่อยู่')

    def clean(self):
        if not self.phone or len(self.phone) != 10:
            raise ValidationError({'phone': 'เบอร์โทรศัพท์ต้องมี 10 หลัก'})
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'attendance_user'  # กำหนดชื่อตารางให้ชัดเจน
        verbose_name = 'ผู้ใช้งาน'
        verbose_name_plural = 'ผู้ใช้งาน'

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('present', 'มาทำงาน'),
        ('late', 'มาสาย'),
        ('absent', 'ขาดงาน'),
        ('leave', 'ลา'),
    )
    
    employee = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='พนักงาน')
    date = models.DateField('วันที่')
    check_in = models.TimeField('เวลาเข้างาน', null=True, blank=True)
    check_out = models.TimeField('เวลาออกงาน', null=True, blank=True)
    latitude = models.DecimalField('ละติจูด', max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField('ลองจิจูด', max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField('สถานะ', max_length=10, choices=STATUS_CHOICES)
    note = models.TextField('หมายเหตุ', blank=True)

    class Meta:
        verbose_name = 'การลงเวลา'
        verbose_name_plural = 'การลงเวลา'

class LocationSettings(models.Model):
    name = models.CharField('ชื่อสถานที่', max_length=100)
    latitude = models.DecimalField('ละติจูด', max_digits=20, decimal_places=15)
    longitude = models.DecimalField('ลองจิจูด', max_digits=20, decimal_places=15)
    radius = models.IntegerField('รัศมี (เมตร)', default=100)

    class Meta:
        verbose_name = 'ตั้งค่าพิกัดสถานที่'
        verbose_name_plural = 'ตั้งค่าพิกัดสถานที่'