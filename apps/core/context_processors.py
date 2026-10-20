from core.models import Category, Province, Notification


def global_context(request):
    categories = Category.objects.filter(is_active=True).order_by('category_name')
    provinces = Province.objects.all().order_by('province_name')
    
    saved_worker_ids = []
    unread_notifications_count = 0
    recent_notifications = []

    if request.user.is_authenticated:
        saved_worker_ids = list(request.user.saved_workers.values_list('worker_id', flat=True))
        unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        recent_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]
        
    return {
        'global_categories': categories,
        'global_provinces': provinces,
        'user_saved_worker_ids': saved_worker_ids,
        'unread_notifications_count': unread_notifications_count,
        'recent_notifications': recent_notifications,
        'site_title': 'ระบบประกาศและค้นหาช่างรับจ้างท้องถิ่น (ช่างใกล้บ้าน)',
    }
