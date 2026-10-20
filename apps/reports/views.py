from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Report
from workers.models import WorkerProfile
from core.models import Notification


@login_required
def create_report_view(request):
    if request.method == 'POST':
        worker_id = request.POST.get('worker_id')
        reason = request.POST.get('reason', '').strip()

        if not reason:
            messages.error(request, "กรุณาระบุรายละเอียดเหตุผลการรายงานปัญหา")
            return redirect(request.META.get('HTTP_REFERER', 'core:home'))

        reported_worker = None
        if worker_id and worker_id.isdigit():
            reported_worker = WorkerProfile.objects.filter(id=worker_id).first()

        evidence_image = request.FILES.get('evidence_image')

        Report.objects.create(
            reporter=request.user,
            reported_worker=reported_worker,
            reason=reason,
            evidence_image=evidence_image,
            status='PENDING'
        )

        messages.success(request, "ส่งรายงานปัญหาไปยังทีมผู้ดูแลระบบเรียบร้อยแล้ว เราจะดำเนินการตรวจสอบโดยเร็วที่สุด")
        return redirect(request.META.get('HTTP_REFERER', 'core:home'))

    return redirect('core:home')


@login_required
def resolve_report_view(request, report_id):
    if not request.user.is_admin_user:
        messages.error(request, "สิทธิ์เฉพาะผู้ดูแลระบบเท่านั้น")
        return redirect('core:home')

    report = get_object_or_404(Report, id=report_id)

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        admin_notes = request.POST.get('admin_notes', '').strip()
        target_worker = report.reported_worker
        target_user = target_worker.user if target_worker else report.reported_user
        now_str = timezone.now().strftime('%d/%m/%Y %H:%M')

        if action == 'WARN':
            # 1. ส่งข้อความเตือนไปยังช่าง / ผู้ใช้ที่ถูกรายงาน
            warning_msg = request.POST.get('warning_message', '').strip()
            if not warning_msg:
                warning_msg = f"ผู้ดูแลระบบได้รับรายงานปัญหาเกี่ยวกับพฤติกรรมหรือบริการของคุณ (รายงาน #{report.id}) กรุณาปรับปรุงการให้บริการและปฏิบัติตามกฎระเบียบของระบบอย่างเคร่งครัด"

            if target_user:
                Notification.objects.create(
                    recipient=target_user,
                    sender=request.user,
                    title="⚠️ แจ้งเตือนข้อควรระวัง / พฤติกรรมไม่เหมาะสม",
                    message=warning_msg,
                    link_url='/dashboard/',
                    notification_type='SYSTEM'
                )

            note_entry = f"[แจ้งเตือนเมื่อ {now_str}]: {warning_msg}"
            report.admin_notes = f"{note_entry}\n{report.admin_notes}" if report.admin_notes else note_entry
            report.save()

            messages.warning(request, f"ส่งข้อความแจ้งเตือนไปยังคุณ {target_user.full_name if target_user else 'ผู้ใช้'} สำเร็จ")

        elif action == 'SUSPEND':
            # 2. ระงับบัญชีช่างทันที
            suspend_reason = request.POST.get('suspend_reason', '').strip()
            if not suspend_reason:
                suspend_reason = f"ตรวจพบพฤติกรรมไม่เหมาะสมหรือผิดเงื่อนไขตามรายงานปัญหา #{report.id}: {report.reason}"

            if target_worker:
                target_worker.status = 'SUSPENDED'
                target_worker.is_available = False
                target_worker.rejection_reason = suspend_reason
                target_worker.save()

                Notification.objects.create(
                    recipient=target_worker.user,
                    sender=request.user,
                    title="🚫 บัญชีช่างของคุณถูกระงับการใช้งานชั่วคราว",
                    message=f"บัญชีของคุณถูกระงับเนื่องจาก: {suspend_reason} หากมีข้อโต้แย้งกรุณาติดต่อผู้ดูแลระบบ",
                    link_url='/dashboard/',
                    notification_type='SYSTEM'
                )

            note_entry = f"[ระงับบัญชีเมื่อ {now_str}]: {suspend_reason}"
            report.admin_notes = f"{note_entry}\n{report.admin_notes}" if report.admin_notes else note_entry
            report.status = 'RESOLVED'
            report.save()

            messages.error(request, f"ระงับการใช้งานบัญชีช่าง {target_worker.user.full_name if target_worker else ''} และแจ้งเตือนแล้ว")

        elif action == 'RESTORE':
            # 3. ปลดระงับบัญชีช่าง
            if target_worker:
                target_worker.status = 'APPROVED'
                target_worker.save()

                Notification.objects.create(
                    recipient=target_worker.user,
                    sender=request.user,
                    title="✅ บัญชีช่างของคุณได้รับการปลดระงับแล้ว",
                    message="ผู้ดูแลระบบได้ทำการปลดระงับบัญชีของคุณเรียบร้อยแล้ว คุณสามารถกลับมาเปิดรับงานได้ตามปกติ",
                    link_url='/dashboard/',
                    notification_type='SYSTEM'
                )

            note_entry = f"[ปลดระงับบัญชีเมื่อ {now_str}]"
            report.admin_notes = f"{note_entry}\n{report.admin_notes}" if report.admin_notes else note_entry
            report.save()

            messages.success(request, f"ปลดระงับบัญชีช่าง {target_worker.user.full_name if target_worker else ''} สำเร็จ")

        elif action == 'DISMISS':
            # 4. ยกเลิกรายงานปัญหา (ไม่พบความผิด)
            report.status = 'DISMISSED'
            if admin_notes:
                note_entry = f"[ยกเลิกรายงานเมื่อ {now_str}]: {admin_notes}"
                report.admin_notes = f"{note_entry}\n{report.admin_notes}" if report.admin_notes else note_entry
            report.save()
            messages.info(request, f"ยกเลิกรายงานปัญหา #{report.id} เรียบร้อยแล้ว")

        else:
            # 5. จัดการทั่วไป (RESOLVE หรืออัปเดตสถานะพร้อมบันทึก)
            new_status = request.POST.get('status', 'RESOLVED')
            warning_msg = request.POST.get('warning_message', '').strip()
            suspend_worker = request.POST.get('suspend_worker') == '1'

            if suspend_worker and target_worker:
                target_worker.status = 'SUSPENDED'
                target_worker.is_available = False
                target_worker.rejection_reason = admin_notes or f"ถูกระงับตามรายงาน #{report.id}"
                target_worker.save()

                Notification.objects.create(
                    recipient=target_worker.user,
                    sender=request.user,
                    title="🚫 บัญชีช่างของคุณถูกระงับการใช้งานชั่วคราว",
                    message=f"บัญชีของคุณถูกระงับเนื่องจาก: {target_worker.rejection_reason}",
                    link_url='/dashboard/',
                    notification_type='SYSTEM'
                )

            if warning_msg and target_user:
                Notification.objects.create(
                    recipient=target_user,
                    sender=request.user,
                    title="⚠️ แจ้งเตือนข้อควรระวังจากผู้ดูแลระบบ",
                    message=warning_msg,
                    link_url='/dashboard/',
                    notification_type='SYSTEM'
                )

            if new_status in ['PENDING', 'RESOLVED', 'DISMISSED']:
                report.status = new_status

            if admin_notes:
                note_entry = f"[บันทึกเมื่อ {now_str}]: {admin_notes}"
                report.admin_notes = f"{note_entry}\n{report.admin_notes}" if report.admin_notes else note_entry

            report.save()
            messages.success(request, f"บันทึกการดำเนินการรายงาน #{report.id} เรียบร้อยแล้ว")

    return redirect('dashboard:admin_reports')
