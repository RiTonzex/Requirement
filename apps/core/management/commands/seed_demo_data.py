import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from workers.models import WorkerProfile, WorkerService, WorkerServiceArea
from bookings.models import ServiceRequest
from reviews.models import Review
from core.models import Category, Province, Notification, SearchLog
from core.mongodb import (
    get_mongo_db,
    add_worker_portfolio_item,
    send_chat_message
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds realistic demo workers, bookings, MongoDB portfolios, chats, reviews, and notifications'

    def handle(self, *args, **options):
        self.stdout.write("Seeding comprehensive demo data...")

        # 1. Ensure Categories exist
        categories_data = [
            {'name': 'งานเครื่องปรับอากาศและแอร์', 'icon': 'fa-snowflake', 'desc': 'ล้างแอร์ ซ่อมแอร์ เติมน้ำยา ติดตั้งแอร์ใหม่'},
            {'name': 'งานระบบไฟฟ้าและแสงสว่าง', 'icon': 'fa-bolt', 'desc': 'เดินสายไฟ ซ่อมไฟรั่ว ติดตั้งปลั๊กไฟ ตู้เบรกเกอร์'},
            {'name': 'งานประปาและสุขภัณฑ์', 'icon': 'fa-faucet-drip', 'desc': 'ซ่อมท่อแตก ท่อตัน ติดตั้งปั๊มน้ำ เครื่องทำน้ำอุ่น'},
            {'name': 'งานต่อเติมและตกแต่งบ้าน', 'icon': 'fa-hammer', 'desc': 'งานไม้ ก่อฉาบ ทาสี ปูกระเบื้อง หลังคา'},
            {'name': 'งานทำความสะอาดและแม่บ้าน', 'icon': 'fa-broom', 'desc': 'บิ๊กคลีนนิ่ง ดูดไรฝุ่น ซักโซฟา ทำความสะอาดบ้าน'},
            {'name': 'งานซ่อมเครื่องใช้ไฟฟ้า', 'icon': 'fa-tv', 'desc': 'ซ่อมตู้เย็น เครื่องซักผ้า ไมโครเวฟ พัดลม'},
        ]

        category_objs = {}
        for cdata in categories_data:
            cat, _ = Category.objects.get_or_create(
                category_name=cdata['name'],
                defaults={'icon': cdata['icon'], 'description': cdata['desc'], 'is_active': True}
            )
            category_objs[cdata['name']] = cat

        # 2. Ensure Provinces exist
        bkk, _ = Province.objects.get_or_create(province_name="กรุงเทพมหานคร")
        nonthaburi, _ = Province.objects.get_or_create(province_name="นนทบุรี")
        pathum, _ = Province.objects.get_or_create(province_name="ปทุมธานี")
        samutprakan, _ = Province.objects.get_or_create(province_name="สมุทรปราการ")
        chiangmai, _ = Province.objects.get_or_create(province_name="เชียงใหม่")
        chonburi, _ = Province.objects.get_or_create(province_name="ชลบุรี")

        # 3. Create Demo Customers
        c1, _ = User.objects.get_or_create(
            username='vipada',
            defaults={
                'email': 'vipada@customer.com',
                'first_name': 'วิภาดา',
                'last_name': 'สุขใจ',
                'phone_number': '0812345678',
                'role': 'CUSTOMER'
            }
        )
        c1.set_password('pass1234')
        c1.save()

        c2, _ = User.objects.get_or_create(
            username='thanapon',
            defaults={
                'email': 'thanapon@customer.com',
                'first_name': 'ธนพล',
                'last_name': 'เจริญทรัพย์',
                'phone_number': '0898765432',
                'role': 'CUSTOMER'
            }
        )
        c2.set_password('pass1234')
        c2.save()

        # 4. Create Demo Workers
        demo_workers_info = [
            {
                'username': 'somsak_air',
                'first_name': 'สมศักดิ์',
                'last_name': 'แอร์เซอร์วิส',
                'email': 'somsak@worker.com',
                'phone': '081-999-1111',
                'bio': 'ช่างแอร์ประสบการณ์กว่า 12 ปี ผ่านการอบรมช่างเครื่องปรับอากาศระดับ 2 บริการล้างแอร์ด้วยปั๊มแรงดันสูง ตรวจเช็กระบบไฟ เติมน้ำยา R32/R410a รับประกันงานซ่อมนาน 30 วัน',
                'working_hours': 'จันทร์ - เสาร์ (08:00 - 18:30 น.)',
                'status': 'APPROVED',
                'is_verified': True,
                'provinces': [bkk, nonthaburi, pathum],
                'services': [
                    (category_objs['งานเครื่องปรับอากาศและแอร์'], 500, '/เครื่อง'),
                    (category_objs['งานซ่อมเครื่องใช้ไฟฟ้า'], 600, '/งาน'),
                ],
                'portfolios': [
                    ('ล้างแอร์ติดผนัง Inverter 18,000 BTU', 'ล้างคอยล์เย็นและคอยล์ร้อนหมดจด ฆ่าเชื้อรา ไร้กลิ่นอับ ลูกค้าประทับใจมาก', 'งานเครื่องปรับอากาศและแอร์'),
                    ('ซ่อมแอร์ไม่เย็น คอมเพรสเซอร์ไม่ตัด', 'ตรวจพบแคปรันบวม ทำการเปลี่ยนอะไหล่แท้ศูนย์และเติมน้ำยาแอร์เต็มระบบ', 'งานเครื่องปรับอากาศและแอร์'),
                ]
            },
            {
                'username': 'ekachai_electric',
                'first_name': 'เอกชัย',
                'last_name': 'ระบบไฟฟ้า',
                'email': 'ekachai@worker.com',
                'phone': '082-888-2222',
                'bio': 'มีใบประกอบวิชาชีพช่างไฟฟ้าภายในอาคาร (กฟน.) รับติดตั้งตู้คอนซูมเมอร์ เบรกเกอร์กันดูด RCBO เดินสายไฟร้อยท่อ ตรวจเช็กไฟรั่วด้วยเครื่องมือมาตรฐานความปลอดภัยสูง',
                'working_hours': 'ทุกวัน (08:30 - 20:00 น.)',
                'status': 'APPROVED',
                'is_verified': True,
                'provinces': [bkk, samutprakan],
                'services': [
                    (category_objs['งานระบบไฟฟ้าและแสงสว่าง'], 400, '/จุด'),
                ],
                'portfolios': [
                    ('ติดตั้งตู้เบรกเกอร์ Schneider 8 ช่อง', 'เปลี่ยนตู้ไฟเก่าที่ชำรุดเป็นระบบ RCBO ป้องกันไฟดูดไฟรั่ว 100%', 'งานระบบไฟฟ้าและแสงสว่าง'),
                ]
            },
            {
                'username': 'manop_plumbing',
                'first_name': 'มานพ',
                'last_name': 'ท่อตันและประปา',
                'email': 'manop@worker.com',
                'phone': '083-777-3333',
                'bio': 'ช่างประปาและแก้ท่อตัน งูเหล็กไฟฟ้ากำลังสูง ไม่ต้องทุบพื้น ซ่อมท่อประปาฝังผนังรั่วซึม ติดตั้งปั๊มน้ำอัตโนมัติ ถังเก็บน้ำ ปรึกษาและประเมินราคาก่อนเริ่มงาน',
                'working_hours': 'จันทร์ - เสาร์ (08:00 - 18:00 น.)',
                'status': 'APPROVED',
                'is_verified': True,
                'provinces': [chiangmai],
                'services': [
                    (category_objs['งานประปาและสุขภัณฑ์'], 450, '/จุด'),
                ],
                'portfolios': [
                    ('แก้ปัญหาน้ำรั่วซึมใต้อ่างล้างจาน', 'เปลี่ยนชุดสะดืออ่างและท่อดักกลิ่น P-Trap ใหม่ ทดสอบน้ำไหลสะดวกไม่มีหยด', 'งานประปาและสุขภัณฑ์'),
                ]
            },
            {
                'username': 'kanda_cleaning',
                'first_name': 'กานดา',
                'last_name': 'คลีนนิ่งโปร',
                'email': 'kanda@worker.com',
                'phone': '084-666-4444',
                'bio': 'ทีมงานแม่บ้านทำความสะอาดระดับพรีเมียม อุปกรณ์ครบครัน ใช้น้ำยาออร์แกนิกปลอดภัยต่อเด็กและสัตว์เลี้ยง บริการ Big Cleaning คอนโด/บ้านก่อนเข้าอยู่ ซักผ้าม่านโซฟา',
                'working_hours': 'จันทร์ - อาทิตย์ (09:00 - 17:00 น.)',
                'status': 'APPROVED',
                'is_verified': True,
                'provinces': [bkk, nonthaburi],
                'services': [
                    (category_objs['งานทำความสะอาดและแม่บ้าน'], 800, '/งาน'),
                ],
                'portfolios': [
                    ('บิ๊กคลีนนิ่งคอนโด 45 ตร.ม. หลังตกแต่ง', 'ขจัดคราบสีและฝุ่นละอองทุกซอกมุม เช็ดกระจกใสสะอาดพร้อมเข้าอยู่ทันที', 'งานทำความสะอาดและแม่บ้าน'),
                ]
            },
            {
                'username': 'prasit_pending',
                'first_name': 'ประสิทธิ์',
                'last_name': 'ช่างก่อสร้าง (สมัครใหม่)',
                'email': 'prasit@worker.com',
                'phone': '085-555-5555',
                'bio': 'รับงานก่อฉาบ ทาสีบ้าน งานฝ้าเพดาน ซ่อมแซมบ้านทั่วไป',
                'working_hours': 'จันทร์ - เสาร์ (08:30 - 17:30 น.)',
                'status': 'PENDING',
                'is_verified': False,
                'provinces': [bkk],
                'services': [
                    (category_objs['งานต่อเติมและตกแต่งบ้าน'], 350, '/ตร.ม.'),
                ],
                'portfolios': []
            }
        ]

        created_worker_profiles = []

        for w_info in demo_workers_info:
            u, _ = User.objects.get_or_create(
                username=w_info['username'],
                defaults={
                    'email': w_info['email'],
                    'first_name': w_info['first_name'],
                    'last_name': w_info['last_name'],
                    'phone_number': w_info['phone'],
                    'role': 'WORKER'
                }
            )
            u.set_password('pass1234')
            u.save()

            wp, _ = WorkerProfile.objects.get_or_create(
                user=u,
                defaults={
                    'bio': w_info['bio'],
                    'status': w_info['status'],
                    'is_available': True,
                    'is_id_verified': w_info['is_verified'],
                    'working_hours': w_info['working_hours'],
                }
            )
            wp.bio = w_info['bio']
            wp.status = w_info['status']
            wp.is_id_verified = w_info['is_verified']
            wp.working_hours = w_info['working_hours']
            wp.save()

            # Services
            wp.services.all().delete()
            for cat, price, unit in w_info['services']:
                WorkerService.objects.create(
                    worker=wp,
                    category=cat,
                    starting_price=price,
                    price_unit=unit
                )

            # Service Areas
            wp.service_areas.all().delete()
            for prov in w_info['provinces']:
                WorkerServiceArea.objects.create(worker=wp, province=prov)

            # MongoDB Portfolios
            for p_title, p_desc, p_cat in w_info['portfolios']:
                add_worker_portfolio_item(
                    worker_id=wp.id,
                    title=p_title,
                    description=p_desc,
                    category_name=p_cat,
                    before_image="https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=500&auto=format&fit=crop&q=60",
                    after_image="https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=500&auto=format&fit=crop&q=60"
                )

            created_worker_profiles.append(wp)

        # 5. Create Realistic Service Requests (Bookings)
        somsak = created_worker_profiles[0]
        ekachai = created_worker_profiles[1]
        manop = created_worker_profiles[2]

        # Job 1: COMPLETED (with review & invoice ready)
        req1, _ = ServiceRequest.objects.get_or_create(
            id=1001,
            defaults={
                'customer': c1,
                'worker': somsak,
                'category': category_objs['งานเครื่องปรับอากาศและแอร์'],
                'details': 'แอร์ห้องนอนไม่ค่อยเย็น มีน้ำหยดลงพื้นด้านล่าง และมีเสียงดังตอนเปิดพัดลมแรง',
                'address_note': 'หมู่บ้านพฤกษา 12 ซอย 5/2 อ.เมือง นนทบุรี',
                'preferred_date': (timezone.now() - timedelta(days=5)).date(),
                'preferred_time_slot': 'MORNING',
                'status': 'COMPLETED'
            }
        )
        req1.status = 'COMPLETED'
        req1.save()

        # Review for Job 1
        Review.objects.get_or_create(
            request=req1,
            defaults={
                'customer': c1,
                'worker': somsak,
                'rating': 5,
                'comment': 'ช่างสมศักดิ์มาตรงเวลามาก สุภาพ ล้างแอร์สะอาดหมดจด น้ำไม่หยดแล้ว เย็นฉ่ำเหมือนใหม่ แนะนำเลยครับ!',
                'worker_reply': 'ขอบพระคุณคุณวิภาดามากครับ ยินดีให้บริการเสมอครับ หากมีปัญหาใน 30 วันติดต่อได้ตลอดครับ',
                'worker_replied_at': timezone.now() - timedelta(days=4)
            }
        )

        # Job 2: IN_PROGRESS (with chat conversation)
        req2, _ = ServiceRequest.objects.get_or_create(
            id=1002,
            defaults={
                'customer': c2,
                'worker': ekachai,
                'category': category_objs['งานระบบไฟฟ้าและแสงสว่าง'],
                'details': 'ต้องการเปลี่ยนตู้เบรกเกอร์หลักของบ้านเป็นระบบกันดูด และเพิ่มปลั๊กไฟห้องทำงาน 2 จุด',
                'address_note': 'คอนโดลุมพินี สุขุมวิท 77 เขตสวนหลวง กรุงเทพฯ',
                'preferred_date': timezone.now().date(),
                'preferred_time_slot': 'AFTERNOON',
                'status': 'IN_PROGRESS'
            }
        )
        req2.status = 'IN_PROGRESS'
        req2.save()

        # Seed Chat Messages in MongoDB for Job 2
        try:
            send_chat_message(req2.id, c2, "สวัสดีครับช่างเอกชัย พรุ่งนี้ช่วงบ่ายสะดวกเข้ามากี่โมงครับ")
            send_chat_message(req2.id, ekachai.user, "สวัสดีครับคุณธนพล ประมาณ 13.30 น. ผมจะเข้าไปถึงหน้างานพร้อมอุปกรณ์ครับผม")
            send_chat_message(req2.id, c2, "โอเคครับ มีที่จอดรถสำหรับช่างชั้นใต้ดิน แจ้งรปภ.ได้เลยครับ")
        except Exception:
            pass

        # Job 3: REQUESTED (New incoming request)
        req3, _ = ServiceRequest.objects.get_or_create(
            id=1003,
            defaults={
                'customer': c1,
                'worker': manop,
                'category': category_objs['งานประปาและสุขภัณฑ์'],
                'details': 'ก๊อกน้ำอ่างล้างหน้าหลวม และชักโครกกดน้ำแล้วไหลไม่หยุด',
                'address_note': 'ถ.นิมมานเหมินท์ ซอย 9 อ.เมือง จ.เชียงใหม่',
                'preferred_date': (timezone.now() + timedelta(days=1)).date(),
                'preferred_time_slot': 'MORNING',
                'status': 'REQUESTED'
            }
        )

        # 6. Seed Notifications
        Notification.objects.get_or_create(
            recipient=somsak.user,
            sender=c1,
            title="ลูกค้าให้คะแนนรีวิว 5 ดาว!",
            message="คุณวิภาดา สุขใจ ได้เขียนรีวิวและให้คะแนน 5 ดาวแก่งาน #1001",
            link_url="/dashboard/",
            notification_type='REVIEW'
        )

        Notification.objects.get_or_create(
            recipient=c2,
            sender=ekachai.user,
            title="ช่างตอบรับงานของคุณแล้ว",
            message="ช่างเอกชัย ได้ตอบรับงาน #1002 เรียบร้อยแล้ว",
            link_url=f"/bookings/{req2.id}/",
            notification_type='STATUS'
        )

        # 7. Seed Search Logs & MongoDB Indexes
        from core.mongodb import init_mongodb_indexes
        init_mongodb_indexes()

        keywords = ['ล้างแอร์', 'ช่างไฟ', 'ท่อตัน', 'ซ่อมปั๊มน้ำ', 'แม่บ้าน']
        for kw in keywords:
            SearchLog.objects.create(
                keyword=kw,
                province=bkk,
                category=category_objs['งานเครื่องปรับอากาศและแอร์'] if kw == 'ล้างแอร์' else None,
            )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully! 5 Workers, 2 Customers, Bookings, Portfolios, and Chats are ready."))
