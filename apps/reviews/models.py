from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from workers.models import WorkerProfile
from bookings.models import ServiceRequest


class Review(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews', verbose_name='ใบงานที่เกี่ยวข้อง')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_reviews', verbose_name='ผู้ให้รีวิว (ลูกค้า)')
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='reviews', verbose_name='ช่างที่ถูกรีวิว')
    rating = models.IntegerField('คะแนน (1-5)', validators=[MinValueValidator(1), MaxValueValidator(5)], default=5)
    comment = models.TextField('ความคิดเห็น / รีวิว', blank=True, null=True)
    worker_reply = models.TextField('การตอบกลับจากช่าง', blank=True, null=True)
    worker_replied_at = models.DateTimeField('เวลาที่ช่างตอบกลับ', blank=True, null=True)
    is_hidden = models.BooleanField('ซ่อนรีวิวนี้ (Admin Moderation)', default=False)
    created_at = models.DateTimeField('วันที่รีวิว', auto_now_add=True)

    class Meta:
        db_table = 'reviews'
        verbose_name = 'รีวิวและการให้คะแนน'
        verbose_name_plural = 'รีวิวทั้งหมด'
        ordering = ['-created_at']

    def __str__(self):
        return f"รีวิว {self.rating}★ จาก {self.customer.full_name} ถึง {self.worker.user.full_name}"
