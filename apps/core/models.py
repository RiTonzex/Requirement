from django.db import models
from django.conf import settings


class Category(models.Model):
    category_name = models.CharField('ชื่อหมวดหมู่', max_length=100, unique=True)
    icon = models.CharField('ไอคอน (FontAwesome)', max_length=50, default='fa-wrench')
    description = models.CharField('คำอธิบาย', max_length=255, blank=True, null=True)
    is_active = models.BooleanField('สถานะการเปิดใช้งาน', default=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'หมวดหมู่งาน/บริการ'
        verbose_name_plural = 'หมวดหมู่งาน/บริการทั้งหมด'
        ordering = ['category_name']

    def __str__(self):
        return self.category_name


class Province(models.Model):
    province_name = models.CharField('ชื่อจังหวัด', max_length=100, unique=True)

    class Meta:
        db_table = 'provinces'
        verbose_name = 'จังหวัด'
        verbose_name_plural = 'รายชื่อ 77 จังหวัด'
        ordering = ['province_name']

    def __str__(self):
        return self.province_name


class SearchLog(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='หมวดหมู่')
    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='จังหวัด')
    keyword = models.CharField('คำค้นหา', max_length=100, blank=True, null=True)
    searched_at = models.DateTimeField('เวลาที่ค้นหา', auto_now_add=True)
    ip_address = models.GenericIPAddressField('IP Address', blank=True, null=True)

    class Meta:
        db_table = 'search_logs'
        verbose_name = 'บันทึกการค้นหา'
        verbose_name_plural = 'ประวัติการค้นหาทั้งหมด'
        ordering = ['-searched_at']

    def __str__(self):
        return f"Search [{self.keyword or 'All'}] at {self.searched_at:%Y-%m-%d %H:%M}"


class Notification(models.Model):
    TYPE_CHOICES = (
        ('BOOKING', 'คำขอจองบริการ'),
        ('STATUS', 'อัปเดตสถานะงาน'),
        ('REVIEW', 'รีวิวใหม่'),
        ('KYC', 'การยืนยันตัวตน'),
        ('SYSTEM', 'ข้อความจากระบบ'),
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', verbose_name='ผู้รับการแจ้งเตือน')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications', verbose_name='ผู้ส่ง')
    title = models.CharField('หัวข้อแจ้งเตือน', max_length=150)
    message = models.TextField('ข้อความแจ้งเตือน')
    link_url = models.CharField('ลิงก์ไปยังหน้าที่เกี่ยวข้อง', max_length=255, blank=True, null=True)
    notification_type = models.CharField('ประเภทการแจ้งเตือน', max_length=20, choices=TYPE_CHOICES, default='SYSTEM')
    is_read = models.BooleanField('อ่านแล้วหรือยัง', default=False)
    created_at = models.DateTimeField('เวลาที่สร้าง', auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'การแจ้งเตือน'
        verbose_name_plural = 'การแจ้งเตือนทั้งหมด'
        ordering = ['-created_at']

    def __str__(self):
        return f"แจ้งเตือน: {self.title} ถึง {self.recipient.username}"
