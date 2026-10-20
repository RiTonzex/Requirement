from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'ผู้ดูแลระบบ (Admin)'),
        ('CUSTOMER', 'ผู้ใช้ทั่วไป/ลูกค้า (Customer)'),
        ('WORKER', 'ช่างรับจ้าง (Worker)'),
    )

    email = models.EmailField('อีเมล', unique=True)
    phone_number = models.CharField('เบอร์โทรศัพท์', max_length=20, blank=True, null=True)
    role = models.CharField('บทบาท', max_length=20, choices=ROLE_CHOICES, default='CUSTOMER')
    avatar = models.ImageField('รูปโปรไฟล์/รูปประจำตัว', upload_to='users/avatars/', max_length=255, blank=True, null=True)
    created_at = models.DateTimeField('วันที่สร้างบัญชี', auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'ผู้ใช้งาน'
        verbose_name_plural = 'ผู้ใช้งานทั้งหมด'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin_user(self):
        return self.role == 'ADMIN' or self.is_superuser

    @property
    def is_worker(self):
        return self.role == 'WORKER'

    @property
    def is_customer(self):
        return self.role == 'CUSTOMER'

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def avatar_url(self):
        """ดึง URL รูปโปรไฟล์: หากเป็นช่างและมีรูปโปรไฟล์ช่างให้ใช้รูปช่าง, หรือใช้ avatar ของ user, หากไม่มีให้ใช้ภาพ Avatar คุณภาพสูง"""
        if self.is_worker and hasattr(self, 'worker_profile'):
            return self.worker_profile.display_profile_image_url
        if self.avatar:
            raw = str(self.avatar)
            if raw.startswith(('http://', 'https://')):
                return raw
            try:
                return self.avatar.url
            except Exception:
                pass
        
        from core.avatar_utils import generate_initial_avatar
        display_name = self.first_name or self.username or self.email
        return generate_initial_avatar(display_name, self.id)


