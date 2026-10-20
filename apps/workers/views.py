from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.files.storage import default_storage
from django.db.models import Avg, Count, Q
from .models import WorkerProfile, WorkerService, WorkerServiceArea, SavedWorker
from core.models import Category, Province
from reviews.models import Review
from core.mongodb import get_worker_portfolio, add_worker_portfolio_item, delete_worker_portfolio_item


def worker_detail_view(request, worker_id):
    worker = get_object_or_404(
        WorkerProfile.objects.select_related('user').prefetch_related(
            'services__category', 'service_areas__province'
        ),
        id=worker_id
    )

    # Reviews
    reviews = worker.reviews.filter(is_hidden=False).select_related('customer').order_by('-created_at')

    # Rating Breakdown (1 to 5 stars count)
    rating_counts = {star: reviews.filter(rating=star).count() for star in range(5, 0, -1)}
    total_reviews = reviews.count()
    rating_percentages = {}
    for star, count in rating_counts.items():
        rating_percentages[star] = round((count / total_reviews * 100)) if total_reviews > 0 else 0

    is_saved = False
    if request.user.is_authenticated:
        is_saved = SavedWorker.objects.filter(customer=request.user, worker=worker).exists()

    # Fetch MongoDB Portfolio Gallery
    portfolio_items = get_worker_portfolio(worker.id)

    context = {
        'worker': worker,
        'reviews': reviews,
        'rating_counts': rating_counts,
        'rating_percentages': rating_percentages,
        'total_reviews': total_reviews,
        'is_saved': is_saved,
        'portfolio_items': portfolio_items,
    }
    return render(request, 'workers/worker_detail.html', context)


@login_required
def toggle_save_worker(request, worker_id):
    if request.user.is_worker:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
            return JsonResponse({'status': 'error', 'message': 'บัญชีช่างไม่สามารถกดบันทึกช่างได้'}, status=403)
        messages.error(request, "บัญชีช่างไม่สามารถกดบันทึกช่างได้")
        return redirect(request.META.get('HTTP_REFERER', 'core:home'))

    worker = get_object_or_404(WorkerProfile, id=worker_id)
    saved_obj, created = SavedWorker.objects.get_or_create(customer=request.user, worker=worker)

    if not created:
        saved_obj.delete()
        saved = False
        msg = f"ยกเลิกการบันทึกช่าง {worker.user.full_name} แล้ว"
    else:
        saved = True
        msg = f"บันทึกช่าง {worker.user.full_name} ไว้ในรายการที่ถูกใจแล้ว"

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({'status': 'success', 'saved': saved, 'message': msg})

    messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER', 'core:home'))


@login_required
def toggle_availability(request):
    if not request.user.is_worker:
        messages.error(request, "สิทธิ์เฉพาะช่างรับจ้างเท่านั้น")
        return redirect('core:home')

    worker = request.user.worker_profile
    worker.is_available = not worker.is_available
    worker.save()

    status_str = "พร้อมรับงาน" if worker.is_available else "พักการรับงานชั่วคราว"
    messages.success(request, f"เปลี่ยนสถานะเป็น '{status_str}' เรียบร้อยแล้ว")
    return redirect('dashboard:worker_dashboard')


@login_required
def edit_profile_view(request):
    if not request.user.is_worker:
        messages.error(request, "สิทธิ์เฉพาะช่างรับจ้างเท่านั้น")
        return redirect('core:home')

    worker, _ = WorkerProfile.objects.get_or_create(user=request.user)
    all_categories = Category.objects.filter(is_active=True)
    all_provinces = Province.objects.all()

    if request.method == 'POST':
        # Update Bio, Working hours, and User data
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.phone_number = request.POST.get('phone_number', '').strip()
        request.user.save()

        worker.bio = request.POST.get('bio', '').strip()
        worker.working_hours = request.POST.get('working_hours', 'จันทร์ - เสาร์ (08:30 - 18:00 น.)').strip()
        
        # Profile image update / delete
        if request.POST.get('delete_profile_image') == '1':
            if worker.profile_image:
                worker.profile_image.delete(save=False)
                worker.profile_image = None
        elif 'profile_image' in request.FILES:
            worker.profile_image = request.FILES['profile_image']

        # KYC document uploads / delete
        if request.POST.get('delete_id_card_image') == '1':
            if worker.id_card_image:
                worker.id_card_image.delete(save=False)
                worker.id_card_image = None
        elif 'id_card_image' in request.FILES:
            worker.id_card_image = request.FILES['id_card_image']

        if request.POST.get('delete_certificate_image') == '1':
            if worker.certificate_image:
                worker.certificate_image.delete(save=False)
                worker.certificate_image = None
        elif 'certificate_image' in request.FILES:
            worker.certificate_image = request.FILES['certificate_image']

        worker.save()


        # Update Services (Categories + Prices + Units)
        selected_category_ids = request.POST.getlist('categories')
        WorkerService.objects.filter(worker=worker).exclude(category_id__in=selected_category_ids).delete()
        for cat_id in selected_category_ids:
            price_key = f"price_{cat_id}"
            unit_key = f"unit_{cat_id}"
            price_val = request.POST.get(price_key, '0.00').strip()
            unit_val = request.POST.get(unit_key, '/งาน').strip()
            try:
                price = float(price_val)
            except ValueError:
                price = 0.00

            WorkerService.objects.update_or_create(
                worker=worker,
                category_id=cat_id,
                defaults={
                    'starting_price': max(0.00, price),
                    'price_unit': unit_val if unit_val else '/งาน'
                }
            )

        # Update Provinces
        selected_province_ids = request.POST.getlist('provinces')
        WorkerServiceArea.objects.filter(worker=worker).exclude(province_id__in=selected_province_ids).delete()
        for prov_id in selected_province_ids:
            WorkerServiceArea.objects.get_or_create(
                worker=worker,
                province_id=prov_id
            )

        messages.success(request, "บันทึกข้อมูลโปรไฟล์ช่างเรียบร้อยแล้ว")
        return redirect('dashboard:worker_dashboard')

    current_services = {ws.category_id: {'price': ws.starting_price, 'unit': ws.price_unit} for ws in worker.services.all()}
    current_provinces = set(worker.service_areas.values_list('province_id', flat=True))
    portfolio_items = get_worker_portfolio(worker.id)

    context = {
        'worker': worker,
        'all_categories': all_categories,
        'all_provinces': all_provinces,
        'current_services': current_services,
        'current_provinces': current_provinces,
        'portfolio_items': portfolio_items,
    }
    return render(request, 'workers/edit_profile.html', context)


@login_required
def add_portfolio_view(request):
    if not request.user.is_worker:
        messages.error(request, "สิทธิ์เฉพาะช่างรับจ้างเท่านั้น")
        return redirect('core:home')

    worker = request.user.worker_profile

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category_name = request.POST.get('category_name', 'งานทั่วไป').strip()

        before_path = None
        after_path = None

        if 'before_image' in request.FILES:
            b_file = request.FILES['before_image']
            b_saved = default_storage.save(f"workers/portfolios/{worker.id}_{b_file.name}", b_file)
            before_path = default_storage.url(b_saved)

        if 'after_image' in request.FILES:
            a_file = request.FILES['after_image']
            a_saved = default_storage.save(f"workers/portfolios/{worker.id}_{a_file.name}", a_file)
            after_path = default_storage.url(a_saved)

        if title:
            success, res = add_worker_portfolio_item(
                worker_id=worker.id,
                title=title,
                description=description,
                category_name=category_name,
                before_image=before_path,
                after_image=after_path,
            )
            if success:
                messages.success(request, "เพิ่มผลงานตัวอย่างเข้าพอร์ตโฟลิโอ (MongoDB) เรียบร้อยแล้ว!")
            else:
                messages.error(request, f"เกิดข้อผิดพลาดในการบันทึกผลงาน: {res}")
        else:
            messages.error(request, "กรุณาระบุชื่องาน/ผลงาน")

    return redirect('dashboard:worker_dashboard')


@login_required
def delete_portfolio_view(request, item_id):
    if not request.user.is_worker:
        messages.error(request, "สิทธิ์เฉพาะช่างรับจ้างเท่านั้น")
        return redirect('core:home')

    worker = request.user.worker_profile
    ok = delete_worker_portfolio_item(worker.id, item_id)
    if ok:
        messages.success(request, "ลบรายการผลงานเรียบร้อยแล้ว")
    else:
        messages.error(request, "ไม่สามารถลบผลงานได้")

    return redirect('dashboard:worker_dashboard')
