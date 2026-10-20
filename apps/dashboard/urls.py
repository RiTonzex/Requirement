from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Customer & Worker Dashboards
    path('customer/', views.customer_dashboard, name='customer_dashboard'),
    path('worker/', views.worker_dashboard, name='worker_dashboard'),

    # Admin Management Dashboards
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/workers/', views.admin_workers_list, name='admin_workers'),
    path('admin/categories/', views.admin_categories_list, name='admin_categories'),
    path('admin/users/', views.admin_users_list, name='admin_users'),
    path('admin/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('admin/reports/', views.admin_reports_list, name='admin_reports'),
    path('admin/reviews/', views.admin_reviews_list, name='admin_reviews'),
    path('admin/stats/', views.admin_stats_view, name='admin_stats'),
]
