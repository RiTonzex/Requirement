from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import Category, Province, SearchLog
from workers.models import WorkerProfile, WorkerService, WorkerServiceArea, SavedWorker
from bookings.models import ServiceRequest
from reviews.models import Review

User = get_user_model()


class LocalWorkerSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Category & Province
        self.category = Category.objects.create(category_name='งานซ่อมระบบไฟ', icon='fa-bolt', description='ซ่อมไฟฟ้า')
        self.province = Province.objects.create(province_name='กรุงเทพมหานคร')

        # Create Admin
        self.admin = User.objects.create_superuser(
            username='admin_test',
            email='admin_test@example.com',
            password='password123',
            role='ADMIN'
        )

        # Create Customer
        self.customer = User.objects.create_user(
            username='cust_test',
            email='cust_test@example.com',
            password='password123',
            role='CUSTOMER',
            first_name='สมชาย',
            last_name='ลูกค้า'
        )

        # Create Worker
        self.worker_user = User.objects.create_user(
            username='worker_test',
            email='worker_test@example.com',
            password='password123',
            role='WORKER',
            first_name='สมปอง',
            last_name='ช่างไฟ'
        )
        self.worker_profile = WorkerProfile.objects.create(
            user=self.worker_user,
            status='APPROVED',
            is_available=True,
            bio='ช่างไฟประสบการณ์สูง'
        )
        WorkerService.objects.create(worker=self.worker_profile, category=self.category, starting_price=500.00)
        WorkerServiceArea.objects.create(worker=self.worker_profile, province=self.province)

    def test_homepage_loads(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ช่างใกล้บ้าน')
        self.assertContains(response, 'สมปอง')

    def test_search_view(self):
        response = self.client.get(reverse('core:search'), {'keyword': 'สมปอง'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'สมปอง')
        # Check SearchLog recorded
        self.assertTrue(SearchLog.objects.filter(keyword='สมปอง').exists())

    def test_worker_detail_view(self):
        response = self.client.get(reverse('workers:detail', args=[self.worker_profile.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'สมปอง ช่างไฟ')
        self.assertContains(response, '500')

    def test_create_booking(self):
        self.client.login(username='cust_test@example.com', password='password123')
        response = self.client.post(reverse('bookings:create', args=[self.worker_profile.id]), {
            'category_id': self.category.id,
            'details': 'สายไฟช็อตที่ห้องครัว',
            'address_note': 'รามคำแหง 24 กทม.',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ServiceRequest.objects.filter(customer=self.customer, worker=self.worker_profile).exists())

    def test_create_review(self):
        self.client.login(username='cust_test@example.com', password='password123')
        response = self.client.post(reverse('reviews:create', args=[self.worker_profile.id]), {
            'rating': 5,
            'comment': 'บริการรวดเร็วและมืออาชีพมากครับ',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Review.objects.filter(customer=self.customer, worker=self.worker_profile, rating=5).exists())

    def test_toggle_save_worker(self):
        self.client.login(username='cust_test@example.com', password='password123')
        # Save worker
        response = self.client.get(reverse('workers:toggle_save', args=[self.worker_profile.id]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SavedWorker.objects.filter(customer=self.customer, worker=self.worker_profile).exists())
        # Unsave worker
        response2 = self.client.get(reverse('workers:toggle_save', args=[self.worker_profile.id]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response2.status_code, 200)
        self.assertFalse(SavedWorker.objects.filter(customer=self.customer, worker=self.worker_profile).exists())

    def test_admin_dashboard_access(self):
        # Normal customer should not access admin dashboard
        self.client.login(username='cust_test@example.com', password='password123')
        response = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(response.status_code, 302)

        # Admin login
        self.client.login(username='admin_test@example.com', password='password123')
        response_admin = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(response_admin.status_code, 200)
