import cloudinary
import cloudinary.uploader
from django.core.management.base import BaseCommand
from django.conf import settings
from accounts.models import User
from workers.models import WorkerProfile
from bookings.models import ServiceRequest
from core.mongodb import get_mongo_db


class Command(BaseCommand):
    help = 'Download curated HD images and upload all directly into Cloudinary, linking to PostgreSQL and MongoDB'

    def handle(self, *args, **options):
        cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', None)
        api_key = getattr(settings, 'CLOUDINARY_API_KEY', None)
        api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', None)

        self.stdout.write(self.style.NOTICE(f"[-] Connected to Cloudinary Cloud Name='{cloud_name}'..."))

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )

        # 1. Upload User Avatars
        self.stdout.write(self.style.NOTICE("[-] Uploading User Avatars to Cloudinary..."))
        user_avatars = {
            'ritonz': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&auto=format&fit=crop&q=80',
            'sompong_worker': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500&auto=format&fit=crop&q=80',
            'prasert_worker': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=500&auto=format&fit=crop&q=80',
            'wichai_worker': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=500&auto=format&fit=crop&q=80',
            'somchai_customer': 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=500&auto=format&fit=crop&q=80',
            'suda_customer': 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=500&auto=format&fit=crop&q=80',
        }

        for username, url in user_avatars.items():
            try:
                user = User.objects.filter(username=username).first()
                if user:
                    res = cloudinary.uploader.upload(url, folder="avatars", public_id=f"user_{user.id}_avatar", overwrite=True)
                    user.avatar = res['secure_url']
                    user.save(update_fields=['avatar'])
                    self.stdout.write(f" -> User '{username}' avatar: {res['secure_url']}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error for {username}: {e}"))

        # 2. Upload Worker Profiles, KYC Cards, Certificates
        self.stdout.write(self.style.NOTICE("[-] Uploading Worker Profiles, KYC IDs & Certificates to Cloudinary..."))
        worker_mock_images = [
            {
                'profile': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&auto=format&fit=crop&q=80',
                'id_card': 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=600&auto=format&fit=crop&q=80',
                'cert': 'https://images.unsplash.com/photo-1589330694653-ded6df03f754?w=600&auto=format&fit=crop&q=80'
            },
            {
                'profile': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=600&auto=format&fit=crop&q=80',
                'id_card': 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=600&auto=format&fit=crop&q=80',
                'cert': 'https://images.unsplash.com/photo-1589330694653-ded6df03f754?w=600&auto=format&fit=crop&q=80'
            },
            {
                'profile': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=600&auto=format&fit=crop&q=80',
                'id_card': 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=600&auto=format&fit=crop&q=80',
                'cert': 'https://images.unsplash.com/photo-1589330694653-ded6df03f754?w=600&auto=format&fit=crop&q=80'
            },
            {
                'profile': 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=600&auto=format&fit=crop&q=80',
                'id_card': 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=600&auto=format&fit=crop&q=80',
                'cert': 'https://images.unsplash.com/photo-1589330694653-ded6df03f754?w=600&auto=format&fit=crop&q=80'
            },
            {
                'profile': 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&auto=format&fit=crop&q=80',
                'id_card': 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=600&auto=format&fit=crop&q=80',
                'cert': 'https://images.unsplash.com/photo-1589330694653-ded6df03f754?w=600&auto=format&fit=crop&q=80'
            },
        ]

        workers = WorkerProfile.objects.all()
        for idx, w in enumerate(workers):
            mock = worker_mock_images[idx % len(worker_mock_images)]
            try:
                res_p = cloudinary.uploader.upload(mock['profile'], folder="workers/profiles", public_id=f"worker_{w.id}_profile", overwrite=True)
                res_id = cloudinary.uploader.upload(mock['id_card'], folder="workers/kyc", public_id=f"worker_{w.id}_id_card", overwrite=True)
                res_cert = cloudinary.uploader.upload(mock['cert'], folder="workers/certificates", public_id=f"worker_{w.id}_certificate", overwrite=True)

                w.profile_image = res_p['secure_url']
                w.id_card_image = res_id['secure_url']
                w.certificate_image = res_cert['secure_url']
                w.save(update_fields=['profile_image', 'id_card_image', 'certificate_image'])
                self.stdout.write(f" -> Worker #{w.id} ({w.user.full_name}) profile/KYC/cert uploaded to Cloudinary.")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error for worker #{w.id}: {e}"))

        # 3. Upload Booking Problem Attachments
        self.stdout.write(self.style.NOTICE("[-] Uploading Booking Problem Attachments to Cloudinary..."))
        problem_mock_urls = [
            'https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=600&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=600&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1585704032915-c3400ca199e7?w=600&auto=format&fit=crop&q=80',
        ]
        requests = ServiceRequest.objects.all()
        for idx, req in enumerate(requests):
            try:
                p_url = problem_mock_urls[idx % len(problem_mock_urls)]
                res_req = cloudinary.uploader.upload(p_url, folder="bookings/problems", public_id=f"problem_req_{req.id}", overwrite=True)
                req.problem_image = res_req['secure_url']
                req.save(update_fields=['problem_image'])
                self.stdout.write(f" -> ServiceRequest #{req.id} problem image uploaded.")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error for request #{req.id}: {e}"))

        # 4. Upload MongoDB Portfolio Before/After Showcases to Cloudinary
        self.stdout.write(self.style.NOTICE("[-] Uploading MongoDB Portfolio Before/After Showcases to Cloudinary..."))
        try:
            db = get_mongo_db()
            mongo_portfolios = list(db.worker_portfolios.find({}))
            for p_doc in mongo_portfolios:
                w_id = p_doc.get('worker_id')
                gallery = p_doc.get('gallery', [])
                updated_gallery = []
                for item in gallery:
                    b_img = item.get('before_image')
                    a_img = item.get('after_image')
                    item_id = item.get('item_id', 'item')
                    
                    if b_img and b_img.startswith('http'):
                        res_b = cloudinary.uploader.upload(b_img, folder="workers/portfolios", public_id=f"portfolio_{w_id}_{item_id}_before", overwrite=True)
                        item['before_image'] = res_b['secure_url']
                    
                    if a_img and a_img.startswith('http'):
                        res_a = cloudinary.uploader.upload(a_img, folder="workers/portfolios", public_id=f"portfolio_{w_id}_{item_id}_after", overwrite=True)
                        item['after_image'] = res_a['secure_url']
                    
                    updated_gallery.append(item)
                
                db.worker_portfolios.update_one({'_id': p_doc['_id']}, {'$set': {'gallery': updated_gallery}})
                self.stdout.write(f" -> Updated MongoDB Portfolio for Worker #{w_id} with Cloudinary URLs.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error updating MongoDB Portfolios: {e}"))

        self.stdout.write(self.style.SUCCESS("[SUCCESS] ALL IMAGES UPLOADED & SYNCED TO CLOUDINARY!"))
