from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from attendance.models import LocationSettings

User = get_user_model()

class Command(BaseCommand):
    help = 'Initialize database with required data'

    def handle(self, *args, **kwargs):
        # สร้าง superuser
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='adminpassword',
                role='manager',
                department='it',
                phone='0000000000',
                address='Bangkok'
            )
            self.stdout.write(self.style.SUCCESS('Superuser created successfully'))

        # สร้างข้อมูล LocationSettings
        if not LocationSettings.objects.exists():
            LocationSettings.objects.create(
                name='Office',
                latitude='13.736717',
                longitude='100.523186',
                radius=100
            )
            self.stdout.write(self.style.SUCCESS('Location settings created successfully'))