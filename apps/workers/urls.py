from django.urls import path
from . import views

app_name = 'workers'

urlpatterns = [
    path('<int:worker_id>/', views.worker_detail_view, name='detail'),
    path('<int:worker_id>/save/', views.toggle_save_worker, name='toggle_save'),
    path('toggle-availability/', views.toggle_availability, name='toggle_availability'),
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),
    path('portfolio/add/', views.add_portfolio_view, name='add_portfolio'),
    path('portfolio/delete/<str:item_id>/', views.delete_portfolio_view, name='delete_portfolio'),
]
