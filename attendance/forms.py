from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Attendance

class EmployeeRegistrationForm(UserCreationForm):
    username = forms.CharField(
        label='ชื่อผู้ใช้',
        widget=forms.TextInput(attrs={'class': 'w-full p-2 border rounded'})
    )
    first_name = forms.CharField(
        label='ชื่อจริง',
        widget=forms.TextInput(attrs={'class': 'w-full p-2 border rounded'})
    )
    last_name = forms.CharField(
        label='นามสกุล',
        widget=forms.TextInput(attrs={'class': 'w-full p-2 border rounded'})
    )
    email = forms.EmailField(
        label='อีเมล',
        widget=forms.EmailInput(attrs={'class': 'w-full p-2 border rounded'})
    )
    # เพิ่มฟิลด์ department
    department = forms.ChoiceField(
        label='แผนก',
        choices=User.DEPARTMENT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white'
        })
    )
    phone = forms.CharField(
        label='เบอร์โทรศัพท์',
        widget=forms.TextInput(attrs={'class': 'w-full p-2 border rounded'})
    )
    address = forms.CharField(
        label='ที่อยู่',
        widget=forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'rows': '3'})
    )
    password1 = forms.CharField(
        label='รหัสผ่าน',
        widget=forms.PasswordInput(attrs={'class': 'w-full p-2 border rounded'})
    )
    password2 = forms.CharField(
        label='ยืนยันรหัสผ่าน',
        widget=forms.PasswordInput(attrs={'class': 'w-full p-2 border rounded'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'department', 'phone', 'address', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ปรับข้อความช่วยเหลือเป็นภาษาไทย
        self.fields['password1'].help_text = 'รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร'
        self.fields['username'].help_text = 'ต้องเป็นตัวอักษร ตัวเลข หรือ @/./+/-/_ เท่านั้น'
        # ปรับแต่งฟิลด์ department
        self.fields['department'].widget.attrs.update({
            'class': 'w-full p-2 border rounded dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:ring-2 focus:ring-indigo-500'
        })

class LeaveRequestForm(forms.ModelForm):
    date = forms.DateField(label='วันที่ต้องการลา', widget=forms.DateInput(attrs={'type': 'date'}))
    note = forms.CharField(label='เหตุผลการลา', widget=forms.Textarea)

    class Meta:
        model = Attendance
        fields = ['date', 'note']