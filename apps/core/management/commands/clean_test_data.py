from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import SearchLog
from workers.models import WorkerProfile, WorkerService, WorkerServiceArea, SavedWorker
from bookings.models import ServiceRequest
from reviews.models import Review
from reports.models import Report
from core.mongodb import get_mongo_db

User = get_user_model()


class Command(BaseCommand):
    help = 'Clean all test sample accounts and dummy data while preserving Admin and Master Data (Provinces/Categories)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("[-] Cleaning test accounts and dummy data..."))

        # 1. Delete Reviews
        r_deleted, _ = Review.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"[OK] Cleared {r_deleted} test reviews"))

        # 2. Delete Reports
        rep_deleted, _ = Report.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"[OK] Cleared {rep_deleted} test reports"))

        # 3. Delete Bookings (Service Requests)
        b_deleted, _ = ServiceRequest.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"[OK] Cleared {b_deleted} test bookings"))

        # 4. Delete Saved Workers
        sw_deleted, _ = SavedWorker.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"[OK] Cleared {sw_deleted} saved worker bookmarks"))

        # 5. Delete Worker Services and Areas
        ws_deleted, _ = WorkerService.objects.all().delete()
        wsa_deleted, _ = WorkerServiceArea.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"[OK] Cleared {ws_deleted} worker services and {wsa_deleted} service areas"))

        # 6. Delete Worker Profiles
        wp_deleted, _ = WorkerProfile.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"[OK] Cleared {wp_deleted} worker profiles"))

        # 7. Delete Search Logs
        sl_deleted, _ = SearchLog.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"[OK] Cleared {sl_deleted} search logs"))

        # 8. Delete all non-admin test users
        test_users = User.objects.filter(is_superuser=False, role__in=['CUSTOMER', 'WORKER'])
        test_count = test_users.count()
        test_users.delete()
        self.stdout.write(self.style.SUCCESS(f"[OK] Deleted {test_count} test user accounts"))

        # Check remaining users
        remaining = list(User.objects.values('username', 'email', 'role', 'is_superuser'))
        self.stdout.write(self.style.SUCCESS(f"[OK] Remaining active users: {remaining}"))

        # 9. Clean MongoDB Collections
        try:
            db = get_mongo_db()
            db.worker_portfolios.delete_many({})
            db.reviews_and_feedback.delete_many({})
            db.search_logs.delete_many({})
            db.activity_audit_logs.delete_many({})
            db.analytics_daily_summary.replace_one(
                {'_id': 'system_summary_latest'},
                {
                    '_id': 'system_summary_latest',
                    'total_users': User.objects.count(),
                    'total_workers': 0,
                    'approved_workers': 0,
                    'total_bookings': 0,
                    'completed_bookings': 0,
                    'total_reviews': 0,
                    'status': 'READY_FOR_PRODUCTION'
                },
                upsert=True
            )
            self.stdout.write(self.style.SUCCESS("[OK] MongoDB collections cleaned and reset to production-ready state"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"[WARN] Could not reset MongoDB: {e}"))

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] All test data removed! System is clean and ready for real users."))
