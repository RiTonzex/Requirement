from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.core.files.storage import default_storage
from django.utils import timezone
from .models import ServiceRequest
from workers.models import WorkerProfile
from core.models import Category, Notification
from reviews.models import Review
from core.mongodb import (
    get_mongo_db,
    send_chat_message,
    get_chat_messages,
    mark_chat_messages_as_read
)


@login_required
def create_booking_view(request, worker_id):
    worker = get_object_or_404(WorkerProfile, id=worker_id)

    if request.user.is_worker:
        messages.error(request, "บัญชีช่างไม่สามารถส่งคำขอรับบริการได้ กรุณาใช้บัญชีลูกค้าสำหรับการจองงาน")
        return redirect('workers:detail', worker_id=worker.id)

    if request.user == worker.user:
        messages.error(request, "คุณไม่สามารถส่งคำขอรับบริการถึงตัวเองได้")
        return redirect('workers:detail', worker_id=worker.id)

    if request.method == 'POST':
        category_ids = request.POST.getlist('category_ids')
        if not category_ids:
            single_cat = request.POST.get('category_id')
            if single_cat:
                category_ids = [single_cat]

        details = request.POST.get('details', '').strip()
        address_note = request.POST.get('address_note', '').strip()
        preferred_date = request.POST.get('preferred_date')
        preferred_time_slot = request.POST.get('preferred_time_slot', 'ANY')

        if not category_ids or not details:
            messages.error(request, "กรุณาเลือกประเภทงานอย่างน้อย 1 ประเภท และกรอกรายละเอียดให้ครบถ้วน")
            return redirect('workers:detail', worker_id=worker.id)

        selected_categories = list(Category.objects.filter(id__in=category_ids))
        if not selected_categories:
            messages.error(request, "ไม่พบประเภทงานที่เลือก")
            return redirect('workers:detail', worker_id=worker.id)

        primary_category = selected_categories[0]

        req = ServiceRequest(
            customer=request.user,
            worker=worker,
            category=primary_category,
            details=details,
            address_note=address_note,
            preferred_date=preferred_date if preferred_date else None,
            preferred_time_slot=preferred_time_slot,
            status='REQUESTED'
        )

        if 'problem_image' in request.FILES:
            req.problem_image = request.FILES['problem_image']

        req.save()
        req.categories.set(selected_categories)

        # 1. Create In-App Notification to Worker
        cats_label = ", ".join([c.category_name for c in selected_categories])
        Notification.objects.create(
            recipient=worker.user,
            sender=request.user,
            title="มีคำขอรับบริการใหม่เข้ามา!",
            message=f"คุณ {request.user.full_name} ส่งคำขอรับบริการ '{cats_label}' ถึงคุณ",
            link_url=reverse('bookings:detail', kwargs={'booking_id': req.id}),
            notification_type='BOOKING'
        )

        # 2. Record Audit Log in MongoDB
        try:
            db = get_mongo_db()
            db.activity_audit_logs.insert_one({
                'event_type': 'BOOKING_CREATED',
                'booking_id': req.id,
                'customer_id': request.user.id,
                'customer_name': request.user.full_name,
                'worker_id': worker.id,
                'worker_name': worker.user.full_name,
                'category': category.category_name,
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'timestamp_dt': timezone.now(),
            })
        except Exception:
            pass

        messages.success(request, f"ส่งคำขอรับบริการถึงช่าง {worker.user.full_name} สำเร็จแล้ว!")
        return redirect('bookings:detail', booking_id=req.id)

    return redirect('workers:detail', worker_id=worker.id)


@login_required
def booking_detail_view(request, booking_id):
    booking = get_object_or_404(
        ServiceRequest.objects.select_related('customer', 'worker__user', 'category'),
        id=booking_id
    )

    is_customer = request.user == booking.customer
    is_worker = request.user == booking.worker.user
    is_admin = request.user.is_admin_user

    if not (is_customer or is_worker or is_admin):
        messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงข้อมูลคำขอนี้")
        return redirect('core:home')

    # Check if review already exists
    existing_review = Review.objects.filter(request=booking).first()

    # 5-Step Visual Progress Stepper
    has_review = bool(existing_review)
    is_paid = booking.payment_status == 'PAID'
    is_completed = booking.status == 'COMPLETED'

    status_steps = [
        {'step': 1, 'label': 'ส่งคำขอ', 'icon': 'fa-paper-plane', 'done': booking.status != 'REQUESTED' and booking.status != 'CANCELLED', 'active': booking.status == 'REQUESTED'},
        {'step': 2, 'label': 'ช่างตอบรับ', 'icon': 'fa-handshake', 'done': booking.status in ['IN_PROGRESS', 'COMPLETED'], 'active': booking.status == 'ACCEPTED'},
        {'step': 3, 'label': 'เข้าซ่อมแซม', 'icon': 'fa-screwdriver-wrench', 'done': is_completed, 'active': booking.status == 'IN_PROGRESS'},
        {'step': 4, 'label': 'ส่งมอบ & ชำระเงิน', 'icon': 'fa-qrcode', 'done': is_paid, 'active': is_completed and not is_paid},
        {'step': 5, 'label': 'รีวิวผลงาน', 'icon': 'fa-star', 'done': has_review, 'active': is_completed and is_paid and not has_review},
    ]

    # Chat summary
    chat_messages = get_chat_messages(booking.id)

    context = {
        'booking': booking,
        'is_customer': is_customer,
        'is_worker': is_worker,
        'is_admin': is_admin,
        'existing_review': existing_review,
        'status_steps': status_steps,
        'chat_messages_count': len(chat_messages),
    }
    return render(request, 'bookings/booking_detail.html', context)


@login_required
def update_booking_status_view(request, booking_id):
    booking = get_object_or_404(ServiceRequest, id=booking_id)

    is_worker = request.user == booking.worker.user
    is_customer = request.user == booking.customer
    is_admin = request.user.is_admin_user

    if not (is_worker or is_customer or is_admin):
        messages.error(request, "คุณไม่มีสิทธิ์ในการแก้ไขสถานะคำขอนี้")
        return redirect('core:home')

    new_status = request.POST.get('status')
    valid_statuses = [choice[0] for choice in ServiceRequest.STATUS_CHOICES]

    # อนุญาตให้เฉพาะช่างผู้รับงานเท่านั้นที่สามารถกด ตอบรับงาน, เริ่มปฏิบัติงาน, หรือแจ้งงานเสร็จสิ้น
    if new_status in ['ACCEPTED', 'IN_PROGRESS', 'COMPLETED'] and not is_worker:
        messages.error(request, "สิทธิ์ในการตอบรับและดำเนินงานนี้เป็นของช่างผู้รับงานเท่านั้น")
        return redirect('bookings:detail', booking_id=booking.id)

    if new_status in valid_statuses:
        old_status_display = booking.get_status_display()
        booking.status = new_status

        # If marking as completed, handle completion photo and warranty
        if new_status == 'COMPLETED':
            if 'completion_image' in request.FILES:
                booking.completion_image = request.FILES['completion_image']
            if request.POST.get('completion_note'):
                booking.completion_note = request.POST.get('completion_note').strip()

            w_days = booking.warranty_days or (booking.worker.warranty_days if booking.worker else 30)
            booking.warranty_days = w_days
            booking.warranty_expires_at = timezone.now().date() + timedelta(days=w_days)

        booking.save()

        # Send Notification to other party
        target_user = booking.customer if is_worker else booking.worker.user
        Notification.objects.create(
            recipient=target_user,
            sender=request.user,
            title=f"สถานะงาน #{booking.id} มีการเปลี่ยนแปลง",
            message=f"สถานะงานของคุณถูกเปลี่ยนเป็น '{booking.get_status_display()}' โดย {request.user.full_name}",
            link_url=reverse('bookings:detail', kwargs={'booking_id': booking.id}),
            notification_type='STATUS'
        )

        # Record in MongoDB Audit Log
        try:
            db = get_mongo_db()
            db.activity_audit_logs.insert_one({
                'event_type': 'STATUS_CHANGED',
                'booking_id': booking.id,
                'changed_by': request.user.full_name,
                'old_status': old_status_display,
                'new_status': booking.get_status_display(),
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'timestamp_dt': timezone.now(),
            })
        except Exception:
            pass

        messages.success(request, f"อัปเดตสถานะคำขอ #{booking.id} เป็น '{booking.get_status_display()}' เรียบร้อยแล้ว")
    else:
        messages.error(request, "สถานะที่เลือกไม่ถูกต้อง")

    return redirect('bookings:detail', booking_id=booking.id)


@login_required
def update_booking_price_view(request, booking_id):
    """
    อนุญาตให้ช่าง (หรือแอดมิน) ปรับแก้ไขเรทราคาค่าบริการระหว่างดำเนินการได้
    เพื่อความยืดหยุ่น เช่น มีค่าอะไหล่เพิ่ม หรือลดราคาพิเศษตามที่ตกลงกับลูกค้า
    """
    booking = get_object_or_404(
        ServiceRequest.objects.select_related('customer', 'worker__user', 'category'),
        id=booking_id
    )

    is_worker = request.user == booking.worker.user
    is_admin = request.user.is_admin_user

    if not (is_worker or is_admin):
        messages.error(request, "เฉพาะช่างผู้รับงานหรือผู้ดูแลระบบเท่านั้นที่สามารถแก้ไขเรทราคาได้")
        return redirect('bookings:detail', booking_id=booking.id)

    if request.method == 'POST':
        raw_price = request.POST.get('agreed_price', '').strip()
        price_note = request.POST.get('price_note', '').strip()

        try:
            new_price = float(raw_price)
            if new_price < 0:
                raise ValueError("ราคาต้องไม่ติดลบ")
        except (ValueError, TypeError):
            messages.error(request, "กรุณากรอกจำนวนเงินราคาที่ถูกต้อง (ตัวเลขมากกว่าหรือเท่ากับ 0)")
            return redirect('bookings:detail', booking_id=booking.id)

        booking.agreed_price = new_price
        booking.price_note = price_note
        booking.save()

        # Send notification to customer
        Notification.objects.create(
            recipient=booking.customer,
            sender=request.user,
            title=f"ช่างได้ปรับปรุงเรทราคาค่าบริการงาน #{booking.id}",
            message=f"ช่าง {booking.worker.user.full_name} ได้ปรับเรทราคาเป็น ฿{new_price:,.2f} บาท" + (f" (หมายเหตุ: {price_note})" if price_note else ""),
            link_url=reverse('bookings:detail', kwargs={'booking_id': booking.id}),
            notification_type='STATUS'
        )

        messages.success(request, f"ปรับปรุงเรทราคาค่าบริการเป็น ฿{new_price:,.2f} บาท เรียบร้อยแล้ว")

    return redirect('bookings:detail', booking_id=booking.id)


@login_required
def chat_view(request, booking_id):
    booking = get_object_or_404(
        ServiceRequest.objects.select_related('customer', 'worker__user', 'category'),
        id=booking_id
    )

    is_customer = request.user == booking.customer
    is_worker = request.user == booking.worker.user
    is_admin = request.user.is_admin_user

    if not (is_customer or is_worker or is_admin):
        messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงห้องสนทนานี้")
        return redirect('core:home')

    # Mark unread messages as read
    mark_chat_messages_as_read(booking.id, request.user.id)

    # Fetch chat history from MongoDB
    messages_list = get_chat_messages(booking.id)

    context = {
        'booking': booking,
        'is_customer': is_customer,
        'is_worker': is_worker,
        'other_user': booking.worker.user if is_customer else booking.customer,
        'messages_list': messages_list,
    }
    return render(request, 'bookings/chat.html', context)


@login_required
def send_chat_message_api(request, booking_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    booking = get_object_or_404(ServiceRequest, id=booking_id)

    is_customer = request.user == booking.customer
    is_worker = request.user == booking.worker.user
    is_admin = request.user.is_admin_user

    if not (is_customer or is_worker or is_admin):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)

    msg_text = request.POST.get('message', '').strip()
    image_url = None

    if 'image' in request.FILES:
        img_file = request.FILES['image']
        saved_path = default_storage.save(f"chat/{booking.id}_{img_file.name}", img_file)
        image_url = default_storage.url(saved_path)

    if not msg_text and not image_url:
        return JsonResponse({'status': 'error', 'message': 'Empty message'}, status=400)

    ok, res = send_chat_message(
        booking_id=booking.id,
        sender_user=request.user,
        message_text=msg_text,
        image_url=image_url
    )

    if ok:
        # Notify other user if they are not actively on chat
        target_user = booking.worker.user if is_customer else booking.customer
        Notification.objects.create(
            recipient=target_user,
            sender=request.user,
            title=f"ข้อความใหม่จาก {request.user.full_name}",
            message=msg_text[:60] if msg_text else "ส่งรูปภาพ",
            link_url=reverse('bookings:chat', kwargs={'booking_id': booking.id}),
            notification_type='SYSTEM'
        )

        return JsonResponse({'status': 'success', 'message': res})
    return JsonResponse({'status': 'error', 'message': str(res)}, status=500)


@login_required
def invoice_view(request, booking_id):
    booking = get_object_or_404(
        ServiceRequest.objects.select_related('customer', 'worker__user', 'category'),
        id=booking_id
    )

    is_customer = request.user == booking.customer
    is_worker = request.user == booking.worker.user
    is_admin = request.user.is_admin_user

    if not (is_customer or is_worker or is_admin):
        messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงเอกสารนี้")
        return redirect('core:home')

    # Get final agreed price or service starting price for calculation
    unit_price = float(booking.final_price)
    price_unit = booking.service_price_unit

    # Invoice metadata
    invoice_number = f"INV-{booking.created_at.strftime('%Y%m%d')}-{booking.id:04d}"
    warranty_until = booking.updated_at + timezone.timedelta(days=30)

    context = {
        'booking': booking,
        'invoice_number': invoice_number,
        'unit_price': unit_price,
        'price_unit': price_unit,
        'price_note': booking.price_note,
        'warranty_until': warranty_until,
        'today': timezone.now(),
        'is_customer': is_customer,
        'is_worker': is_worker,
    }
    return render(request, 'bookings/invoice.html', context)


@login_required
def upload_payment_slip_view(request, booking_id):
    """ลูกค้าอัปโหลดสลิปการโอนเงินเพื่อยืนยันการชำระเงิน"""
    booking = get_object_or_404(ServiceRequest, id=booking_id)

    if request.user != booking.customer and not request.user.is_admin_user:
        messages.error(request, "เฉพาะลูกค้าผู้ว่าจ้างเท่านั้นที่สามารถอัปโหลดสลิปได้")
        return redirect('bookings:detail', booking_id=booking.id)

    if request.method == 'POST' and 'payment_slip' in request.FILES:
        booking.payment_slip = request.FILES['payment_slip']
        booking.payment_status = 'SLIP_UPLOADED'
        booking.save()

        # แจ้งเตือนช่าง
        Notification.objects.create(
            recipient=booking.worker.user,
            sender=request.user,
            title=f"ลูกค้าได้อัปโหลดสลิปโอนเงินงาน #{booking.id}",
            message=f"คุณ {request.user.full_name} ได้แนบสลิปชำระเงินเรียบร้อยแล้ว กรุณาตรวจสอบและกดยืนยันการรับเงิน",
            link_url=reverse('bookings:detail', kwargs={'booking_id': booking.id}),
            notification_type='STATUS'
        )

        messages.success(request, "อัปโหลดสลิปการโอนเงินสำเร็จแล้ว! ระบบส่งแจ้งเตือนให้ช่างตรวจสอบยอดเงินเรียบร้อยครับ")
    else:
        messages.error(request, "กรุณาเลือกไฟล์สลิปการโอนเงิน (JPG/PNG)")

    return redirect('bookings:detail', booking_id=booking.id)


@login_required
def confirm_payment_view(request, booking_id):
    """ช่างหรือแอดมินกดยืนยันการรับชำระเงิน"""
    booking = get_object_or_404(ServiceRequest, id=booking_id)

    if request.user != booking.worker.user and not request.user.is_admin_user:
        messages.error(request, "เฉพาะช่างผู้รับงานหรือผู้ดูแลระบบเท่านั้นที่สามารถยืนยันการรับเงินได้")
        return redirect('bookings:detail', booking_id=booking.id)

    if request.method == 'POST':
        booking.payment_status = 'PAID'
        booking.paid_at = timezone.now()

        # ตั้งค่าวันหมดอายุการรับประกัน
        w_days = booking.warranty_days or (booking.worker.warranty_days if booking.worker else 30)
        booking.warranty_days = w_days
        booking.warranty_expires_at = timezone.now().date() + timedelta(days=w_days)
        booking.save()

        # แจ้งเตือนลูกค้า
        Notification.objects.create(
            recipient=booking.customer,
            sender=request.user,
            title=f"ช่างยืนยันการรับชำระเงินงาน #{booking.id} แล้ว",
            message=f"ช่าง {booking.worker.user.full_name} ยืนยันการรับชำระเงินเรียบร้อยแล้ว ขอบคุณที่ไว้วางใจใช้บริการครับ",
            link_url=reverse('bookings:detail', kwargs={'booking_id': booking.id}),
            notification_type='STATUS'
        )

        messages.success(request, f"ยืนยันการรับชำระเงินสำหรับคำขอ #{booking.id} เรียบร้อยแล้ว (สถานะ: ชำระแล้ว)")

    return redirect('bookings:detail', booking_id=booking.id)


@login_required
def sync_to_portfolio_view(request, booking_id):
    """ช่างกดนำภาพผลงานหลังซ่อมไปโชว์ใน Portfolio หน้าโปรไฟล์สาธารณะ"""
    booking = get_object_or_404(ServiceRequest, id=booking_id)

    if request.user != booking.worker.user and not request.user.is_admin_user:
        messages.error(request, "เฉพาะช่างเท่านั้นที่สามารถบันทึกผลงานเข้า Portfolio ได้")
        return redirect('bookings:detail', booking_id=booking.id)

    title = request.POST.get('title', f"ผลงาน {booking.all_categories_display} (งาน #{booking.id})")
    description = request.POST.get('description', booking.completion_note or booking.details)

    try:
        db = get_mongo_db()
        image_url = booking.display_completion_image_url
        before_url = booking.display_problem_image_url

        db.portfolios.insert_one({
            'worker_id': booking.worker.id,
            'title': title,
            'description': description,
            'category_id': booking.category.id if booking.category else None,
            'category_name': booking.all_categories_display,
            'before_image_url': before_url,
            'image_url': image_url,
            'booking_id': booking.id,
            'created_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'created_at_dt': timezone.now(),
        })
        messages.success(request, "บันทึกภาพผลงาน Before & After เข้า Portfolio หน้าโปรไฟล์ของคุณเรียบร้อยแล้ว!")
    except Exception as e:
        messages.error(request, f"เกิดข้อผิดพลาดในการบันทึกเข้า Portfolio: {e}")

    return redirect('bookings:detail', booking_id=booking.id)


@login_required
def chat_rooms_view(request):
    """หน้ารวมห้องสนทนาทั้งหมดของผู้ใช้ (ทั้งลูกค้าและช่าง)"""
    if request.user.is_worker and hasattr(request.user, 'worker_profile'):
        bookings = ServiceRequest.objects.filter(worker=request.user.worker_profile)
    else:
        bookings = ServiceRequest.objects.filter(customer=request.user)

    bookings = bookings.select_related('customer', 'worker__user', 'category').order_by('-created_at')

    # รวมข้อมูลห้องแชท
    chat_rooms = []
    for b in bookings:
        other = b.customer if (request.user.is_worker and hasattr(request.user, 'worker_profile') and b.worker.user == request.user) else b.worker.user
        chat_rooms.append({
            'booking': b,
            'other_user': other,
        })

    return render(request, 'bookings/chat_rooms.html', {
        'chat_rooms': chat_rooms,
    })
