import io
import os
from PIL import Image, ImageDraw, ImageFont
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from django.core.management.base import BaseCommand
from django.conf import settings


def set_cell_background(cell, fill_hex):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tc_pr.append(shd)


def set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tc_pr.append(tc_mar)


def create_clean_er_diagram(output_path):
    """สร้างภาพ ER Diagram ตามสไตล์อาจารย์กนิษฐา (Relational Schema ERD)"""
    width, height = 1200, 750
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Grid lines
    for x in range(0, width, 50):
        draw.line([(x, 0), (x, height)], fill=(245, 247, 250), width=1)
    for y in range(0, height, 50):
        draw.line([(0, y), (width, y)], fill=(245, 247, 250), width=1)

    entities = [
        ("users", 40, 50, 320, 310, [
            "id [PK, BigInt]",
            "email [Unique, Varchar]",
            "username [Unique, Varchar]",
            "role [ADMIN/WORKER/CUSTOMER]",
            "first_name, last_name",
            "phone_number",
            "avatar [Cloudinary Image]",
            "created_at [DateTime]"
        ], (30, 41, 59)),
        ("worker_profiles", 420, 50, 740, 330, [
            "id [PK, BigInt]",
            "user_id [FK, Unique, OneToOne]",
            "bio [Text]",
            "working_hours [Varchar]",
            "status [Pending/Approved/Rejected]",
            "is_available [Boolean]",
            "profile_image [Cloudinary Image]",
            "id_card_image [KYC Image]",
            "certificate_image [Cert Image]",
            "is_id_verified [Boolean]"
        ], (30, 41, 59)),
        ("categories", 850, 50, 1150, 240, [
            "id [PK, BigInt]",
            "category_name [Varchar]",
            "icon [Varchar]",
            "description [Text]",
            "is_active [Boolean]"
        ], (30, 41, 59)),
        ("provinces", 850, 300, 1150, 430, [
            "id [PK, BigInt]",
            "province_name [Unique, Varchar]"
        ], (30, 41, 59)),
        ("service_requests", 40, 410, 360, 690, [
            "id [PK, BigInt]",
            "customer_id [FK -> users.id]",
            "worker_id [FK -> worker_profiles.id]",
            "category_id [FK -> categories.id]",
            "status [Requested/Accepted/Done]",
            "details [Text]",
            "address_note [Varchar]",
            "preferred_date, time_slot",
            "problem_image [Cloudinary Image]",
            "created_at, updated_at"
        ], (30, 41, 59)),
        ("worker_services", 420, 410, 740, 550, [
            "id [PK, BigInt]",
            "worker_id [FK -> worker_profiles.id]",
            "category_id [FK -> categories.id]",
            "starting_price [Decimal]",
            "price_unit [/งาน, /จุด, /ตร.ม.]"
        ], (30, 41, 59)),
        ("reviews", 820, 500, 1150, 680, [
            "id [PK, BigInt]",
            "request_id [FK, Unique -> requests]",
            "customer_id [FK -> users.id]",
            "worker_id [FK -> worker_profiles.id]",
            "rating [Integer 1 - 5]",
            "comment [Text]",
            "worker_reply [Text]",
            "created_at [DateTime]"
        ], (30, 41, 59)),
    ]

    for title, x1, y1, x2, y2, fields, hdr_color in entities:
        draw.rounded_rectangle([x1 + 3, y1 + 3, x2 + 3, y2 + 3], radius=10, fill=(226, 232, 240))
        draw.rounded_rectangle([x1, y1, x2, y2], radius=10, fill=(248, 250, 252), outline=(100, 116, 139), width=2)
        draw.rounded_rectangle([x1, y1, x2, y1 + 30], radius=8, fill=hdr_color)
        draw.text((x1 + 14, y1 + 7), title, fill=(255, 255, 255))
        cur_y = y1 + 40
        for f in fields:
            draw.text((x1 + 14, cur_y), f, fill=(30, 41, 59))
            cur_y += 24

    # Connectors
    # 1. users -> worker_profiles (1:1)
    draw.line([(320, 140), (420, 140)], fill=(37, 99, 235), width=3)
    draw.text((345, 120), "1 : 1 (EXTENDS)", fill=(37, 99, 235))

    # 2. worker_profiles -> categories (worker_services 1:N)
    draw.line([(740, 140), (850, 140)], fill=(16, 185, 129), width=3)
    draw.text((765, 120), "1 : N", fill=(16, 185, 129))

    # 3. users -> service_requests (1:N)
    draw.line([(180, 310), (180, 410)], fill=(217, 119, 6), width=3)
    draw.text((190, 350), "1 : N (PLACES)", fill=(217, 119, 6))

    # 4. worker_profiles -> service_requests (1:N)
    draw.line([(420, 280), (360, 450)], fill=(217, 119, 6), width=3)
    draw.text((385, 340), "1 : N", fill=(217, 119, 6))

    # 5. service_requests -> reviews (1:1)
    draw.line([(360, 590), (820, 590)], fill=(147, 51, 234), width=3)
    draw.text((540, 570), "1 : 1 (REVIEWS)", fill=(147, 51, 234))

    # 6. worker_profiles -> worker_services (1:N)
    draw.line([(580, 330), (580, 410)], fill=(16, 185, 129), width=3)
    draw.text((590, 360), "1 : N (OFFERS)", fill=(16, 185, 129))

    img.save(output_path, format='PNG', quality=95)
    return output_path


def create_ui_mockup_image(title_th, subtitle_th, elements, output_path):
    """สร้างภาพจำลอง UI แต่ละหน้าเพื่อฝังในรายงาน Word"""
    width, height = 900, 520
    img = Image.new('RGB', (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Browser window mockup header
    draw.rounded_rectangle([20, 20, 880, 500], radius=16, fill=(255, 255, 255), outline=(203, 213, 225), width=2)
    draw.rounded_rectangle([20, 20, 880, 70], radius=14, fill=(241, 245, 249))
    # Browser buttons
    draw.ellipse([40, 40, 52, 52], fill=(239, 68, 68))
    draw.ellipse([60, 40, 72, 52], fill=(245, 158, 11))
    draw.ellipse([80, 40, 92, 52], fill=(34, 197, 94))
    # URL bar
    draw.rounded_rectangle([120, 34, 750, 58], radius=8, fill=(255, 255, 255), outline=(226, 232, 240))
    draw.text((140, 38), "https://local-worker.vercel.app - ช่างใกล้บ้าน", fill=(100, 116, 139))

    # Title Bar
    draw.text((450, 95), title_th, fill=(15, 23, 42), anchor="mm")
    draw.text((450, 125), subtitle_th, fill=(79, 70, 229), anchor="mm")
    draw.line([(50, 145), (850, 145)], fill=(226, 232, 240), width=2)

    # Content Boxes / Cards
    y = 165
    for elem_title, elem_desc, color_accent in elements:
        draw.rounded_rectangle([50, y, 850, y + 80], radius=12, fill=(255, 255, 255), outline=(226, 232, 240), width=2)
        draw.rounded_rectangle([50, y, 60, y + 80], radius=8, fill=color_accent)
        draw.text((80, y + 16), elem_title, fill=(15, 23, 42))
        draw.text((80, y + 46), elem_desc, fill=(100, 116, 139))
        y += 95

    img.save(output_path, format='PNG', quality=95)
    return output_path


class Command(BaseCommand):
    help = 'Build official Requirement document matching 6712732121.docx template'

    def handle(self, *args, **options):
        base_dir = settings.BASE_DIR
        self.stdout.write(self.style.NOTICE("[-] Generating Requirement Document matching sample format..."))

        # Generate Diagrams & UI Images
        er_path = base_dir / 'req_erd.png'
        create_clean_er_diagram(str(er_path))

        ui1_path = base_dir / 'req_ui_search.png'
        create_ui_mockup_image(
            "1. หน้าค้นหาและจับคู่ช่าง (Worker Search & Directory)",
            "ค้นหาช่างตามคำค้นหา หมวดหมู่งาน 10 หมวดหมู่ และ 77 จังหวัดทั่วไทย",
            [
                ("Search Box & Dynamic Filters", "ช่องกรองค้นหาตามคำค้นหา เช่น ช่างไฟ, ล้างแอร์, ซ่อมท่อ พร้อมเลือกจังหวัดและหมวดหมู่", (37, 99, 235)),
                ("Worker Cards Grid with Verified Badges", "แสดงการ์ดช่างพร้อมรูปโปรไฟล์ HD, ตรา Verified Badge, คะแนนรีวิวเฉลี่ย และราคาเริ่มต้น", (16, 185, 129)),
                ("AJAX Bookmark / Saved Worker", "ปุ่มกดบันทึกช่างที่ถูกใจลงรายการโปรดแบบทันทีโดยไม่ต้องโหลดหน้าเว็บใหม่", (245, 158, 11))
            ],
            str(ui1_path)
        )

        ui2_path = base_dir / 'req_ui_detail.png'
        create_ui_mockup_image(
            "2. หน้าโปรไฟล์ช่างและผลงานตัวอย่าง (Worker Profile & Portfolio)",
            "แสดงทักษะ อัตราค่าบริการ เอกสารยืนยันตัวตน และแกลเลอรีผลงาน Before/After",
            [
                ("Profile Header & Identity Badge", "รูปถ่ายช่าง, ข้อมูลติดต่อ, เวลาทำการ และตราเครื่องหมายช่างยืนยันตัวตน (KYC Verified)", (37, 99, 235)),
                ("Portfolio Showcase (Before & After)", "แสดงภาพถ่ายผลงานเปรียบเทียบ ก่อนทำ - หลังทำ จากฐานข้อมูล MongoDB เพื่อสร้างความมั่นใจ", (16, 185, 129)),
                ("Services & Price Table", "ตารางแสดงหมวดหมู่งานที่รับบริการ พร้อมระบุราคาเริ่มต้นและหน่วยราคา (/งาน, /จุด, /ตร.ม.)", (147, 51, 234))
            ],
            str(ui2_path)
        )

        ui3_path = base_dir / 'req_ui_booking.png'
        create_ui_mockup_image(
            "3. หน้าส่งคำขอจองบริการและแนบรูปหน้างาน (Service Request & Problem Upload)",
            "ระบบจองงานพร้อมแนบรูปถ่ายปัญหาหน้างานขึ้น Cloudinary และระบบเปลี่ยนสถานะงาน",
            [
                ("Booking Request Form", "ฟอร์มระบุรายละเอียดงานที่ต้องการซ่อมแซม วันที่สะดวก ช่วงเวลา (เช้า/บ่าย/เย็น) และสถานที่", (37, 99, 235)),
                ("Problem Image Upload (Cloudinary)", "อัปโหลดภาพถ่ายจุดชำรุดหรือหน้างานจริง โดยระบบจะจัดเก็บบน Cloudinary อัตโนมัติ", (217, 119, 6)),
                ("Workflow State Transition", "ระบบอัปเดตสถานะงาน: รอดำเนินการ -> ช่างตอบรับ -> กำลังทำงาน -> เสร็จสมบูรณ์", (16, 185, 129))
            ],
            str(ui3_path)
        )

        ui4_path = base_dir / 'req_ui_dashboard.png'
        create_ui_mockup_image(
            "4. แผงควบคุมและสถิติภาพรวม (Admin & Worker Dashboard)",
            "แดชบอร์ดจัดการงาน ตรวจสอบเอกสาร KYC อนุมัติช่าง และกราฟสถิติความต้องการในแต่ละพื้นที่",
            [
                ("Stat Counters & Overview Cards", "ตัวเลขสรุปคำขอใหม่, งานที่กำลังทำ, งานเสร็จสมบูรณ์ และคะแนนรีวิวเฉลี่ยของช่าง", (37, 99, 235)),
                ("KYC Verification & Worker Approval", "เมนูตรวจสอบรูปบัตรประชาชนและใบประกอบวิชาชีพของช่างก่อนอนุมัติเปิดรับงาน", (16, 185, 129)),
                ("Interactive Chart.js Analytics", "กราฟสถิติวิเคราะห์หมวดหมู่งานยอดนิยม และคำค้นหายอดฮิตในแต่ละจังหวัดจาก Search Logs", (147, 51, 234))
            ],
            str(ui4_path)
        )

        # Create DOCX Document
        doc = docx.Document()

        # Margins
        for sec in doc.sections:
            sec.top_margin = Inches(1.25)
            sec.bottom_margin = Inches(1.0)
            sec.left_margin = Inches(1.25)
            sec.right_margin = Inches(1.0)

        # Style
        normal_style = doc.styles['Normal']
        normal_style.font.name = 'TH Sarabun New'
        normal_style.font.size = Pt(16)
        normal_style.font.color.rgb = RGBColor(0, 0, 0)
        normal_style.paragraph_format.line_spacing = 1.15
        normal_style.paragraph_format.space_after = Pt(4)

        def add_p(text, font_size=16, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=0, space_after=4):
            p = doc.add_paragraph()
            p.alignment = align
            p.paragraph_format.space_before = Pt(space_before)
            p.paragraph_format.space_after = Pt(space_after)
            p.paragraph_format.line_spacing = 1.15
            run = p.add_run(text)
            run.font.name = 'TH Sarabun New'
            run.font.size = Pt(font_size)
            run.font.bold = bold
            return p

        # ==========================================
        # 1. หน้าปก (COVER)
        # ==========================================
        add_p("", font_size=20, space_before=50)
        add_p("รายงาน", font_size=22, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_p("เรื่อง ระบบประกาศและค้นหาช่างรับจ้างท้องถิ่น (ช่างใกล้บ้าน)", font_size=20, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=12, space_after=40)

        add_p("นายภูพิรัฐ แซ่โค้ว   รหัสนักศึกษา 6812732119", font_size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_p("นายมนต์พระกาญจน์ คำเหลือ   รหัสนักศึกษา 6812732120", font_size=16, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=40)

        add_p("เสนอ", font_size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_p("ผู้ช่วยศาสตราจารย์ ดร.กนิษฐา อินธิชิต", font_size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=50)

        add_p("รายงานนี้เป็นส่วนหนึ่งของรายวิชาระบบฐานข้อมูล ( 4123202+ )", font_size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_p("ภาคเรียนที่ 1 ปีการศึกษา 2569", font_size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_p("สาขาวิทยาการคอมพิวเตอร์ คณะศิลปศาสตร์และวิทยาศาสตร์", font_size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_p("มหาวิทยาลัยราชภัฏศรีสะเกษ", font_size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

        doc.add_page_break()

        # ==========================================
        # 2. สารบัญ (TABLE OF CONTENTS)
        # ==========================================
        add_p("สารบัญ", font_size=20, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18)

        add_p("Requirement\t\t\t\t\t\t\t\t\t\t           1", font_size=16)
        add_p("แผนภาพความสัมพันธ์ของข้อมูล (E-R Diagram)\t\t\t\t                       2", font_size=16)
        add_p("ข้อมูลตารางทั้งหมด (Data Dictionary)\t\t\t\t\t                       4", font_size=16)
        add_p("User Interface (UI)\t\t\t\t                			                       6", font_size=16)

        doc.add_page_break()

        # ==========================================
        # 3. หน้า 1: REQUIREMENT
        # ==========================================
        add_p("1", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_p("Requirement", font_size=18, bold=True, space_after=6)
        add_p("ระบบการจัดการและประกาศค้นหาช่างรับจ้างท้องถิ่น (ช่างใกล้บ้าน)")
        add_p("สามารถสร้างโปรไฟล์ช่างได้ และมีการตั้งราคาเริ่มต้นและหน่วยราคาได้ เช่น สร้างรายการบริการ งานไฟฟ้า 450 บาท/งาน")
        add_p("สามารถสร้างและเลือกหมวดหมู่งานบริการ (10 หมวดหมู่หลัก) และเลือกพื้นที่ให้บริการ 77 จังหวัดได้")
        add_p("สามารถค้นหาช่างตามคำค้นหา หมวดหมู่งาน และจังหวัดได้ พร้อมระบบบันทึก Search Log เพื่อวิเคราะห์ความต้องการในแต่ละพื้นที่")
        add_p("สามารถส่งคำขอรับบริการ (Booking) โดยเลือกวันที่สะดวก ช่วงเวลา และแนบรูปถ่ายปัญหาหน้างานจริงได้")
        add_p("สามารถประเมินผลงานและรีวิว 1-5 ดาว พร้อมข้อคิดเห็น และช่างสามารถเขียนตอบกลับรีวิวได้")
        add_p("สามารถยืนยันตัวตนช่างด้วยการอัปโหลดบัตรประชาชนและใบประกอบวิชาชีพ (KYC) เพื่อขอรับตรา Verified Badge")
        
        add_p("การทำงานของระบบ", font_size=16, bold=True, space_before=10, space_after=4)
        add_p("หน้าแรกเมื่อเปิดเข้ามาจะมีแถบค้นหาช่าง หมวดหมู่บริการยอดนิยม และรายการช่างแนะนำ พร้อมปุ่มสมัครสมาชิกและเข้าสู่ระบบ เมื่อค้นหาช่างจะแสดงการ์ดข้อมูลช่างพร้อมปุ่มดูโปรไฟล์ เมื่อเข้าไปในหน้าโปรไฟล์ช่างจะแสดงรายละเอียดทักษะ ค่าบริการเริ่มต้น แกลเลอรีผลงาน ก่อนทำ-หลังทำ (Before & After) และปุ่มส่งคำขอจองบริการ")

        add_p("วิธีการใช้งาน", font_size=16, bold=True, space_before=10, space_after=4)
        add_p("ผู้ใช้ทั่วไปสามารถค้นหาช่างตามหมวดหมู่และจังหวัด จากนั้นเลือกช่างที่ต้องการเพื่อดูรายละเอียด แล้วกรอกฟอร์มขอรับบริการพร้อมแนบรูปจุดที่ชำรุด เมื่อส่งคำขอแล้ว ช่างจะได้รับการแจ้งเตือนและสามารถกดตอบรับงาน (Accepted) ดำเนินการซ่อมแซม (In Progress) และเมื่อเสร็จสิ้นงาน (Completed) ลูกค้าสามารถเข้ามากดเขียนรีวิวให้คะแนนช่างได้")

        add_p("ข้อมูลหลัก", font_size=16, bold=True, space_before=10, space_after=4)
        add_p("ผู้ใช้ทั่วไป (ลูกค้า) - ค้นหาช่าง, บันทึกช่างที่ถูกใจ (Bookmark), ส่งคำขอรับบริการ, แนบรูปปัญหาหน้างาน, เขียนรีวิว")
        add_p("ช่างรับจ้าง (Worker) - แก้ไขโปรไฟล์, กำหนดราคาเริ่มต้นและหน่วยราคา, เลือกพื้นที่บริการ, อัปโหลดเอกสาร KYC, จัดการคำขอจองงาน, ตอบกลับรีวิว, เพิ่มรูปผลงาน ก่อน-หลัง")
        add_p("ผู้ดูแลระบบ (Admin) - ตรวจสอบและอนุมัติช่าง, ตรวจสอบเอกสาร KYC, จัดการหมวดหมู่บริการ, ตรวจสอบรายงานปัญหา (Reports), ดู Analytics Dashboard")

        add_p("ฟังก์ชันหลัก", font_size=16, bold=True, space_before=10, space_after=4)
        add_p("ระบบค้นหาและตัวกรองช่าง - ค้นหาแบบ Dynamic ตามคำค้นหา หมวดหมู่ และ 77 จังหวัด")
        add_p("ระบบจัดการคำขอจองงาน - จัดการสถานะคำขอ: รอดำเนินการ (Requested) -> ตอบรับงาน (Accepted) -> กำลังดำเนินการ (In Progress) -> เสร็จสมบูรณ์ (Completed) -> ยกเลิก (Cancelled)")
        add_p("ระบบจัดเก็บสื่อ Cloudinary - จัดเก็บรูปโปรไฟล์, บัตรประชาชน (KYC), ใบประกอบวิชาชีพ และรูปหน้างานบน Cloud พร้อมระบบ Content-Hash ป้องกันการสร้างรูปซ้ำ และระบบลบไฟล์ขยะอัตโนมัติ")
        add_p("ระบบ Hybrid Database - ทำงานบน Cloud Database 100% (Neon Serverless PostgreSQL + MongoDB Atlas) ไม่มีฐานข้อมูลบนเครื่อง Local")
        add_p("มีฟังก์ชันใช้งานสำหรับมือถือและคอมพิวเตอร์ (Responsive Web Design)")
        add_p("รูปแบบเว็บเข้าใจง่าย ใช้งานง่าย สไตล์ Glassmorphism สีสันอ่านง่ายไม่ซับซ้อน")

        doc.add_page_break()

        # ==========================================
        # 4. หน้า 2: E-R DIAGRAM
        # ==========================================
        add_p("2", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_p("แผนภาพความสัมพันธ์ของข้อมูล (E-R Diagram)", font_size=18, bold=True, space_after=10)

        if os.path.exists(str(er_path)):
            doc.add_picture(str(er_path), width=Inches(6.2))

        add_p("1. เอนทิตี (Entity Description)", font_size=16, bold=True, space_before=12, space_after=4)
        add_p("ระบบประกอบด้วย 7 เอนทิตีหลักที่ทำงานร่วมกันในฐานข้อมูลเชิงสัมพันธ์ (Relational Database) ดังนี้:")
        add_p("users: เก็บข้อมูลบัญชีผู้ใช้งานทั้งหมดในระบบ แบ่งตามบทบาท (Admin, Worker, Customer) พร้อมรูป Avatar")
        add_p("worker_profiles: เก็บข้อมูลโปรไฟล์เฉพาะของช่างรับจ้าง เช่น ประวัติแนะนำตัว, วันเวลาทำการ, สถานะการอนุมัติ, รูปโปรไฟล์, รูปบัตรประชาชน (KYC), รูปใบประกอบวิชาชีพ และตรา Verified Badge")
        add_p("categories: เก็บข้อมูลหมวดหมู่งานบริการ 10 หมวดหมู่หลัก (เช่น งานระบบไฟฟ้า, งานแอร์, งานประปา, งานก่อสร้าง)")
        add_p("provinces: เก็บข้อมูล 77 จังหวัดทั่วประเทศไทยสำหรับใช้เป็นขอบเขตพื้นที่ให้บริการ")
        add_p("worker_services: เอนทิตีตัวกลางที่ทำหน้าที่จับคู่ช่างกับหมวดหมู่งาน เพื่อกำหนดราคาเริ่มต้นและหน่วยราคา")
        add_p("worker_service_areas: เอนทิตีตัวกลางที่กำหนดว่าช่างแต่ละคนสะดวกให้บริการในจังหวัดใดบ้าง")
        add_p("service_requests: เป็นศูนย์กลางข้อมูลคำขอจองงาน เก็บรายละเอียดงาน, สถานะงาน, วันและช่วงเวลาที่นัดหมาย และรูปถ่ายหน้างานจริง")
        add_p("reviews: เก็บข้อมูลการประเมินคะแนน 1-5 ดาว ความคิดเห็นของลูกค้า และข้อความตอบกลับจากช่าง")
        add_p("saved_workers: เก็บข้อมูลรายการช่างที่ลูกค้ากดบันทึกไว้เป็นรายการโปรด (Bookmark)")

        doc.add_page_break()

        # ==========================================
        # 5. หน้า 3: RELATIONSHIP ANALYSIS
        # ==========================================
        add_p("3", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_p("2. คำอธิบายความสัมพันธ์ (Relationship Analysis)", font_size=16, bold=True, space_after=8)
        add_p("ความสัมพันธ์ระหว่างข้อมูลถูกออกแบบตามหลักการ Normalization เพื่อลดความซ้ำซ้อนและรักษาความถูกต้องของข้อมูล (Data Integrity) ดังนี้:")

        add_p("users — worker_profiles (EXTENDS): ความสัมพันธ์แบบ One-to-One (1:1)", bold=True)
        add_p("ผู้ใช้ 1 บัญชีที่มีบทบาทเป็น WORKER จะมีข้อมูลโปรไฟล์ช่างได้เพียง 1 รายการเท่านั้น โดยใช้ user_id เป็นคีย์เชื่อมโยงแบบ Unique")

        add_p("users — service_requests (PLACES): ความสัมพันธ์แบบ One-to-Many (1:M)", bold=True)
        add_p("ลูกค้า 1 คน สามารถส่งคำขอจองงานได้หลายครั้ง (Many Requests) แต่คำขอจอง 1 ใบ จะต้องระบุลูกค้าผู้สร้างคำขอเพียงคนเดียวเท่านั้น โดยใช้ customer_id เป็นตัวเชื่อม")

        add_p("worker_profiles — service_requests (RECEIVES): ความสัมพันธ์แบบ One-to-Many (1:M)", bold=True)
        add_p("ช่าง 1 คน สามารถรับงานและมีรายการคำขอจองงานได้หลายรายการ แต่คำขอจอง 1 ใบจะส่งถึงช่างผู้รับงานเพียงคนเดียว โดยใช้ worker_id เป็นตัวเชื่อม")

        add_p("categories — service_requests (CATEGORIZED_BY): ความสัมพันธ์แบบ One-to-Many (1:M)", bold=True)
        add_p("หมวดหมู่งาน 1 หมวดหมู่ สามารถปรากฏอยู่ในคำขอจองงานได้หลายรายการ โดยใช้ category_id เป็นตัวอ้างอิง")

        add_p("worker_profiles — worker_services (OFFERS): ความสัมพันธ์แบบ One-to-Many (1:M)", bold=True)
        add_p("ช่าง 1 คน สามารถรับงานได้หลายหมวดหมู่พร้อมกำหนดราคาเริ่มต้นและหน่วยราคาที่แตกต่างกันในแต่ละบริการ")

        add_p("worker_profiles — worker_service_areas (COVERS): ความสัมพันธ์แบบ One-to-Many (1:M)", bold=True)
        add_p("ช่าง 1 คน สามารถเลือกพื้นที่ให้บริการได้หลายจังหวัด เพื่อให้ลูกค้าในจังหวัดนั้นๆ สามารถค้นหาช่างพบได้")

        add_p("service_requests — reviews (REVIEWS): ความสัมพันธ์แบบ One-to-One (1:1)", bold=True)
        add_p("คำขอจองงานที่เสร็จสิ้นสมบูรณ์ (Completed) 1 รายการ จะสามารถสร้างรีวิวประเมินความพึงพอใจได้เพียง 1 ครั้งเท่านั้น เพื่อป้องกันการปั๊มรีวิวซ้ำซ้อน โดยใช้ request_id เป็น Unique Foreign Key")

        doc.add_page_break()

        # ==========================================
        # 6. หน้า 4: DATA DICTIONARY
        # ==========================================
        add_p("4", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_p("ข้อมูลตารางทั้งหมด (Data Dictionary)", font_size=18, bold=True, space_after=8)
        add_p("Entity ทั้งหมด", font_size=16, bold=True)

        add_p("ตารางผู้ใช้งาน (users)", font_size=16, bold=True, space_before=6)
        add_p("ใช้เก็บข้อมูลบัญชีผู้ใช้งานทั้งหมดในระบบเพื่อจัดการสิทธิ์และการเข้าสู่ระบบ")
        add_p("โครงสร้าง: ประกอบด้วยรหัสผู้ใช้ (id [PK]), อีเมล (email [Unique]), ชื่อผู้ใช้ (username [Unique]), บทบาท (role: ADMIN/WORKER/CUSTOMER), ชื่อจริง (first_name), นามสกุล (last_name), เบอร์โทรศัพท์ (phone_number), รูปประจำตัว (avatar [Cloudinary Image]) และวันที่สร้างบัญชี (created_at)")
        add_p("ตัวอย่างข้อมูล: ritonz@admin.com (ภูพิรัฐ แซ่โค้ว / ADMIN), sompong.elec@example.com (สมพงษ์ ช่างไฟ / WORKER) และ customer@example.com (สมชาย ใจดี / CUSTOMER)")

        add_p("ตารางโปรไฟล์ช่าง (workers / worker_profiles)", font_size=16, bold=True, space_before=8)
        add_p("ใช้เก็บข้อมูลประวัติ ความเชี่ยวชาญ และเอกสารยืนยันตัวตนของช่างรับจ้าง")
        add_p("โครงสร้าง: ประกอบด้วยรหัสโปรไฟล์ (id [PK]), รหัสผู้ใช้ (user_id [FK, Unique]), ประวัติแนะนำตัว (bio), เวลาทำการ (working_hours), สถานะการอนุมัติ (status: PENDING/APPROVED/REJECTED/SUSPENDED), สถานะพร้อมรับงาน (is_available), รูปโปรไฟล์ (profile_image), รูปบัตรประชาชน (id_card_image), รูปใบประกอบวิชาชีพ (certificate_image) และสถานะยืนยันตัวตน (is_id_verified)")
        add_p("ตัวอย่างข้อมูล: ช่างสมพงษ์ (สถานะ: APPROVED, ประสบการณ์ 15 ปี, มีใบรับรองช่างไฟฟ้า, ผ่านการยืนยันตัวตน Verified Badge)")

        add_p("ตารางหมวดหมู่บริการ (categories)", font_size=16, bold=True, space_before=8)
        add_p("ใช้เก็บประเภทงานบริการและไอคอนเพื่อแสดงผลให้ลูกค้าเลือกค้นหา")
        add_p("โครงสร้าง: ประกอบด้วยรหัสหมวดหมู่ (id [PK]), ชื่อหมวดหมู่ (category_name), ไอคอน (icon), คำอธิบาย (description) และสถานะเปิดใช้งาน (is_active)")
        add_p("ตัวอย่างข้อมูล: มี 10 หมวดหมู่หลัก เช่น งานระบบไฟฟ้าและแสงสว่าง (fa-bolt), งานเครื่องปรับอากาศและล้างแอร์ (fa-snowflake), งานระบบประปาและสุขาภิบาล (fa-faucet-drip)")

        doc.add_page_break()

        # ==========================================
        # 7. หน้า 5: DATA DICTIONARY (CONT.)
        # ==========================================
        add_p("5", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)

        add_p("ตารางบริการและราคาช่าง (worker_services)", font_size=16, bold=True, space_before=4)
        add_p("ทำหน้าที่กำหนดทักษะงานที่ช่างรับทำและอัตราค่าบริการเริ่มต้น")
        add_p("โครงสร้าง: ประกอบด้วยรหัสรายการ (id [PK]), รหัสช่าง (worker_id [FK]), รหัสหมวดหมู่ (category_id [FK]), ราคาเริ่มต้น (starting_price) และหน่วยราคา (price_unit เช่น /งาน, /เครื่อง, /จุด, /ตร.ม., /ชั่วโมง)")
        add_p("ตัวอย่างข้อมูล: ช่างสมพงษ์ ให้บริการงานระบบไฟฟ้า ราคาเริ่มต้น 450.00 บาท/งาน และงานติดตั้งกล้องวงจรปิด 600.00 บาท/จุด")

        add_p("ตารางคำขอรับบริการ (service_requests)", font_size=16, bold=True, space_before=8)
        add_p("ใช้เก็บข้อมูลภาพรวมของการจองงาน สถานะงาน และหลักฐานหน้างาน")
        add_p("โครงสร้าง: เชื่อมโยงลูกค้าผ่าน customer_id [FK], ช่างผู้รับงาน worker_id [FK], หมวดหมู่งาน category_id [FK], รายละเอียดงาน (details), สถานะงาน (status: REQUESTED/ACCEPTED/IN_PROGRESS/COMPLETED/CANCELLED), วันที่นัดหมาย (preferred_date), ช่วงเวลา (preferred_time_slot: MORNING/AFTERNOON/EVENING/ANY), รูปถ่ายปัญหาหน้างาน (problem_image [Cloudinary Image]) และวันเวลาสร้างคำขอ (created_at)")
        add_p("ตัวอย่างข้อมูล: คำขอ #1 โดยคุณสมชาย ถึงช่างสมพงษ์ งานติดตั้งตู้ไฟ Consumer Unit นัดหมายช่วงเช้า สถานะ COMPLETED")

        add_p("ตารางการประเมินและรีวิว (reviews)", font_size=16, bold=True, space_before=8)
        add_p("ใช้บันทึกคะแนนความพึงพอใจ ข้อคิดเห็นของลูกค้า และคำตอบกลับของช่าง")
        add_p("โครงสร้าง: ประกอบด้วยรหัสรีวิว (id [PK]), รหัสคำขอจอง (request_id [FK, Unique]), รหัสลูกค้า (customer_id [FK]), รหัสช่าง (worker_id [FK]), คะแนนดาว (rating: 1-5 ดาว), ข้อคิดเห็น (comment), ข้อความตอบกลับของช่าง (worker_reply), วันที่ตอบกลับ (worker_replied_at) และสถานะซ่อนรีวิว (is_hidden)")
        add_p("ตัวอย่างข้อมูล: รีวิวคำขอ #1 ให้ 5 ดาว ข้อคิดเห็น 'ช่างสมพงษ์ทำงานเรียบร้อยมากครับ เก็บงานเนียน' ช่างตอบกลับ 'ขอบพระคุณมากครับ'")

        add_p("ตารางพื้นที่ให้บริการ (worker_service_areas)", font_size=16, bold=True, space_before=8)
        add_p("ใช้บันทึกจังหวัดที่ช่างสะดวกเดินทางไปปฏิบัติงาน")
        add_p("โครงสร้าง: รหัสรายการ (id [PK]), รหัสช่าง (worker_id [FK]) และรหัสจังหวัด (province_id [FK])")
        add_p("ตัวอย่างข้อมูล: ช่างสมพงษ์ เลือกให้บริการใน 4 จังหวัด คือ กรุงเทพมหานคร, นนทบุรี, ปทุมธานี และสมุทรปราการ")

        add_p("   ทุกตารางมีการระบุ Primary Key และ Foreign Key อย่างชัดเจนเพื่อรักษาความถูกต้องของข้อมูล (Data Integrity) การรองรับระบบ Cloud Storage: ฟิลด์รูปภาพทั้งหมด (profile_image, id_card_image, certificate_image, problem_image, avatar) ถูกผูกและจัดเก็บบน Cloudinary พร้อมทั้งเชื่อมโยงข้อมูลแกลเลอรีผลงาน Before/After และประวัติ Search Logs บน MongoDB Atlas ซึ่งสอดคล้องกับสถาปัตยกรรม Hybrid Cloud ของโครงการ", font_size=15, space_before=8)

        doc.add_page_break()

        # ==========================================
        # 8. หน้า 6: USER INTERFACE (UI)
        # ==========================================
        add_p("6", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_p("User Interface (UI)", font_size=18, bold=True, space_after=8)

        add_p("1. หน้าค้นหาและจับคู่ช่าง (Worker Search & Directory)", font_size=16, bold=True)
        add_p("หน้านี้จะดึงข้อมูลมาจากตาราง worker_profiles, categories, worker_services และ provinces เพื่อแสดงผลช่างรับจ้างในรูปแบบการ์ดที่ค้นหาได้ง่าย")
        add_p("ลักษณะการออกแบบ: แสดงผลแถบค้นหาแบบรวมศูนย์ (Search Bar) พร้อมตัวกรองหมวดหมู่งานและ 77 จังหวัด")
        add_p("สถานะและการแสดงผล:")
        add_p("รูปโปรไฟล์ช่าง: แสดงรูปโปรไฟล์ระดับ HD ดึงจาก Cloudinary หรือระบบ Fallback Avatar")
        add_p("ตรา Verified Badge: แสดงเครื่องหมายถูกสีฟ้าสำหรับช่างที่ผ่านการยืนยันตัวตนด้วยบัตรประชาชน (KYC)")
        add_p("ปุ่มดูโปรไฟล์: เมื่อคลิกที่การ์ดช่าง จะเปิดเข้าสู่หน้าแสดงรายละเอียดโปรไฟล์ของช่างคนนั้นทันที")

        if os.path.exists(str(ui1_path)):
            doc.add_picture(str(ui1_path), width=Inches(5.8))

        add_p("2. หน้าโปรไฟล์ช่างและผลงานตัวอย่าง (Worker Profile & Portfolio)", font_size=16, bold=True, space_before=10)
        add_p("ทำหน้าที่แสดงรายละเอียดประวัติ ค่าบริการเริ่มต้น และแกลเลอรีผลงานตัวอย่าง โดยดึงข้อมูลจากตาราง worker_profiles, worker_services และคอลเลกชัน worker_portfolios ใน MongoDB Atlas")
        add_p("การแสดงผล: ข้อมูลประวัติและเวลาทำการ, ตารางราคาเริ่มต้นตามหมวดหมู่งาน, และภาพถ่ายผลงานเปรียบเทียบ ก่อนทำ - หลังทำ (Before & After)")
        add_p("ฟังก์ชันการทำงาน:")
        add_p("ลูกค้าสามารถคลิกดูรูปผลงานขยายใหญ่เพื่อดูคุณภาพงานจริงก่อนตัดสินใจจ้าง")
        add_p("มีปุ่ม 'ส่งคำขอรับบริการ (Book Service)' และปุ่ม 'บันทึกช่างที่ถูกใจ (Bookmark)'")

        if os.path.exists(str(ui2_path)):
            doc.add_picture(str(ui2_path), width=Inches(5.8))

        doc.add_page_break()

        # ==========================================
        # 9. หน้า 7: USER INTERFACE (CONT.)
        # ==========================================
        add_p("7", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)

        add_p("3. หน้าส่งคำขอจองบริการและแนบรูปหน้างาน (Service Request & Problem Upload)", font_size=16, bold=True)
        add_p("หน้านี้สอดคล้องกับตาราง service_requests โดยให้ลูกค้ากรอกข้อมูลความต้องการและแนบรูปจุดชำรุด")
        add_p("ฟังก์ชันการทำงาน:")
        add_p("การเลือกเวลา: สามารถเลือกวันที่สะดวกและระบุช่วงเวลา (ช่วงเช้า 08:00-12:00 น., ช่วงบ่าย 13:00-17:00 น., ช่วงเย็น หรือสะดวกทุกเวลา)")
        add_p("การอัปโหลดรูปหน้างาน: ปุ่มสำหรับถ่ายภาพหรือเลือกไฟล์รูปภาพปัญหาหน้างาน เพื่อส่งไปจัดเก็บบน Cloudinary")
        add_p("การบันทึก: เมื่อกดยืนยัน ระบบจะสร้างคำขอใหม่สถานะ 'REQUESTED' และแจ้งเตือนไปยังช่างผู้รับงานทันที")

        if os.path.exists(str(ui3_path)):
            doc.add_picture(str(ui3_path), width=Inches(5.8))

        add_p("4. แผงควบคุมและสถิติภาพรวม (Admin & Worker Dashboard)", font_size=16, bold=True, space_before=10)
        add_p("แสดงผลแดชบอร์ดการจัดการสำหรับช่างและผู้ดูแลระบบ โดยดึงข้อมูลจาก service_requests, reviews, search_logs และ MongoDB")
        add_p("รายละเอียดแดชบอร์ด:")
        add_p("แผงควบคุมช่าง: แสดงกล่องสรุปจำนวนคำขอใหม่, งานที่กำลังทำ, งานเสร็จสมบูรณ์, คะแนนรีวิวเฉลี่ย และเครื่องมือเพิ่มรูปผลงาน Before/After")
        add_p("แผงควบคุมผู้ดูแลระบบ (Admin): แสดงสถิติภาพรวมทั้งระบบ, ตารางตรวจสอบเอกสาร KYC บัตรประชาชนของช่างเพื่อกดอนุมัติ, และกราฟสถิติ Chart.js แสดงหมวดหมู่งานยอดนิยมและคำค้นหายอดฮิตในแต่ละจังหวัด")

        if os.path.exists(str(ui4_path)):
            doc.add_picture(str(ui4_path), width=Inches(5.8))

        # Save DOCX
        output_filename = '6812732119_Requirement_ระบบช่างใกล้บ้าน.docx'
        out_path = base_dir / output_filename
        doc.save(str(out_path))

        # Copy to the exact sample name format as well
        copy_filename = 'Requirement_ระบบช่างใกล้บ้าน_ตรงตามตัวอย่าง_6712732121.docx'
        doc.save(str(base_dir / copy_filename))

        self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Official Requirement Document created successfully at: {out_path}"))
