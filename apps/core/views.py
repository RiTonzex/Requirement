from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Avg, Count
from .models import Category, Province, SearchLog, Notification
from workers.models import WorkerProfile
from reviews.models import Review
import math

PROVINCE_COORDINATES = {
    'กรุงเทพมหานคร': (13.7563, 100.5018),
    'เชียงใหม่': (18.7883, 98.9853),
    'ขอนแก่น': (16.4322, 102.8236),
    'นครราชสีมา': (14.9799, 102.0978),
    'ภูเก็ต': (7.8804, 98.3923),
    'ศรีสะเกษ': (15.1186, 104.3239),
    'ชลบุรี': (13.3611, 100.9847),
    'นนทบุรี': (13.8591, 100.5217),
    'สมุทรปราการ': (13.5991, 100.5998),
    'ปทุมธานี': (14.0208, 100.5250),
}

def haversine_km(lat1, lon1, lat2, lon2):
    """คำนวณระยะทางระหว่างพิกัด 2 จุดบนผิวโลกเป็นกิโลเมตร (Haversine Formula)"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def home_view(request):
    # Approved & available workers
    featured_workers = WorkerProfile.objects.filter(
        status='APPROVED',
        is_available=True
    ).select_related('user').prefetch_related('services__category', 'service_areas__province', 'reviews')[:6]

    # Quick categories
    categories = Category.objects.filter(is_active=True).annotate(
        worker_count=Count('worker_services__worker', filter=Q(worker_services__worker__status='APPROVED'), distinct=True)
    )

    # Recent 5-star reviews
    recent_reviews = Review.objects.filter(
        is_hidden=False,
        rating__gte=4
    ).select_related('customer', 'worker__user')[:4]

    # Key statistics
    total_workers = WorkerProfile.objects.filter(status='APPROVED').count()
    total_categories = categories.count()
    total_provinces = Province.objects.count()
    total_reviews = Review.objects.filter(is_hidden=False).count()

    context = {
        'featured_workers': featured_workers,
        'categories': categories,
        'recent_reviews': recent_reviews,
        'total_workers': total_workers,
        'total_categories': total_categories,
        'total_provinces': total_provinces,
        'total_reviews': total_reviews,
    }
    return render(request, 'core/home.html', context)


def search_view(request):
    keyword = request.GET.get('keyword', '').strip()
    category_id = request.GET.get('category')
    province_id = request.GET.get('province')
    sort_by = request.GET.get('sort', 'recommended')
    available_only = request.GET.get('available') == '1'

    # Filter approved workers
    workers = WorkerProfile.objects.filter(status='APPROVED').select_related('user').prefetch_related(
        'services__category', 'service_areas__province', 'reviews'
    )

    selected_category = None
    selected_province = None

    if category_id and category_id.isdigit():
        selected_category = Category.objects.filter(id=category_id).first()
        if selected_category:
            workers = workers.filter(services__category_id=category_id)

    if province_id and province_id.isdigit():
        selected_province = Province.objects.filter(id=province_id).first()
        if selected_province:
            workers = workers.filter(service_areas__province_id=province_id)

    # Intelligent Auto-Detection: If user typed province or category directly into the search bar
    log_province = selected_province
    log_category = selected_category

    if keyword:
        # Check if keyword contains or matches a province
        if not log_province:
            direct_prov = Province.objects.filter(province_name__iexact=keyword).first()
            if direct_prov:
                log_province = direct_prov
            else:
                for p in Province.objects.all():
                    if p.province_name in keyword:
                        log_province = p
                        break

        # Check if keyword contains or matches a category
        if not log_category:
            direct_cat = Category.objects.filter(category_name__icontains=keyword).first()
            if direct_cat:
                log_category = direct_cat

        workers = workers.filter(
            Q(user__first_name__icontains=keyword) |
            Q(user__last_name__icontains=keyword) |
            Q(bio__icontains=keyword) |
            Q(services__category__category_name__icontains=keyword) |
            Q(service_areas__province__province_name__icontains=keyword)
        )

    if available_only:
        workers = workers.filter(is_available=True)

    workers = workers.distinct()

    # Annotate with review statistics for sorting
    workers = workers.annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_hidden=False)),
        num_reviews=Count('reviews', filter=Q(reviews__is_hidden=False), distinct=True),
        completed_count=Count('service_requests', filter=Q(service_requests__status='COMPLETED'), distinct=True)
    )

    if sort_by == 'rating':
        workers = workers.order_by('-avg_rating', '-num_reviews')
    elif sort_by == 'completed':
        workers = workers.order_by('-completed_count')
    elif sort_by == 'newest':
        workers = workers.order_by('-id')
    else:  # recommended default
        workers = workers.order_by('-is_available', '-avg_rating', '-completed_count')

    # GPS Location and Distance Calculation
    user_lat = request.GET.get('user_lat')
    user_lng = request.GET.get('user_lng')
    user_coords = None
    if user_lat and user_lng:
        try:
            user_coords = (float(user_lat), float(user_lng))
        except (ValueError, TypeError):
            user_coords = None

    workers_list = list(workers)
    for w in workers_list:
        w_lat = float(w.latitude) if w.latitude else None
        w_lng = float(w.longitude) if w.longitude else None
        if not (w_lat and w_lng):
            prov = w.service_areas.first()
            prov_name = prov.province.province_name if prov and prov.province else 'กรุงเทพมหานคร'
            base_lat, base_lng = PROVINCE_COORDINATES.get(prov_name, (13.7563, 100.5018))
            offset = ((w.id * 17) % 50) * 0.002
            w_lat, w_lng = base_lat + offset, base_lng + offset

        w.computed_lat = round(w_lat, 6)
        w.computed_lng = round(w_lng, 6)

        if user_coords:
            dist = haversine_km(user_coords[0], user_coords[1], w_lat, w_lng)
            w.distance_km = round(dist, 1)
        else:
            w.distance_km = None

    if sort_by == 'distance' and user_coords:
        workers_list.sort(key=lambda x: x.distance_km if x.distance_km is not None else 99999)

    # Record search log if any criteria provided
    if keyword or log_category or log_province:
        SearchLog.objects.create(
            category=log_category,
            province=log_province,
            keyword=keyword if keyword else None,
            ip_address=get_client_ip(request)
        )

    context = {
        'workers': workers_list,
        'keyword': keyword,
        'selected_category_id': int(category_id) if category_id and category_id.isdigit() else None,
        'selected_province_id': int(province_id) if province_id and province_id.isdigit() else None,
        'selected_category': selected_category,
        'selected_province': selected_province,
        'sort_by': sort_by,
        'available_only': available_only,
        'results_count': len(workers_list),
        'user_lat': user_lat,
        'user_lng': user_lng,
        'has_gps': bool(user_coords),
    }
    return render(request, 'core/search.html', context)


def about_view(request):
    return render(request, 'core/about.html')


@login_required
def mark_notification_read_view(request, notif_id):
    try:
        notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        if notif.link_url:
            return redirect(notif.link_url)
    except Exception:
        pass
    return redirect(request.META.get('HTTP_REFERER', 'core:home'))


@login_required
def mark_all_notifications_read_view(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'core:home'))
