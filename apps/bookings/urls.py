from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('<int:booking_id>/', views.booking_detail_view, name='detail'),
    path('<int:booking_id>/invoice/', views.invoice_view, name='invoice'),
    path('<int:booking_id>/chat/', views.chat_view, name='chat'),
    path('<int:booking_id>/chat/send/', views.send_chat_message_api, name='send_chat_message'),
    path('create/<int:worker_id>/', views.create_booking_view, name='create'),
    path('update/<int:booking_id>/', views.update_booking_status_view, name='update_status'),
    path('update-price/<int:booking_id>/', views.update_booking_price_view, name='update_price'),
    path('upload-slip/<int:booking_id>/', views.upload_payment_slip_view, name='upload_slip'),
    path('confirm-payment/<int:booking_id>/', views.confirm_payment_view, name='confirm_payment'),
    path('sync-portfolio/<int:booking_id>/', views.sync_to_portfolio_view, name='sync_portfolio'),
]
