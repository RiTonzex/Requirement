from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('create/', views.create_report_view, name='create'),
    path('resolve/<int:report_id>/', views.resolve_report_view, name='resolve'),
]
