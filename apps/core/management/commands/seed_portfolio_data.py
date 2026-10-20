from datetime import datetime
from django.core.management.base import BaseCommand
from workers.models import WorkerProfile
from core.mongodb import get_mongo_db


class Command(BaseCommand):
    help = 'Populate MongoDB worker_portfolios with rich, unique, high quality Before/After showcase images'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("[-] Updating MongoDB worker portfolios..."))
        
        try:
            db = get_mongo_db()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[FAIL] MongoDB connection error: {e}"))
            return

        # Portfolio Data Template per worker category
        portfolios_by_worker = {
            1: [  # สมพงษ์ - งานระบบไฟฟ้า
                {
                    "item_id": "elec_01",
                    "title": "ติดตั้งตู้คอนซูเมอร์ยูนิต Schneider 10 ช่อง",
                    "description": "รื้อตู้ไฟเก่าเสื่อมสภาพ เดินสายดินมาตรฐาน และติดตั้งตู้ไฟใหม่พร้อมเบรกเกอร์กันดูด RCBO ปลอดภัย 100%",
                    "category_name": "งานระบบไฟฟ้าและแสงสว่าง",
                    "before_image": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80",
                    "after_image": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600&auto=format&fit=crop&q=80",
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
                },
                {
                    "item_id": "elec_02",
                    "title": "ติดตั้งโคมไฟระย้าและระบบไฟดาวน์ไลท์ LED",
                    "description": "เจาะฝ้าซ่อนสายไฟ ติดตั้งสวิตช์หรี่ไฟ (Dimmer) แสงสว่างสม่ำเสมอสวยงามทั่วห้องรับแขก",
                    "category_name": "งานระบบไฟฟ้าและแสงสว่าง",
                    "before_image": "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=600&auto=format&fit=crop&q=80",
                    "after_image": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600&auto=format&fit=crop&q=80",
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
                }
            ],
            2: [  # ประเสริฐ - งานแอร์
                {
                    "item_id": "air_01",
                    "title": "ล้างแอร์ติดผนัง Inverter 18,000 BTU",
                    "description": "ล้างคอยล์เย็นและคอยล์ร้อนด้วยปั๊มแรงดันสูง ตรวจเช็กระบบน้ำยา R32 ลมแรงเย็นฉ่ำ ไม่มีกลิ่นอับ",
                    "category_name": "งานเครื่องปรับอากาศและล้างแอร์",
                    "before_image": "https://images.unsplash.com/photo-1621905252507-b35492cc74b4?w=600&auto=format&fit=crop&q=80",
                    "after_image": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=600&auto=format&fit=crop&q=80",
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
                },
                {
                    "item_id": "air_02",
                    "title": "แก้ไขปัญหาน้ำแอร์หยดและท่อน้ำทิ้งตัน",
                    "description": "เป่าล้างท่อน้ำทิ้ง เปลี่ยนฉนวนหุ้มท่อทองแดง ทดสอบเปิดใช้งาน 2 ชั่วโมง ไม่มีน้ำหยดซึม",
                    "category_name": "งานเครื่องปรับอากาศและล้างแอร์",
                    "before_image": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=600&auto=format&fit=crop&q=80",
                    "after_image": "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=600&auto=format&fit=crop&q=80",
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
                }
            ],
            3: [  # วิชัย - งานประปา
                {
                    "item_id": "plumb_01",
                    "title": "แก้ปัญหาน้ำรั่วซึมใต้อ่างล้างจาน",
                    "description": "เปลี่ยนชุดสะดืออ่างสแตนเลสและท่อดักกลิ่น P-Trap ใหม่ทั้งหมด ทดสอบน้ำไหลสะดวก ไม่มีหยดซึม",
                    "category_name": "งานระบบประปาและสุขาภิบาล",
                    "before_image": "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?w=600&auto=format&fit=crop&q=80",
                    "after_image": "https://images.unsplash.com/photo-1584622781564-1d987f7333c1?w=600&auto=format&fit=crop&q=80",
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
                },
                {
                    "item_id": "plumb_02",
                    "title": "ติดตั้งปั๊มน้ำอัตโนมัติและถังเก็บน้ำ",
                    "description": "เดินระบบท่อบายพาส (Bypass) ติดตั้งเช็ควาล์วและเบรกเกอร์คุมปั๊มน้ำ น้ำแรงสม่ำเสมอทุกชั้น",
                    "category_name": "งานระบบประปาและสุขาภิบาล",
                    "before_image": "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=600&auto=format&fit=crop&q=80",
                    "after_image": "https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=600&auto=format&fit=crop&q=80",
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
                }
            ],
            4: [  # ฉัตรชัย - งานปูนก่อสร้าง
                {
                    "item_id": "build_01",
                    "title": "รีโนเวทปูกระเบื้องห้องน้ำและห้องครัว",
                    "description": "รื้อกระเบื้องเดิม ทาน้ำยากันซึม 3 ชั้น ปูกระเบื้องแกรนิตโต้ 60x60 ซม. ยาแนวเรียบเนียนสวยงาม",
                    "category_name": "งานปูน ก่อสร้าง ต่อเติม ซ่อมแซม",
                    "before_image": "https://images.unsplash.com/photo-1590381105924-c72589b9ef3f?w=600&auto=format&fit=crop&q=80",
                    "after_image": "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=600&auto=format&fit=crop&q=80",
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
                },
                {
                    "item_id": "build_02",
                    "title": "ซ่อมแซมรอยแตกร้าวผนังและทาสีใหม่",
                    "description": "สกัดรอยร้าว อัดหมันด้วย PU Sealant ทาสีรองพื้นปูนเก่าและสีทับหน้ากันเชื้อรา 2 เที่ยว",
                    "category_name": "งานปูน ก่อสร้าง ต่อเติม ซ่อมแซม",
                    "before_image": "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=600&auto=format&fit=crop&q=80",
                    "after_image": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=600&auto=format&fit=crop&q=80",
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
                }
            ],
            5: [  # อนวัช - งานไม้
                {
                    "item_id": "wood_01",
                    "title": "บิวท์อินตู้เสื้อผ้าและชั้นวางทีวีไม้โมเดิร์น",
                    "description": "โครงสร้างไม้จริง ปิดผิวลามิเนตลายไม้เกรดพรีเมียม ติดตั้งบานพับ Soft-close แข็งแรง ทนทาน",
                    "category_name": "งานไม้และเฟอร์นิเจอร์บิวท์อิน",
                    "before_image": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=600&auto=format&fit=crop&q=80",
                    "after_image": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=600&auto=format&fit=crop&q=80",
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
                }
            ],
            6: [  # ธนกฤต - งานหลังคา
                {
                    "item_id": "roof_01",
                    "title": "ซ่อมรอยรั่วครอบสันหลังคาและเปลี่ยนกระเบื้อง",
                    "description": "รื้อครอบสันเดิมที่ปูนแตก ติดตั้งระบบครอบแห้ง (Dry Ridge) กันน้ำรั่วซึมได้ 100%",
                    "category_name": "งานซ่อมหลังคาและแก้ปัญหารั่วซึม",
                    "before_image": "https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?w=600&auto=format&fit=crop&q=80",
                    "after_image": "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=600&auto=format&fit=crop&q=80",
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
                }
            ]
        }

        # Clear existing duplicate documents in MongoDB worker_portfolios
        db.worker_portfolios.delete_many({})
        self.stdout.write("[*] Cleared old duplicate portfolio entries from MongoDB.")

        # Insert fresh unique showcases
        workers = WorkerProfile.objects.all()
        for w in workers:
            gallery = portfolios_by_worker.get(w.id, portfolios_by_worker[1])
            doc = {
                "worker_id": int(w.id),
                "gallery": gallery,
                "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            db.worker_portfolios.replace_one({"worker_id": int(w.id)}, doc, upsert=True)
            self.stdout.write(f" -> Created {len(gallery)} unique showcases for Worker #{w.id} ({w.user.full_name})")

        self.stdout.write(self.style.SUCCESS("[SUCCESS] MongoDB Worker Portfolios updated cleanly with HD Before/After images!"))
