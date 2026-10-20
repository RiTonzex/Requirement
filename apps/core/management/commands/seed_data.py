from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Category, Province, SearchLog
from workers.models import WorkerProfile, WorkerService, WorkerServiceArea, SavedWorker
from bookings.models import ServiceRequest
from reviews.models import Review
from reports.models import Report

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with 77 Thai provinces, categories, admin, test workers, customers, reviews, and requests'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("[*] Seeding data..."))
        
        # 1. 77 Provinces
        thai_provinces = [
            'กรุงเทพมหานคร', 'กระบี่', 'กาญจนบุรี', 'กาฬสินธุ์', 'กำแพงเพชร',
            'ขอนแก่น', 'จันทบุรี', 'ฉะเชิงเทรา', 'ชลบุรี', 'ชัยนาท',
            'ชัยภูมิ', 'ชุมพร', 'เชียงราย', 'เชียงใหม่', 'ตรัง',
            'ตราด', 'ตาก', 'นครนายก', 'นครปฐม', 'นครพนม',
            'นครราชสีมา', 'นครศรีธรรมราช', 'นครสวรรค์', 'นนทบุรี', 'นราธิวาส',
            'น่าน', 'บึงกาฬ', 'บุรีรัมย์', 'ปทุมธานี', 'ประจวบคีรีขันธ์',
            'ปราจีนบุรี', 'ปัตตานี', 'พระนครศรีอยุธยา', 'พะเยา', 'พังงา',
            'พัทลุง', 'พิจิตร', 'พิษณุโลก', 'เพชรบุรี', 'เพชรบูรณ์',
            'แพร่', 'ภูเก็ต', 'มหาสารคาม', 'มุกดาหาร', 'แม่ฮ่องสอน',
            'ยโสธร', 'ยะลา', 'ร้อยเอ็ด', 'ระนอง', 'ระยอง',
            'ราชบุรี', 'ลพบุรี', 'ลำปาง', 'ลำพูน', 'เลย',
            'ศรีสะเกษ', 'สกลนคร', 'สงขลา', 'สตูล', 'สมุทรปราการ',
            'สมุทรสงคราม', 'สมุทรสาคร', 'สระแก้ว', 'สระบุรี', 'สิงห์บุรี',
            'สุโขทัย', 'สุพรรณบุรี', 'สุราษฎร์ธานี', 'สุรินทร์', 'หนองคาย',
            'หนองบัวลำภู', 'อ่างทอง', 'อำนาจเจริญ', 'อุดรธานี', 'อุตรดิตถ์',
            'อุทัยธานี', 'อุบลราชธานี'
        ]
        provinces_dict = {}
        for p_name in thai_provinces:
            obj, _ = Province.objects.get_or_create(province_name=p_name)
            provinces_dict[p_name] = obj
        self.stdout.write(self.style.SUCCESS(f"[OK] Loaded {len(provinces_dict)} provinces."))

        # 2. Categories
        categories_data = [
            ('งานระบบไฟฟ้าและแสงสว่าง', 'fa-bolt', 'บริการซ่อม เดินสายไฟ ติดตั้งตู้คอนซูเมอร์ สวิตช์ ปลั๊ก และโคมไฟ'),
            ('งานระบบประปาและสุขาภิบาล', 'fa-faucet-drip', 'บริการเดินท่อประปา ซ่อมท่อรั่วซึม ติดตั้งสุขภัณฑ์ ปั๊มน้ำ แท็งก์น้ำ'),
            ('งานเครื่องปรับอากาศและล้างแอร์', 'fa-snowflake', 'บริการล้างแอร์ ซ่อมแอร์ เติมน้ำยา ติดตั้งและย้ายเครื่องปรับอากาศ'),
            ('งานปูน ก่อสร้าง ต่อเติม ซ่อมแซม', 'fa-trowel-bricks', 'บริการก่อฉาบ เทพื้นปูน งานฝ้าเพดาน ปูกระเบื้อง ซ่อมผนังร้าว'),
            ('งานทาสีบ้านและอาคาร', 'fa-paint-roller', 'บริการทาสีภายนอก ภายใน ทาสีหลังคา ขูดลอกสีเก่า ทากันซึม'),
            ('งานเหล็ก ประตู หน้าต่าง โครงหลังคา', 'fa-hammer', 'บริการงานเชื่อมเหล็ก ติดตั้งประตูม้วน หน้าต่าง ประตูสแตนเลส หลังคาเมทัลชีท'),
            ('งานไม้และเฟอร์นิเจอร์บิวท์อิน', 'fa-chair', 'บริการงานไม้ ซ่อมแซมเฟอร์นิเจอร์ ปูพื้นไม้ บิวท์อินตู้และเคาน์เตอร์'),
            ('งานระบบกล้องวงจรปิดและระบบความปลอดภัย', 'fa-video', 'บริการติดตั้งและตั้งค่าระบบกล้อง CCTV สัญญาณกันขโมย สมาร์ทโฮม'),
            ('งานกำจัดปลวกและแมลงรบกวน', 'fa-bug', 'บริการฉีดปลวก วางท่ออัดน้ำยา กำจัดมด หนู แมลงสาบ'),
            ('งานซ่อมหลังคาและแก้ปัญหารั่วซึม', 'fa-shield-halved', 'บริการสำรวจ ซ่อมรอยรั่วหลังคา เปลี่ยนกระเบื้อง ทากันซึมดาดฟ้า'),
        ]
        cat_dict = {}
        for name, icon, desc in categories_data:
            cat, _ = Category.objects.get_or_create(
                category_name=name,
                defaults={'icon': icon, 'description': desc, 'is_active': True}
            )
            cat_dict[name] = cat
        self.stdout.write(self.style.SUCCESS(f"[OK] Loaded {len(cat_dict)} categories."))

        # 3. Superuser / Admin
        admin_user, created = User.objects.get_or_create(
            username='ritonz',
            defaults={
                'email': 'ritonz@admin.com',
                'first_name': 'ภูพิรัฐ',
                'last_name': 'ผู้ดูแลระบบ',
                'phone_number': '0812345678',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('21112549ooki')
        admin_user.role = 'ADMIN'
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        self.stdout.write(self.style.SUCCESS("[OK] Created Admin user (ritonz / 21112549ooki)"))

        # 4. Sample Customers
        cust1, created = User.objects.get_or_create(
            email='customer@example.com',
            defaults={
                'username': 'customer1',
                'first_name': 'สมชาย',
                'last_name': 'ใจดี',
                'phone_number': '0891112233',
                'role': 'CUSTOMER',
            }
        )
        if created:
            cust1.set_password('customer1234')
            cust1.save()

        cust2, created = User.objects.get_or_create(
            email='somying@example.com',
            defaults={
                'username': 'customer2',
                'first_name': 'สมหญิง',
                'last_name': 'รักสงบ',
                'phone_number': '0894445566',
                'role': 'CUSTOMER',
            }
        )
        if created:
            cust2.set_password('customer1234')
            cust2.save()

        self.stdout.write(self.style.SUCCESS("[OK] Created sample customers."))

        # 5. Sample Workers
        workers_data = [
            {
                'email': 'sompong.elec@example.com',
                'username': 'worker_sompong',
                'first_name': 'สมพงษ์',
                'last_name': 'ช่างไฟมืออาชีพ',
                'phone': '0819876543',
                'bio': 'ช่างไฟฟ้าประสบการณ์กว่า 15 ปี รับเดินระบบไฟบ้าน อาคาร โรงงาน มีใบรับรองช่างไฟฟ้าภายในอาคารระดับ 1 งานเรียบร้อย ปลอดภัย ได้มาตรฐาน สวิตช์ ปลั๊ก ตู้คอนซูเมอร์',
                'services': [
                    ('งานระบบไฟฟ้าและแสงสว่าง', 450.00),
                    ('งานระบบกล้องวงจรปิดและระบบความปลอดภัย', 600.00),
                ],
                'provinces': ['กรุงเทพมหานคร', 'นนทบุรี', 'ปทุมธานี', 'สมุทรปราการ'],
                'status': 'APPROVED',
            },
            {
                'email': 'prasert.air@example.com',
                'username': 'worker_prasert',
                'first_name': 'ประเสริฐ',
                'last_name': 'แอร์เซอร์วิส',
                'phone': '0865551234',
                'bio': 'บริการล้างแอร์ ซ่อมแอร์ ติดตั้งแอร์ทุกยี่ห้อ เติมน้ำยา เช็กรั่ว ย้ายแอร์ ช่างผ่านการอบรมจากศูนย์ชั้นนำ เครื่องมือทันสมัย ฉีดน้ำยาฆ่าเชื้อฟรีทุกครั้งที่ล้าง',
                'services': [
                    ('งานเครื่องปรับอากาศและล้างแอร์', 500.00),
                    ('งานระบบไฟฟ้าและแสงสว่าง', 400.00),
                ],
                'provinces': ['กรุงเทพมหานคร', 'สมุทรปราการ', 'ชลบุรี'],
                'status': 'APPROVED',
            },
            {
                'email': 'wichai.plumber@example.com',
                'username': 'worker_wichai',
                'first_name': 'วิชัย',
                'last_name': 'ช่างท่อประปา',
                'phone': '0834449876',
                'bio': 'ช่างประปาชำนาญการ ซ่อมท่อแตก ท่อรั่วซึมใต้พื้น ผนัง ติดตั้งปั๊มน้ำ แท็งก์น้ำ เครื่องทำน้ำอุ่น แก้ปัญหาน้ำไหลช้า สุขภัณฑ์ตัน บริการรวดเร็ว ตรงเวลา',
                'services': [
                    ('งานระบบประปาและสุขาภิบาล', 350.00),
                    ('งานซ่อมหลังคาและแก้ปัญหารั่วซึม', 700.00),
                ],
                'provinces': ['เชียงใหม่', 'ลำพูน', 'ลำปาง'],
                'status': 'APPROVED',
            },
            {
                'email': 'chatchai.build@example.com',
                'username': 'worker_chatchai',
                'first_name': 'ฉัตรชัย',
                'last_name': 'การช่างและก่อสร้าง',
                'phone': '0897778899',
                'bio': 'รับเหมาต่อเติมบ้าน ก่อฉาบ ปูกระเบื้อง ทำฝ้าเพดาน ทาสี รีโนเวทห้องน้ำและห้องครัว งานคุณภาพ รับประกันผลงาน ราคากันเอง พร้อมประเมินหน้างานฟรี',
                'services': [
                    ('งานปูน ก่อสร้าง ต่อเติม ซ่อมแซม', 800.00),
                    ('งานทาสีบ้านและอาคาร', 600.00),
                    ('งานเหล็ก ประตู หน้าต่าง โครงหลังคา', 900.00),
                ],
                'provinces': ['ขอนแก่น', 'นครราชสีมา', 'อุดรธานี'],
                'status': 'APPROVED',
            },
            {
                'email': 'anawat.wood@example.com',
                'username': 'worker_anawat',
                'first_name': 'อนวัช',
                'last_name': 'เฟอร์นิเจอร์ไม้',
                'phone': '0852223344',
                'bio': 'ช่างไม้ฝีมือประณีต บิวท์อินตู้เสื้อผ้า เคาน์เตอร์ครัว ซ่อมโซฟา เก้าอี้ โต๊ะไม้แท้ งานขัดเคลือบพื้นไม้ปาร์เก้ ทำตามแบบลูกค้าสั่งได้ทุกสไตล์',
                'services': [
                    ('งานไม้และเฟอร์นิเจอร์บิวท์อิน', 1200.00),
                ],
                'provinces': ['กรุงเทพมหานคร', 'นนทบุรี', 'นครปฐม'],
                'status': 'APPROVED',
            },
            {
                'email': 'new.worker@example.com',
                'username': 'worker_new',
                'first_name': 'ธนกฤต',
                'last_name': 'ช่างใหม่รออนุมัติ',
                'phone': '0821110099',
                'bio': 'ช่างติดตั้งหลังคาและซ่อมรอยรั่วซึม ประสบการณ์ 5 ปี สมัครเข้ามาใหม่รอแอดมินตรวจสอบเอกสาร',
                'services': [
                    ('งานซ่อมหลังคาและแก้ปัญหารั่วซึม', 500.00),
                ],
                'provinces': ['กรุงเทพมหานคร'],
                'status': 'PENDING',
            }
        ]

        created_workers = []
        for w_data in workers_data:
            w_user, w_created = User.objects.get_or_create(
                email=w_data['email'],
                defaults={
                    'username': w_data['username'],
                    'first_name': w_data['first_name'],
                    'last_name': w_data['last_name'],
                    'phone_number': w_data['phone'],
                    'role': 'WORKER',
                }
            )
            if w_created:
                w_user.set_password('worker1234')
                w_user.save()

            wp, _ = WorkerProfile.objects.get_or_create(
                user=w_user,
                defaults={
                    'bio': w_data['bio'],
                    'status': w_data['status'],
                    'is_available': True,
                    'approved_by': admin_user if w_data['status'] == 'APPROVED' else None,
                    'approved_at': timezone.now() if w_data['status'] == 'APPROVED' else None,
                }
            )

            # Services
            for s_name, price in w_data['services']:
                if s_name in cat_dict:
                    WorkerService.objects.get_or_create(
                        worker=wp,
                        category=cat_dict[s_name],
                        defaults={'starting_price': price}
                    )

            # Service Areas
            for p_name in w_data['provinces']:
                if p_name in provinces_dict:
                    WorkerServiceArea.objects.get_or_create(
                        worker=wp,
                        province=provinces_dict[p_name]
                    )

            created_workers.append(wp)

        self.stdout.write(self.style.SUCCESS(f"[OK] Loaded {len(created_workers)} sample workers."))

        # 6. Sample Bookings / Service Requests
        req1, _ = ServiceRequest.objects.get_or_create(
            customer=cust1,
            worker=created_workers[0],  # Sompong
            category=cat_dict['งานระบบไฟฟ้าและแสงสว่าง'],
            defaults={
                'status': 'COMPLETED',
                'details': 'ติดตั้งตู้ไฟ Consumer Unit ใหม่ 8 ช่อง และเดินสายไฟสำหรับติดตั้งเครื่องทำน้ำอุ่น 2 จุด',
                'address_note': 'ซอยลาดพร้าว 101 แขวงคลองจั่น เขตบางกะปิ กทม.',
                'preferred_date': timezone.now().date(),
            }
        )

        req2, _ = ServiceRequest.objects.get_or_create(
            customer=cust2,
            worker=created_workers[1],  # Prasert
            category=cat_dict['งานเครื่องปรับอากาศและล้างแอร์'],
            defaults={
                'status': 'COMPLETED',
                'details': 'ล้างแอร์ติดผนัง 2 เครื่อง (Inverter 12000 BTU) และเช็กระดับน้ำยาแอร์',
                'address_note': 'หมู่บ้านพฤกษา บางพลี จ.สมุทรปราการ',
                'preferred_date': timezone.now().date(),
            }
        )

        req3, _ = ServiceRequest.objects.get_or_create(
            customer=cust1,
            worker=created_workers[1],  # Prasert
            category=cat_dict['งานเครื่องปรับอากาศและล้างแอร์'],
            defaults={
                'status': 'IN_PROGRESS',
                'details': 'แอร์มีน้ำหยดที่ห้องนอนใหญ่ ต้องการให้เข้ามาดูและแก้ปัญหาด่วน',
                'address_note': 'คอนโดย่านรัชดาภิเษก กทม.',
                'preferred_date': timezone.now().date(),
            }
        )

        # 7. Sample Reviews
        Review.objects.get_or_create(
            request=req1,
            customer=cust1,
            worker=created_workers[0],
            defaults={
                'rating': 5,
                'comment': 'ช่างสมพงษ์ทำงานเรียบร้อยมากครับ เก็บงานเนียน อธิบายระบบไฟชัดเจน แนะนำเลยครับ!',
                'worker_reply': 'ขอบพระคุณมากครับ ยินดีให้บริการเสมอครับ หากมีปัญหาเรียกได้ตลอดครับ',
                'worker_replied_at': timezone.now(),
            }
        )

        Review.objects.get_or_create(
            request=req2,
            customer=cust2,
            worker=created_workers[1],
            defaults={
                'rating': 5,
                'comment': 'ล้างแอร์สะอาดมาก ไม่มีกลิ่นอับ ช่างใส่ถุงคลุมป้องกันน้ำกระเด็นอย่างดี มีฉีดฆ่าเชื้อให้ด้วยค่ะ',
                'worker_reply': 'ขอบคุณคุณสมหญิงมากครับ ยินดีให้บริการครับ',
                'worker_replied_at': timezone.now(),
            }
        )

        # 8. Saved Workers
        SavedWorker.objects.get_or_create(customer=cust1, worker=created_workers[0])
        SavedWorker.objects.get_or_create(customer=cust1, worker=created_workers[1])

        # 9. Search Logs
        SearchLog.objects.get_or_create(
            category=cat_dict['งานระบบไฟฟ้าและแสงสว่าง'],
            province=provinces_dict['กรุงเทพมหานคร'],
            keyword='ช่างไฟ',
            defaults={'ip_address': '127.0.0.1'}
        )
        SearchLog.objects.get_or_create(
            category=cat_dict['งานเครื่องปรับอากาศและล้างแอร์'],
            province=provinces_dict['สมุทรปราการ'],
            keyword='ล้างแอร์',
            defaults={'ip_address': '127.0.0.1'}
        )

        # 10. Sample Reports
        Report.objects.get_or_create(
            reporter=cust2,
            reported_worker=created_workers[3],
            defaults={
                'reason': 'ช่างมาสายกว่าเวลานัดหมาย 2 ชั่วโมงโดยไม่แจ้งล่วงหน้า',
                'status': 'PENDING',
                'admin_notes': 'รอติดต่อสอบถามช่างเพื่อชี้แจง',
            }
        )

        self.stdout.write(self.style.SUCCESS("[SUCCESS] Seed data completed successfully!"))

