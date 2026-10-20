from django.db import models
from django.conf import settings
from workers.models import WorkerProfile


class Report(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'รอการตรวจสอบ (Pending)'),
        ('RESOLVED', 'ดำเนินการเรียบร้อย (Resolved)'),
        ('DISMISSED', 'ยกเลิก / ไม่อนุมัติรายงาน (Dismissed)'),
    )

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submitted_reports', verbose_name='ผู้รายงาน')
    reported_worker = models.ForeignKey(WorkerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_received', verbose_name='ช่างที่ถูกรายงาน')
    reported_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_reports_received', verbose_name='ผู้ใช้ที่ถูกรายงาน')
    reason = models.TextField('สาเหตุ / รายละเอียดการรายงานพฤติกรรมไม่เหมาะสม')
    evidence_image = models.ImageField('รูปภาพหลักฐาน', upload_to='reports/evidence/', max_length=255, blank=True, null=True)
    status = models.CharField('สถานะการดำเนินการ', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    admin_notes = models.TextField('บันทึกของผู้ดูแลระบบ', blank=True, null=True)
    created_at = models.DateTimeField('วันที่แจ้งรายงาน', auto_now_add=True)

    @property
    def display_evidence_url(self):
        if self.evidence_image:
            raw = str(self.evidence_image)
            if raw.startswith(('http://', 'https://')):
                return raw
            try:
                return self.evidence_image.url
            except Exception:
                return None
        return None

    class Meta:
        db_table = 'reports'
        verbose_name = 'รายงานปัญหา'
        verbose_name_plural = 'รายงานปัญหาทั้งหมด'
        ordering = ['-created_at']

    def __str__(self):
        target = self.reported_worker.user.full_name if self.reported_worker else (self.reported_user.full_name if self.reported_user else 'Unknown')
        return f"รายงาน #{self.id} เกี่ยวกับ {target} ({self.get_status_display()})"
