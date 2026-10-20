# ช่างใกล้บ้าน (Local Skilled Worker Directory)
## ระบบประกาศและค้นหาช่างรับจ้างท้องถิ่น (Django Web Application)

**ผู้จัดทำ:** นายภูพิรัฐ แซ่โค้ว (รหัสประจำตัว 6812732119)  
**Requirement by:** นายมนต์พระกาญจน์ คำเหลือ (รหัสประจำตัว 6812732120)

---

## 📌 ภาพรวมของระบบ (Django Architecture)
ระบบ **ช่างใกล้บ้าน** พัฒนาขึ้นด้วย **Python 3 / Django Web Framework** ตามมาตรฐานสากล (Clean Modular Architecture) ผสมผสาน Frontend ด้วย HTML5 Semantic, Modern Glassmorphism CSS, JavaScript (Chart.js, AJAX Bookmarks) เพื่อเป็นศูนย์กลางเชื่อมโยงระหว่างช่างฝีมือรับจ้างท้องถิ่นและผู้ต้องการใช้บริการ

---

## 📂 โครงสร้างโฟลเดอร์ตามมาตรฐานสากล (Project Structure)
```
Requirements/
├── apps/                          # Modular Django Applications
│   ├── accounts/                  # User Model (Admin/Worker/Customer), Auth & Profile
│   ├── core/                      # Homepage, Search, Categories, Search Logs & Seed Command
│   ├── workers/                   # Worker Profiles, Skills, Services & Service Areas
│   ├── bookings/                  # Service Requests & Status Updates
│   ├── reviews/                   # 1-5 Star Ratings, Worker Replies & Moderation
│   ├── reports/                   # Problem & Inappropriate Behavior Reporting
│   └── dashboard/                 # Customer, Worker, and Admin Dashboards & Stats
├── local_worker_project/          # Project Root Settings (settings.py, urls.py, wsgi.py)
├── templates/                     # Reusable Django Templates (base.html, core, accounts, etc.)
├── static/                        # Static Assets (Custom CSS, JavaScript, Images)
├── media/                         # Media Uploads (Managed by Cloudinary Storage)
├── tmp/                           # โฟลเดอร์แยกเก็บไฟล์เดิมที่ไม่ใช้งาน
│   └── legacy_php/                # ไฟล์ระบบเดิมภาษา PHP (index.php, config, database, views)
├── manage.py                      # Django CLI Management Script
└── requirements.txt               # รายการ Dependencies (Django, Cloudinary, psycopg2, pymongo)

```

---

## 💻 วิธีการติดตั้งและเริ่มต้นใช้งาน (Quick Start)

### 1. ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```

### 2. รัน Migration และสร้างข้อมูลจำลอง (Seed Data)
```bash
python manage.py migrate
python manage.py seed_data
```

### 3. รันเซิร์ฟเวอร์สำหรับทดสอบ
```bash
python manage.py runserver
```
เข้าใช้งานผ่านเว็บเบราว์เซอร์ที่: **`http://127.0.0.1:8000`**

### 4. รันการทดสอบ Unit Tests
```bash
python manage.py test core
```

---

## 🔑 การจัดการบัญชีผู้ดูแลระบบ (Admin Access)
- สามารถสร้างบัญชีผู้ดูแลระบบ (Superuser) ใหม่ได้ด้วยคำสั่ง:
  ```bash
  python manage.py createsuperuser
  ```
- เข้าสู่ระบบจัดการผู้ดูแลระบบผ่านหน้าเว็บที่: **`/dashboard/`** หรือ **`/django-admin/`**

---

## 🚀 ฟังก์ชันเด่นของระบบ
1. **Multi-Role System:** 3 บทบาทชัดเจน (Admin, Worker, Customer) พร้อมระบบเปลี่ยนหน้าอัตโนมัติตามสิทธิ์
2. **Dynamic Worker Search & Logging:** ค้นหาช่างตามคำค้นหา หมวดหมู่งาน 10+ หมวดหมู่ และ 77 จังหวัด พร้อมบันทึก Search Log เพื่อวิเคราะห์ความต้องการในแต่ละพื้นที่
3. **Interactive Bookmarking:** กดบันทึกช่างที่ชื่นชอบแบบ AJAX ไม่ต้องโหลดหน้าใหม่
4. **Service Booking & Workflow:** ส่งคำขอรับบริการ ช่างตอบรับงาน และเปลี่ยนสถานะ (Requested -> In Progress -> Completed)
5. **Rating & Worker Reply:** รีวิว 1-5 ดาว ช่างตอบกลับรีวิว และแอดมินสามารถซ่อนรีวิวที่ไม่เหมาะสมได้
6. **Analytics & Charts:** กราฟสถิติหมวดหมู่งานยอดนิยม และคำค้นหายอดฮิตด้วย Chart.js บน Admin Dashboard
