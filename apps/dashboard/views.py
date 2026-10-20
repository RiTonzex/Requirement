import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg, Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth import get_user_model
from workers.models import WorkerProfile, SavedWorker
from bookings.models import ServiceRequest
from reviews.models import Review
from reports.models import Report
from core.models import Category, Province, SearchLog, Notification
from core.mongodb import get_worker_portfolio
from core.cloudinary_utils import delete_cloudinary_asset

User = get_user_model()


# ==========================================
# 1. Customer Dashboard
# ==========================================
@login_required
def customer_dashboard(request):
    bookings = ServiceRequest.objects.filter(customer=request.user).select_related(
        'worker__user', 'category'
    ).order_by('-created_at')

    saved_workers = SavedWorker.objects.filter(customer=request.user).select_related(
        'worker__user'
    ).prefetch_related('worker__services__category')

    my_reviews = Review.objects.filter(customer=request.user).select_related('worker__user')

    context = {
        'bookings': bookings,
        'saved_workers': saved_workers,
        'my_reviews': my_reviews,
        'pending_bookings_count': bookings.filter(status='REQUESTED').count(),
        'in_progress_bookings_count': bookings.filter(status__in=['ACCEPTED', 'IN_PROGRESS']).count(),
        'completed_bookings_count': bookings.filter(status='COMPLETED').count(),
    }
    return render(request, 'dashboard/customer_dashboard.html', context)


# ==========================================
# 2. Worker Dashboard
# ==========================================
@login_required
def worker_dashboard(request):
    if not request.user.is_worker:
        messages.error(request, "สิทธิ์เฉพาะช่างรับจ้างเท่านั้น")
        return redirect('core:home')

    worker, _ = WorkerProfile.objects.get_or_create(user=request.user)

    bookings = ServiceRequest.objects.filter(worker=worker).select_related(
        'customer', 'category'
    ).order_by('-created_at')

    reviews = Review.objects.filter(worker=worker).select_related('customer').order_by('-created_at')
    portfolio_items = get_worker_portfolio(worker.id)

    # Monthly performance chart data (last 6 months)
    month_labels = []
    month_jobs = []
    month_revenues = []
    now = timezone.now()

    for i in range(5, -1, -1):
        # Calculate month date window
        month_dt = now - timezone.timedelta(days=i * 30)
        label = month_dt.strftime('%b %Y')
        month_labels.append(label)

        # Count completed bookings in that month
        completed_in_month = bookings.filter(
            status='COMPLETED',
            created_at__year=month_dt.year,
            created_at__month=month_dt.month
        )
        job_count = completed_in_month.count()
        month_jobs.append(job_count)
        # Approximate revenue: jobs * 650
        month_revenues.append(job_count * 650)

    # Rating distribution
    rating_counts = [
        reviews.filter(rating=5).count(),
        reviews.filter(rating=4).count(),
        reviews.filter(rating=3).count(),
        reviews.filter(rating=2).count(),
        reviews.filter(rating=1).count(),
    ]

    context = {
        'worker': worker,
        'bookings': bookings,
        'reviews': reviews,
        'portfolio_items': portfolio_items,
        'requested_count': bookings.filter(status='REQUESTED').count(),
        'in_progress_count': bookings.filter(status__in=['ACCEPTED', 'IN_PROGRESS']).count(),
        'completed_count': bookings.filter(status='COMPLETED').count(),
        'unreplied_reviews_count': reviews.filter(worker_reply__isnull=True).count(),
        'chart_month_labels': json.dumps(month_labels),
        'chart_month_jobs': json.dumps(month_jobs),
        'chart_month_revenues': json.dumps(month_revenues),
        'chart_rating_counts': json.dumps(rating_counts),
    }
    return render(request, 'dashboard/worker_dashboard.html', context)


# ==========================================
# 3. Admin Dashboard & Sub-modules
# ==========================================
@login_required
def admin_dashboard(request):
    if not request.user.is_admin_user:
        messages.error(request, "สิทธิ์เฉพาะผู้ดูแลระบบเท่านั้น")
        return redirect('core:home')

    total_users = User.objects.count()
    total_customers = User.objects.filter(role='CUSTOMER').count()
    total_workers = WorkerProfile.objects.count()
    approved_workers = WorkerProfile.objects.filter(status='APPROVED').count()
    pending_workers = WorkerProfile.objects.filter(status='PENDING').count()
    verified_workers = WorkerProfile.objects.filter(is_id_verified=True).count()
    
    total_requests = ServiceRequest.objects.count()
    completed_requests = ServiceRequest.objects.filter(status='COMPLETED').count()
    pending_reports = Report.objects.filter(status='PENDING').count()
    total_reviews = Review.objects.count()

    recent_pending_workers = WorkerProfile.objects.filter(status='PENDING').select_related('user')[:5]
    recent_reports = Report.objects.filter(status='PENDING').select_related('reporter', 'reported_worker__user')[:5]
    recent_requests = ServiceRequest.objects.select_related('customer', 'worker__user', 'category').order_by('-created_at')[:6]

    # Analytics charts data
    now = timezone.now()
    trend_labels = []
    trend_data = []

    for i in range(5, -1, -1):
        month_dt = now - timezone.timedelta(days=i * 30)
        label = month_dt.strftime('%b %Y')
        trend_labels.append(label)
        count = ServiceRequest.objects.filter(created_at__year=month_dt.year, created_at__month=month_dt.month).count()
        trend_data.append(count)

    # Categories breakdown
    cat_qs = Category.objects.annotate(count=Count('service_requests')).order_by('-count')[:6]
    cat_labels = [c.category_name for c in cat_qs]
    cat_counts = [c.count for c in cat_qs]

    # Status breakdown
    status_dict = {'REQUESTED': 0, 'ACCEPTED': 0, 'IN_PROGRESS': 0, 'COMPLETED': 0, 'CANCELLED': 0}
    for item in ServiceRequest.objects.values('status').annotate(c=Count('id')):
        if item['status'] in status_dict:
            status_dict[item['status']] = item['c']

    context = {
        'total_users': total_users,
        'total_customers': total_customers,
        'total_workers': total_workers,
        'approved_workers': approved_workers,
        'pending_workers': pending_workers,
        'verified_workers': verified_workers,
        'total_requests': total_requests,
        'completed_requests': completed_requests,
        'pending_reports': pending_reports,
        'total_reviews': total_reviews,
        'recent_pending_workers': recent_pending_workers,
        'recent_reports': recent_reports,
        'recent_requests': recent_requests,
        'chart_trend_labels': json.dumps(trend_labels),
        'chart_trend_data': json.dumps(trend_data),
        'chart_cat_labels': json.dumps(cat_labels),
        'chart_cat_counts': json.dumps(cat_counts),
        'chart_status_counts': json.dumps(list(status_dict.values())),
    }
    return render(request, 'dashboard/admin/dashboard.html', context)


@login_required
def admin_workers_list(request):
    if not request.user.is_admin_user:
        messages.error(request, "สิทธิ์เฉพาะผู้ดูแลระบบเท่านั้น")
        return redirect('core:home')

    status_filter = request.GET.get('status', 'ALL')
    search_q = request.GET.get('q', '').strip()

    workers = WorkerProfile.objects.select_related('user').prefetch_related('services__category', 'service_areas__province')

    if status_filter != 'ALL':
        workers = workers.filter(status=status_filter)

    if search_q:
        workers = workers.filter(
            Q(user__first_name__icontains=search_q) |
            Q(user__last_name__icontains=search_q) |
            Q(user__email__icontains=search_q) |
            Q(user__phone_number__icontains=search_q)
        )

    workers = workers.order_by('-id')

    if request.method == 'POST':
        worker_id = request.POST.get('worker_id')
        action = request.POST.get('action')
        rejection_reason = request.POST.get('rejection_reason', '').strip()

        target_worker = get_object_or_404(WorkerProfile, id=worker_id)

        if action == 'APPROVE':
            target_worker.status = 'APPROVED'
            target_worker.approved_by = request.user
            target_worker.approved_at = timezone.now()
            target_worker.rejection_reason = None
            target_worker.save()

            Notification.objects.create(
                recipient=target_worker.user,
                sender=request.user,
                title="ยินดีด้วย! บัญชีช่างของคุณได้รับการอนุมัติแล้ว",
                message="โปรไฟล์ของคุณผ่านการตรวจสอบและแสดงในผลการค้นหาช่างใกล้บ้านเรียบร้อยแล้ว",
                link_url='/dashboard/',
                notification_type='KYC'
            )
            messages.success(request, f"อนุมัติช่าง {target_worker.user.full_name} เรียบร้อยแล้ว")

        elif action == 'REJECT':
            target_worker.status = 'REJECTED'
            target_worker.rejection_reason = rejection_reason
            target_worker.save()

            Notification.objects.create(
                recipient=target_worker.user,
                sender=request.user,
                title="ผลการตรวจสอบโปรไฟล์ช่าง",
                message=f"โปรไฟล์ของคุณยังไม่ผ่านการอนุมัติ: {rejection_reason}",
                link_url='/workers/edit-profile/',
                notification_type='KYC'
            )
            messages.warning(request, f"ปฏิเสธคำขอของช่าง {target_worker.user.full_name} แล้ว")

        elif action == 'VERIFY_KYC':
            target_worker.is_id_verified = True
            target_worker.save()

            Notification.objects.create(
                recipient=target_worker.user,
                sender=request.user,
                title="การยืนยันตัวตนสำเร็จ (Verified Badge)",
                message="เอกสารของคุณผ่านการตรวจสอบ คุณได้รับตราสัญลักษณ์ 'ช่างยืนยันตัวตนแล้ว' เรียบร้อย",
                link_url='/dashboard/',
                notification_type='KYC'
            )
            messages.success(request, f"ให้ตรา Verified Badge แก่ช่าง {target_worker.user.full_name} เรียบร้อย")

        elif action == 'UNVERIFY_KYC':
            target_worker.is_id_verified = False
            target_worker.save()
            messages.info(request, f"ยกเลิกตรา Verified Badge ของช่าง {target_worker.user.full_name} แล้ว")

        elif action == 'WARN':
            warning_msg = request.POST.get('warning_message', '').strip()
            if not warning_msg:
                warning_msg = "ผู้ดูแลระบบขอแจ้งเตือนเรื่องพฤติกรรมหรือข้อร้องเรียนการให้บริการ กรุณาปฏิบัติตามมาตรฐานชุมชนอย่างเคร่งครัด"
            Notification.objects.create(
                recipient=target_worker.user,
                sender=request.user,
                title="⚠️ ประกาศแจ้งเตือนจากผู้ดูแลระบบ",
                message=warning_msg,
                link_url='/dashboard/',
                notification_type='SYSTEM'
            )
            messages.warning(request, f"ส่งข้อความเตือนไปยังช่าง {target_worker.user.full_name} เรียบร้อยแล้ว")

        elif action == 'SUSPEND':
            suspend_reason = request.POST.get('suspend_reason', '').strip()
            if not suspend_reason:
                suspend_reason = "ถูกระงับการใช้งานเนื่องจากตรวจพบพฤติกรรมไม่เหมาะสมหรือมีข้อร้องเรียนจากผู้ใช้"
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
            messages.error(request, f"ระงับการใช้งานช่าง {target_worker.user.full_name} และส่งข้อความแจ้งเตือนเรียบร้อยแล้ว")

        elif action == 'RESTORE':
            target_worker.status = 'APPROVED'
            target_worker.save()

            Notification.objects.create(
                recipient=target_worker.user,
                sender=request.user,
                title="✅ บัญชีช่างของคุณได้รับการเปิดใช้งานอีกครั้ง",
                message="ผู้ดูแลระบบได้ทำการปลดระงับบัญชีของคุณเรียบร้อยแล้ว คุณสามารถกลับมารับงานได้ตามปกติ",
                link_url='/dashboard/',
                notification_type='SYSTEM'
            )
            messages.success(request, f"เปิดใช้งานช่าง {target_worker.user.full_name} อีกครั้ง และส่งแจ้งเตือนแล้ว")

        return redirect(request.META.get('HTTP_REFERER', 'dashboard:admin_workers'))

    context = {
        'workers': workers,
        'status_filter': status_filter,
        'search_q': search_q,
    }
    return render(request, 'dashboard/admin/workers.html', context)


@login_required
def admin_categories_list(request):
    if not request.user.is_admin_user:
        messages.error(request, "สิทธิ์เฉพาะผู้ดูแลระบบเท่านั้น")
        return redirect('core:home')

    categories = Category.objects.annotate(
        worker_count=Count('worker_services', distinct=True),
        job_count=Count('service_requests', distinct=True)
    ).order_by('category_name')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'ADD':
            name = request.POST.get('category_name', '').strip()
            icon = request.POST.get('icon', 'fa-wrench').strip()
            desc = request.POST.get('description', '').strip()
            if name:
                Category.objects.create(category_name=name, icon=icon, description=desc, is_active=True)
                messages.success(request, f"เพิ่มหมวดหมู่ '{name}' สำเร็จ")
        elif action == 'EDIT':
            cat_id = request.POST.get('category_id')
            category = get_object_or_404(Category, id=cat_id)
            category.category_name = request.POST.get('category_name', '').strip()
            category.icon = request.POST.get('icon', 'fa-wrench').strip()
            category.description = request.POST.get('description', '').strip()
            category.save()
            messages.success(request, f"แก้ไขหมวดหมู่ '{category.category_name}' สำเร็จ")
        elif action == 'TOGGLE':
            cat_id = request.POST.get('category_id')
            category = get_object_or_404(Category, id=cat_id)
            category.is_active = not category.is_active
            category.save()
            messages.info(request, f"เปลี่ยนสถานะหมวดหมู่ '{category.category_name}' สำเร็จ")

        return redirect('dashboard:admin_categories')

    return render(request, 'dashboard/admin/categories.html', {'categories': categories})


@login_required
def admin_users_list(request):
    if not request.user.is_admin_user:
        messages.error(request, "สิทธิ์เฉพาะผู้ดูแลระบบเท่านั้น")
        return redirect('core:home')

    role_filter = request.GET.get('role', 'ALL')
    search_q = request.GET.get('q', '').strip()

    users = User.objects.all().order_by('-created_at')

    if role_filter != 'ALL':
        users = users.filter(role=role_filter)

    if search_q:
        users = users.filter(
            Q(first_name__icontains=search_q) |
            Q(last_name__icontains=search_q) |
            Q(email__icontains=search_q) |
            Q(phone_number__icontains=search_q)
        )

    context = {
        'users': users,
        'role_filter': role_filter,
        'search_q': search_q,
    }
    return render(request, 'dashboard/admin/users.html', context)


@login_required
def admin_delete_user(request, user_id):
    if not request.user.is_admin_user:
        messages.error(request, "สิทธิ์เฉพาะผู้ดูแลระบบเท่านั้น")
        return redirect('core:home')

    if request.method == 'POST':
        target_user = get_object_or_404(User, id=user_id)

        if target_user.id == request.user.id:
            messages.error(request, "ไม่สามารถลบบัญชีของตนเองที่กำลังเข้าสู่ระบบอยู่ได้")
            return redirect('dashboard:admin_users')

        user_name = target_user.full_name
        user_email = target_user.email
        user_role = target_user.get_role_display()

        # ลบรูปภาพที่เกี่ยวข้องบน Cloudinary หากมี
        if target_user.avatar:
            try:
                delete_cloudinary_asset(target_user.avatar)
            except Exception:
                pass

        if hasattr(target_user, 'worker_profile'):
            wp = target_user.worker_profile
            for img_field in [wp.profile_image, wp.id_card_image, wp.certificate_image]:
                if img_field:
                    try:
                        delete_cloudinary_asset(img_field)
                    except Exception:
                        pass

        target_user.delete()
        messages.success(request, f"ลบบัญชีผู้ใช้ '{user_name}' ({user_email}) บทบาท: {user_role} เรียบร้อยแล้ว")
    else:
        messages.warning(request, "การลบบัญชีต้องส่งคำขอแบบ POST เท่านั้น")

    return redirect('dashboard:admin_users')


@login_required
def admin_reports_list(request):
    if not request.user.is_admin_user:
        messages.error(request, "สิทธิ์เฉพาะผู้ดูแลระบบเท่านั้น")
        return redirect('core:home')

    status_filter = request.GET.get('status', 'ALL')
    reports = Report.objects.select_related('reporter', 'reported_worker__user').order_by('-created_at')

    if status_filter != 'ALL':
        reports = reports.filter(status=status_filter)

    context = {
        'reports': reports,
        'status_filter': status_filter,
    }
    return render(request, 'dashboard/admin/reports.html', context)


@login_required
def admin_reviews_list(request):
    if not request.user.is_admin_user:
        messages.error(request, "สิทธิ์เฉพาะผู้ดูแลระบบเท่านั้น")
        return redirect('core:home')

    reviews = Review.objects.select_related('customer', 'worker__user').order_by('-created_at')

    context = {
        'reviews': reviews,
    }
    return render(request, 'dashboard/admin/reviews.html', context)


@login_required
def admin_stats_view(request):
    if not request.user.is_admin_user:
        messages.error(request, "สิทธิ์เฉพาะผู้ดูแลระบบเท่านั้น")
        return redirect('core:home')

    top_keywords = SearchLog.objects.exclude(keyword__isnull=True).exclude(keyword='').values('keyword').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    top_provinces = SearchLog.objects.exclude(province__isnull=True).values('province__province_name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    category_requests = Category.objects.annotate(
        req_count=Count('service_requests')
    ).order_by('-req_count')[:8]

    request_statuses = ServiceRequest.objects.values('status').annotate(count=Count('id'))

    context = {
        'top_keywords': top_keywords,
        'top_provinces': top_provinces,
        'category_requests': category_requests,
        'request_statuses': request_statuses,
    }
    return render(request, 'dashboard/admin/stats.html', context)
