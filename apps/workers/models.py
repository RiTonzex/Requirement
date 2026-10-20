from django.db import models
from django.conf import settings
from django.db.models import Avg, Count
from core.models import Category, Province


class WorkerProfile(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'รอตรวจสอบ (Pending)'),
        ('APPROVED', 'อนุมัติแล้ว (Approved)'),
        ('REJECTED', 'ปฏิเสธ (Rejected)'),
        ('SUSPENDED', 'ระงับการใช้งาน (Suspended)'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='worker_profile', verbose_name='ผู้ใช้')
    bio = models.TextField('ประวัติ / ข้อมูลแนะนำตัว', blank=True, null=True)
    working_hours = models.CharField('วันและเวลาทำการ', max_length=150, blank=True, null=True, default='จันทร์ - เสาร์ (08:30 - 18:00 น.)')
    status = models.CharField('สถานะการอนุมัติ', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    is_available = models.BooleanField('สถานะพร้อมรับงาน', default=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_workers', verbose_name='ผู้อนุมัติ')
    approved_at = models.DateTimeField('เวลาที่อนุมัติ', null=True, blank=True)
    rejection_reason = models.TextField('เหตุผลการปฏิเสธ / หมายเหตุ', blank=True, null=True)
    profile_image = models.ImageField('รูปโปรไฟล์', upload_to='workers/profiles/', max_length=255, blank=True, null=True)
    
    # KYC & Identity Verification
    id_card_image = models.ImageField('รูปบัตรประชาชน (สำหรับ KYC)', upload_to='workers/kyc/', max_length=255, blank=True, null=True)
    certificate_image = models.ImageField('รูปใบประกอบวิชาชีพ / ประกาศนียบัตร', upload_to='workers/certificates/', max_length=255, blank=True, null=True)
    is_id_verified = models.BooleanField('ผ่านการยืนยันตัวตน (Verified Badge)', default=False)

    # PromptPay & Warranty & GPS Location
    promptpay_number = models.CharField('เบอร์พร้อมเพย์ หรือเลขประจำตัวประชาชน', max_length=20, blank=True, null=True)
    warranty_days = models.IntegerField('ระยะเวลารับประกันงานมาตรฐาน (วัน)', default=30)
    latitude = models.DecimalField('พิกัดละติจูด (Latitude)', max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField('พิกัดลองจิจูด (Longitude)', max_digits=10, decimal_places=7, null=True, blank=True)

    class Meta:
        db_table = 'workers'
        verbose_name = 'โปรไฟล์ช่าง'
        verbose_name_plural = 'โปรไฟล์ช่างทั้งหมด'

    def __str__(self):
        return f"ช่าง: {self.user.full_name} ({self.get_status_display()})"

    @property
    def display_profile_image_url(self):
        """ดึง URL รูปโปรไฟล์ช่าง (จาก Cloudinary หรือรูปตัวอย่าง HD เฉพาะทางของแต่ละสายงาน)"""
        if self.profile_image:
            raw = str(self.profile_image)
            if raw.startswith(('http://', 'https://')):
                return raw
            try:
                return self.profile_image.url
            except Exception:
                pass
        
        from core.avatar_utils import generate_initial_avatar
        display_name = ''
        if hasattr(self, 'user') and self.user:
            display_name = self.user.first_name or self.user.username
        return generate_initial_avatar(display_name, getattr(self, 'id', 1))

    @property
    def display_id_card_url(self):
        """ดึง URL บัตรประชาชน KYC หรือตัวอย่างเอกสารยืนยันตัวตน"""
        if self.id_card_image:
            raw = str(self.id_card_image)
            if raw.startswith(('http://', 'https://')):
                return raw
            try:
                return self.id_card_image.url
            except Exception:
                pass
        return "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=600&auto=format&fit=crop&q=80"

    @property
    def display_certificate_url(self):
        """ดึง URL ใบประกอบวิชาชีพ หรือตัวอย่างใบประกาศนียบัตร"""
        if self.certificate_image:
            raw = str(self.certificate_image)
            if raw.startswith(('http://', 'https://')):
                return raw
            try:
                return self.certificate_image.url
            except Exception:
                pass
        return "https://images.unsplash.com/photo-1606326608606-aa0b62935f2b?w=600&auto=format&fit=crop&q=80"



    @property
    def effective_promptpay_number(self):
        """ดึงเบอร์พร้อมเพย์ของช่าง หากไม่ได้ตั้งค่า ให้ใช้เบอร์โทรศัพท์ในบัญชีผู้ใช้งาน"""
        if self.promptpay_number:
            clean = "".join(filter(str.isdigit, str(self.promptpay_number)))
            if clean:
                return clean
        if hasattr(self, 'user') and self.user and self.user.phone_number:
            clean = "".join(filter(str.isdigit, str(self.user.phone_number)))
            if clean:
                return clean
        return "0812345678"

    @property
    def has_reviews(self):
        return self.reviews.filter(is_hidden=False).exists()

    @property
    def average_rating(self):
        avg = self.reviews.filter(is_hidden=False).aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0.0

    @property
    def review_count(self):
        return self.reviews.filter(is_hidden=False).count()

    @property
    def completed_jobs_count(self):
        return self.service_requests.filter(status='COMPLETED').count()

    @property
    def min_starting_service(self):
        """ดึงบริการที่มีราคาเริ่มต้นถูกที่สุดของช่างท่านนี้"""
        return self.services.select_related('category').order_by('starting_price').first()

    @property
    def services_list(self):
        return self.services.select_related('category').order_by('starting_price').all()

    @property
    def service_areas_list(self):
        return self.service_areas.select_related('province').all()


class WorkerService(models.Model):
    PRICE_UNIT_CHOICES = (
        ('/งาน', 'บาท / งาน'),
        ('/เครื่อง', 'บาท / เครื่อง'),
        ('/จุด', 'บาท / จุด'),
        ('/ตร.ม.', 'บาท / ตร.ม.'),
        ('/ชั่วโมง', 'บาท / ชั่วโมง'),
        ('/วัน', 'บาท / วัน'),
    )

    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='services', verbose_name='ช่าง')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='worker_services', verbose_name='หมวดหมู่บริการ')
    starting_price = models.DecimalField('ราคาเริ่มต้น (บาท)', max_digits=10, decimal_places=2, default=0.00)
    price_unit = models.CharField('หน่วยราคา', max_length=20, choices=PRICE_UNIT_CHOICES, default='/งาน')

    class Meta:
        db_table = 'worker_services'
        verbose_name = 'บริการของช่าง'
        verbose_name_plural = 'บริการของช่างทั้งหมด'
        unique_together = ('worker', 'category')
        ordering = ['starting_price']

    def __str__(self):
        return f"{self.worker.user.full_name} - {self.category.category_name} (฿{self.starting_price:,.2f} {self.price_unit})"


class WorkerServiceArea(models.Model):
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='service_areas', verbose_name='ช่าง')
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name='workers_in_province', verbose_name='จังหวัด')

    class Meta:
        db_table = 'worker_service_areas'
        verbose_name = 'พื้นที่ให้บริการของช่าง'
        verbose_name_plural = 'พื้นที่ให้บริการของช่างทั้งหมด'
        unique_together = ('worker', 'province')

    def __str__(self):
        return f"{self.worker.user.full_name} - {self.province.province_name}"


class SavedWorker(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_workers', verbose_name='ลูกค้า')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='saved_by_customers', verbose_name='ช่างที่ถูกใจ')
    created_at = models.DateTimeField('วันที่บันทึก', auto_now_add=True)

    class Meta:
        db_table = 'saved_workers'
        verbose_name = 'ช่างที่บันทึกไว้'
        verbose_name_plural = 'รายการช่างที่บันทึกไว้ทั้งหมด'
        unique_together = ('customer', 'worker')

    def __str__(self):
        return f"{self.customer.full_name} บุ๊กมาร์ก {self.worker.user.full_name}"
