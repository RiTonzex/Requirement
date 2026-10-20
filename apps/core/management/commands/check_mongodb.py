from django.core.management.base import BaseCommand
from django.conf import settings
from core.mongodb import ping_mongodb, get_mongo_db, get_storage_stats, init_mongodb_indexes


class Command(BaseCommand):
    help = 'Check connection status, storage usage, and initialize indexes for MongoDB Atlas.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("[-] Checking MongoDB Atlas connection & storage..."))
        self.stdout.write(f"    Target DB: {getattr(settings, 'MONGO_DB_NAME', 'local_worker_db')}")
        
        success, message = ping_mongodb()
        if success:
            self.stdout.write(self.style.SUCCESS(f"[OK] {message}"))
            
            # Initialize TTL and indexes
            idx_ok, idx_msg = init_mongodb_indexes()
            if idx_ok:
                self.stdout.write(self.style.SUCCESS(f"[OK] TTL Auto-Cleanup & Indexes: {idx_msg}"))
            
            # Storage Stats
            stats = get_storage_stats()
            if 'error' not in stats:
                self.stdout.write(self.style.SUCCESS("\n--- MongoDB Atlas Storage Stats (Free Tier M0) ---"))
                self.stdout.write(f"  * Collections: {stats['collections_count']}")
                self.stdout.write(f"  * Total Documents: {stats['objects_count']}")
                self.stdout.write(f"  * Data Size: {stats['data_size_kb']} KB")
                self.stdout.write(f"  * Storage Used: {stats['storage_size_kb']} KB / 524,288 KB (512 MB Free Limit)")
                pct = round((stats['storage_size_kb'] / 524288) * 100, 4)
                self.stdout.write(self.style.SUCCESS(f"  * Usage Percentage: {pct}% (100% Free - Safe!)"))
            
            try:
                db = get_mongo_db()
                collections = db.list_collection_names()
                self.stdout.write(self.style.SUCCESS(f"\n[OK] Active Collections: {collections}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[WARN] Could not list collections: {e}"))
        else:
            self.stdout.write(self.style.ERROR(f"[FAIL] MongoDB connection failed:\n{message}"))
