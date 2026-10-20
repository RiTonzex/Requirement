from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache

User = get_user_model()


class AccountsSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()
        self.user = User.objects.create_user(
            username='ritonz',
            email='ritonz@admin.com',
            password='21112549ooki',
            role='ADMIN'
        )

    def test_successful_login_with_username(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'ritonz',
            'password': '21112549ooki'
        })
        self.assertEqual(response.status_code, 302)

    def test_successful_login_with_email(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'ritonz@admin.com',
            'password': '21112549ooki'
        })
        self.assertEqual(response.status_code, 302)

    def test_login_rate_limiting_lockout(self):
        # Fail 5 times
        for i in range(5):
            response = self.client.post(reverse('accounts:login'), {
                'username': 'ritonz',
                'password': 'wrongpassword'
            })
            self.assertEqual(response.status_code, 200)

        # 6th attempt should be blocked with rate limit warning
        response = self.client.post(reverse('accounts:login'), {
            'username': 'ritonz',
            'password': '21112549ooki'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ถูกระงับการเข้าสู่ระบบชั่วคราว')
