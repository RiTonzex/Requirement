from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('create/<int:worker_id>/', views.create_review_view, name='create'),
    path('reply/<int:review_id>/', views.reply_review_view, name='reply'),
    path('toggle-hidden/<int:review_id>/', views.toggle_review_hidden_view, name='toggle_hidden'),
]
