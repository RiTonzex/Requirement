from django.db import models
from django.conf import settings
from core.models import Category
from workers.models import WorkerProfile


class ServiceRequest(models.Model):
    STATUS_CHOICES = (
        ('REQUESTED', 'รอดำเนินการตอบรับ (Requested)'),
        ('ACCEPTED', 'ช่างตอบรับงานแล้ว (Accepted)'),
        ('IN_PROGRESS', 'กำลังดำเนินการซ่อม/ติดตั้ง (In Progress)'),
        ('COMPLETED', 'เสร็จสิ้นสมบูรณ์ (Completed)'),
        ('CANCELLED', 'ยกเลิกคำขอ (Cancelled)'),
    )

    TIME_SLOT_CHOICES = (
        ('ANY', 'สะดวกทุกช่วงเวลา'),
        ('MORNING', 'ช่วงเช้า (08:00 - 12:00 น.)'),
        ('AFTERNOON', 'ช่วงบ่าย (13:00 - 17:00 น.)'),
        ('EVENING', 'ช่วงเย็น/ค่ำ (17:00 - 20:00 น.)'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('UNPAID', 'ยังไม่ชำระเงิน (Unpaid)'),
        ('SLIP_UPLOADED', 'แนบสลิปแล้ว - รอช่างตรวจสอบ (Pending Verification)'),
        ('PAID', 'ชำระเงินเรียบร้อยแล้ว (Paid)'),
    )

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_requests', verbose_name='ลูกค้า')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='service_requests', verbose_name='ช่าง')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='service_requests', verbose_name='ประเภทงานหลัก')
    categories = models.ManyToManyField(Category, related_name='multi_service_requests', blank=True, verbose_name='ประเภทงานทั้งหมดที่เลือก')
    status = models.CharField('สถานะงาน', max_length=20, choices=STATUS_CHOICES, default='REQUESTED')
    details = models.TextField('รายละเอียดงานที่ต้องการซ่อม/ติดตั้ง')
    address_note = models.CharField('สถานที่ปฏิบัติงาน / ที่อยู่', max_length=255, blank=True, null=True)
    preferred_date = models.DateField('วันที่สะดวกรับบริการ', blank=True, null=True)
    preferred_time_slot = models.CharField('ช่วงเวลาที่สะดวก', max_length=30, choices=TIME_SLOT_CHOICES, default='ANY')
    problem_image = models.ImageField('รูปถ่ายปัญหา/หน้างาน (Before Photo)', upload_to='bookings/problems/', max_length=255, blank=True, null=True)
    
    # Pricing & Notes
    agreed_price = models.DecimalField('ราคาค่าบริการที่ตกลงกัน (บาท)', max_digits=10, decimal_places=2, null=True, blank=True)
    price_note = models.CharField('หมายเหตุราคา / รายละเอียดค่าใช้จ่ายเพิ่มเติม', max_length=255, null=True, blank=True)
    
    # Feature 1: Payment & Slip Verification
    payment_status = models.CharField('สถานะการชำระเงิน', max_length=20, choices=PAYMENT_STATUS_CHOICES, default='UNPAID')
    payment_slip = models.ImageField('สลิปการโอนเงิน (Payment Slip)', upload_to='bookings/slips/', max_length=255, blank=True, null=True)
    paid_at = models.DateTimeField('วันเวลาที่ยืนยันการชำระเงิน', blank=True, null=True)

    # Feature 2: Before & After Photo Proof
    completion_image = models.ImageField('รูปภาพหลังซ่อม/งานเสร็จสมบูรณ์ (After Photo)', upload_to='bookings/completions/', max_length=255, blank=True, null=True)
    completion_note = models.TextField('บันทึกสรุปงานช่าง / รายละเอียดการซ่อมแซม', blank=True, null=True)

    # Feature 4: Warranty Guarantee
    warranty_days = models.IntegerField('ระยะเวลารับประกันผลงาน (วัน)', default=30)
    warranty_expires_at = models.DateField('วันสิ้นสุดระยะเวลารับประกัน', blank=True, null=True)

    created_at = models.DateTimeField('วันที่สร้างคำขอ', auto_now_add=True)
    updated_at = models.DateTimeField('วันที่อัปเดตล่าสุด', auto_now=True)

    class Meta:
        db_table = 'service_requests'
        verbose_name = 'คำขอรับบริการ'
        verbose_name_plural = 'คำขอรับบริการทั้งหมด'
        ordering = ['-created_at']

    def __str__(self):
        return f"คำขอ #{self.id} โดย {self.customer.full_name} ถึง {self.worker.user.full_name} ({self.get_status_display()})"

    @property
    def display_problem_image_url(self):
        """ดึง URL รูปภาพปัญหาหน้างาน หรือรูปตัวอย่าง HD ตามหมวดหมู่งาน"""
        if self.problem_image:
            raw = str(self.problem_image)
            if raw.startswith(('http://', 'https://')):
                return raw
            try:
                return self.problem_image.url
            except Exception:
                pass
        
        # ภาพปัญหาหน้างานตัวอย่างตามหมวดหมู่งาน
        sample_problems = [
            "https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=700&auto=format&fit=crop&q=80",  # ตู้ไฟ/ระบบไฟฟ้า
            "https://images.unsplash.com/photo-1621905252507-b35492cc74b4?w=700&auto=format&fit=crop&q=80",  # ล้างแอร์/แอร์รั่ว
            "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?w=700&auto=format&fit=crop&q=80",  # ท่อประปาแตก/รั่ว
            "https://images.unsplash.com/photo-1590381105924-c72589b9ef3f?w=700&auto=format&fit=crop&q=80",  # รีโนเวท/ปูนแตกร้าว
        ]
        bid = getattr(self, 'id', 1) or 1
        return sample_problems[bid % len(sample_problems)]

    @property
    def all_categories(self):
        """ดึงรายการหมวดหมู่งานทั้งหมดที่ลูกค้าเลือกไว้ (หากมี ManyToMany ให้ใช้ตามนั้น หรือ fallback เป็น category หลัก)"""
        try:
            cats = list(self.categories.all())
            if cats:
                return cats
        except Exception:
            pass
        if self.category:
            return [self.category]
        return []

    @property
    def all_categories_display(self):
        cats = self.all_categories
        if cats:
            return ", ".join([c.category_name for c in cats])
        return self.category.category_name if self.category else "ไม่ระบุ"

    @property
    def initial_estimated_price(self):
        """คำนวณราคาเริ่มต้นรวมของทุกประเภทงานที่ลูกค้าเลือกไว้"""
        cats = self.all_categories
        if not cats:
            return 0.0
        services = self.worker.services.filter(category__in=cats)
        if services.exists():
            return sum([s.starting_price for s in services])
        service = self.worker.services.filter(category=self.category).first()
        return service.starting_price if service else 0.0

    @property
    def final_price(self):
        """ราคาค่าบริการจริง: หากมีการตกลงเรทราคาใหม่ ให้ใช้ agreed_price, หากยังไม่มีให้ใช้ราคาเริ่มต้นประเมินรวมของช่าง"""
        if self.agreed_price is not None:
            return self.agreed_price
        return self.initial_estimated_price

    @property
    def service_price_unit(self):
        service = self.worker.services.filter(category=self.category).first()
        return service.price_unit if service and service.price_unit else '/งาน'

    @property
    def display_completion_image_url(self):
        """ดึง URL รูปภาพหลังซ่อม/งานเสร็จสมบูรณ์ (After Photo) หรือภาพผลงานสำเร็จตัวอย่าง"""
        if self.completion_image:
            raw = str(self.completion_image)
            if raw.startswith(('http://', 'https://')):
                return raw
            try:
                return self.completion_image.url
            except Exception:
                pass
        
        sample_completions = [
            "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=700&auto=format&fit=crop&q=80",  # ระบบไฟเรียบร้อย
            "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=700&auto=format&fit=crop&q=80",  # ห้องสะอาดเรียบร้อย
            "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=700&auto=format&fit=crop&q=80",  # ท่อประปาใหม่กริ๊บ
            "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=700&auto=format&fit=crop&q=80",  # แอร์เย็นฉ่ำ
        ]
        bid = getattr(self, 'id', 1) or 1
        return sample_completions[bid % len(sample_completions)]

    @property
    def display_payment_slip_url(self):
        """ดึง URL สลิปโอนเงิน"""
        if self.payment_slip:
            raw = str(self.payment_slip)
            if raw.startswith(('http://', 'https://')):
                return raw
            try:
                return self.payment_slip.url
            except Exception:
                pass
        return None

    @property
    def is_warranty_active(self):
        """ตรวจสอบว่าการรับประกันผลงานยังมีความคุ้มครองอยู่หรือไม่"""
        from django.utils import timezone
        if not self.warranty_expires_at:
            return False
        return self.warranty_expires_at >= timezone.now().date()

    @property
    def warranty_days_remaining(self):
        """คำนวณจำนวนวันที่เหลือของความคุ้มครอง"""
        from django.utils import timezone
        if not self.warranty_expires_at:
            return 0
        diff = (self.warranty_expires_at - timezone.now().date()).days
        return max(0, diff)

    @property
    def promptpay_qr_svg(self):
        """สร้าง QR Code พร้อมเพย์ตามยอดเงินจริงและเบอร์ช่าง"""
        try:
            from .promptpay import generate_promptpay_qr_svg
            target_account = self.worker.effective_promptpay_number
            price = float(self.final_price) if self.final_price else 0.0
            return generate_promptpay_qr_svg(target_account, price)
        except Exception:
            return ""

