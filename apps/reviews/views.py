from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Review
from workers.models import WorkerProfile
from bookings.models import ServiceRequest


@login_required
def create_review_view(request, worker_id):
    worker = get_object_or_404(WorkerProfile, id=worker_id)

    if request.user == worker.user:
        messages.error(request, "คุณไม่สามารถรีวิวตนเองได้")
        return redirect('workers:detail', worker_id=worker.id)

    if request.method == 'POST':
        rating_val = request.POST.get('rating', '5')
        comment = request.POST.get('comment', '').strip()
        request_id = request.POST.get('request_id')

        try:
            rating = int(rating_val)
            rating = max(1, min(5, rating))
        except ValueError:
            rating = 5

        service_req = None
        if request_id and request_id.isdigit():
            service_req = ServiceRequest.objects.filter(id=request_id, customer=request.user, worker=worker).first()

        Review.objects.create(
            worker=worker,
            customer=request.user,
            request=service_req,
            rating=rating,
            comment=comment
        )

        messages.success(request, f"ส่งรีวิวและให้คะแนน {rating} ดาวเรียบร้อยแล้ว ขอบคุณสำหรับความคิดเห็นครับ!")
        return redirect('workers:detail', worker_id=worker.id)

    return redirect('workers:detail', worker_id=worker.id)


@login_required
def reply_review_view(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if request.user != review.worker.user and not request.user.is_admin_user:
        messages.error(request, "คุณไม่มีสิทธิ์ตอบกลับรีวิวนี้")
        return redirect('workers:detail', worker_id=review.worker.id)

    if request.method == 'POST':
        reply_text = request.POST.get('worker_reply', '').strip()
        review.worker_reply = reply_text
        review.worker_replied_at = timezone.now()
        review.save()

        messages.success(request, "ส่งคำตอบกลับรีวิวเรียบร้อยแล้ว")

    return redirect('dashboard:worker_dashboard')


@login_required
def toggle_review_hidden_view(request, review_id):
    if not request.user.is_admin_user:
        messages.error(request, "สิทธิ์เฉพาะผู้ดูแลระบบเท่านั้น")
        return redirect('core:home')

    review = get_object_or_404(Review, id=review_id)
    review.is_hidden = not review.is_hidden
    review.save()

    status_str = "ซ่อนรีวิว" if review.is_hidden else "แสดงรีวิว"
    messages.success(request, f"เปลี่ยนสถานะรีวิว #{review.id} เป็น '{status_str}' เรียบร้อยแล้ว")
    return redirect('dashboard:admin_reviews')
