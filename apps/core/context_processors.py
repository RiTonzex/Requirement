from django.core.cache import cache
from core.models import Category, Province, Notification

CACHE_TIMEOUT = 3600  # 1 hour


def global_context(request):
    try:
        categories = cache.get('global_categories')
        if categories is None:
            categories = list(Category.objects.filter(is_active=True).order_by('category_name'))
            cache.set('global_categories', categories, CACHE_TIMEOUT)

        provinces = cache.get('global_provinces')
        if provinces is None:
            provinces = list(Province.objects.all().order_by('province_name'))
            cache.set('global_provinces', provinces, CACHE_TIMEOUT)
        
        saved_worker_ids = []
        unread_notifications_count = 0
        recent_notifications = []

        if request.user.is_authenticated:
            saved_worker_ids = list(request.user.saved_workers.values_list('worker_id', flat=True))
            unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
            recent_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]
    except Exception:
        categories = []
        provinces = []
        saved_worker_ids = []
        unread_notifications_count = 0
        recent_notifications = []
        
    return {
        'global_categories': categories,
        'global_provinces': provinces,
        'user_saved_worker_ids': saved_worker_ids,
        'unread_notifications_count': unread_notifications_count,
        'recent_notifications': recent_notifications,
        'site_title': 'ระบบประกาศและค้นหาช่างรับจ้างท้องถิ่น (ช่างใกล้บ้าน)',
    }
