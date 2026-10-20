from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Category, Province, SearchLog
from workers.models import WorkerProfile, WorkerService, WorkerServiceArea, SavedWorker
from bookings.models import ServiceRequest
from reviews.models import Review
from reports.models import Report
from core.mongodb import get_mongo_db

User = get_user_model()


class Command(BaseCommand):
    help = 'Sync data into MongoDB collections for Hybrid Database Architecture'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("[-] Starting data sync to MongoDB Atlas..."))
        try:
            db = get_mongo_db()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[FAIL] Failed to connect to MongoDB: {e}"))
            return

        # 1. Search Logs & Search Analytics (MongoDB Dedicated)
        search_logs = SearchLog.objects.all()
        s_count = 0
        for s in search_logs:
            doc = {
                '_id': s.id,
                'keyword': s.keyword,
                'category': s.category.category_name if s.category else None,
                'province': s.province.province_name if s.province else None,
                'ip_address': s.ip_address,
                'searched_at': str(s.searched_at),
            }
            db.search_logs.replace_one({'_id': doc['_id']}, doc, upsert=True)
            s_count += 1
        self.stdout.write(self.style.SUCCESS(f"[OK] Synced {s_count} search logs to MongoDB [search_logs]"))

        # 2. Worker Portfolios & Extended Profiles (MongoDB Dedicated)
        workers = WorkerProfile.objects.select_related('user', 'approved_by').prefetch_related('services__category', 'service_areas__province').all()
        w_count = 0
        for w in workers:
            services = [
                {
                    'category_id': s.category_id,
                    'category_name': s.category.category_name,
                    'starting_price': float(s.starting_price),
                }
                for s in w.services.all()
            ]
            areas = [area.province.province_name for area in w.service_areas.all()]

            doc = {
                '_id': w.id,
                'user_id': w.user_id,
                'username': w.user.username,
                'full_name': w.user.full_name,
                'email': w.user.email,
                'phone_number': w.user.phone_number,
                'bio': w.bio,
                'status': w.status,
                'is_available': w.is_available,
                'profile_image': w.profile_image.url if w.profile_image else None,
                'services': services,
                'service_areas': areas,
                'portfolio_gallery': [
                    {
                        'title': f"ผลงานตัวอย่าง {w.user.first_name}",
                        'description': 'งานติดตั้งและซ่อมบำรุงตามมาตรฐาน',
                        'images': ['/static/images/portfolio_sample1.jpg', '/static/images/portfolio_sample2.jpg'],
                        'completed_date': '2026-08-15',
                        'tags': [s['category_name'] for s in services]
                    }
                ],
                'average_rating': float(w.average_rating),
                'review_count': w.review_count,
                'completed_jobs_count': w.completed_jobs_count,
                'approved_at': str(w.approved_at) if w.approved_at else None,
            }
            db.worker_portfolios.replace_one({'_id': doc['_id']}, doc, upsert=True)
            w_count += 1
        self.stdout.write(self.style.SUCCESS(f"[OK] Synced {w_count} worker portfolios to MongoDB [worker_portfolios]"))

        # 3. Reviews & Feedback (MongoDB Dedicated)
        reviews = Review.objects.select_related('customer', 'worker__user', 'request').all()
        r_count = 0
        for r in reviews:
            doc = {
                '_id': r.id,
                'request_id': r.request_id,
                'customer_id': r.customer_id,
                'customer_name': r.customer.full_name,
                'worker_id': r.worker_id,
                'worker_name': r.worker.user.full_name,
                'rating': r.rating,
                'comment': r.comment,
                'worker_reply': r.worker_reply,
                'worker_replied_at': str(r.worker_replied_at) if r.worker_replied_at else None,
                'is_hidden': r.is_hidden,
                'photos': [],
                'detailed_ratings': {
                    'punctuality': r.rating,
                    'service_quality': r.rating,
                    'pricing_fairness': r.rating,
                },
                'created_at': str(r.created_at),
            }
            db.reviews_and_feedback.replace_one({'_id': doc['_id']}, doc, upsert=True)
            r_count += 1
        self.stdout.write(self.style.SUCCESS(f"[OK] Synced {r_count} reviews to MongoDB [reviews_and_feedback]"))

        # 4. Activity & Audit Logs (MongoDB Dedicated)
        bookings = ServiceRequest.objects.select_related('customer', 'worker__user', 'category').all()
        for b in bookings:
            log_doc = {
                'event_type': 'BOOKING_LIFECYCLE',
                'booking_id': b.id,
                'customer_id': b.customer_id,
                'customer_name': b.customer.full_name,
                'worker_id': b.worker_id,
                'worker_name': b.worker.user.full_name,
                'status': b.status,
                'category': b.category.category_name if b.category else None,
                'address_note': b.address_note,
                'details': b.details,
                'created_at': str(b.created_at),
                'updated_at': str(b.updated_at),
            }
            db.activity_audit_logs.replace_one({'booking_id': b.id, 'event_type': 'BOOKING_LIFECYCLE'}, log_doc, upsert=True)
        self.stdout.write(self.style.SUCCESS(f"[OK] Synced booking audit logs to MongoDB [activity_audit_logs]"))

        # 5. System Analytics & Aggregates (MongoDB Dedicated)
        summary_doc = {
            '_id': 'system_summary_latest',
            'total_users': User.objects.count(),
            'total_workers': WorkerProfile.objects.count(),
            'approved_workers': WorkerProfile.objects.filter(status='APPROVED').count(),
            'total_bookings': ServiceRequest.objects.count(),
            'completed_bookings': ServiceRequest.objects.filter(status='COMPLETED').count(),
            'total_reviews': Review.objects.count(),
            'total_categories': Category.objects.count(),
            'total_provinces': Province.objects.count(),
        }
        db.analytics_daily_summary.replace_one({'_id': summary_doc['_id']}, summary_doc, upsert=True)
        self.stdout.write(self.style.SUCCESS(f"[OK] Generated system dashboard summary to MongoDB [analytics_daily_summary]"))

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] All MongoDB Collections populated successfully!"))
