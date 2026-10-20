"""
URL configuration for local_worker_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as accounts_views

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('admin-login/', accounts_views.admin_login_view, name='admin_login'),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('workers/', include('workers.urls')),
    path('bookings/', include('bookings.urls')),
    path('reviews/', include('reviews.urls')),
    path('reports/', include('reports.urls')),
    path('dashboard/', include('dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
