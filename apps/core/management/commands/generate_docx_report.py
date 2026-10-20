import os
from PIL import Image, ImageDraw, ImageFont
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from django.core.management.base import BaseCommand
from django.conf import settings


def set_cell_background(cell, fill_hex):
    """Set table cell background color"""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tc_pr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set table cell internal margins"""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tc_pr.append(tc_mar)


def create_er_diagram_image(output_path):
    """Create a crisp ER Diagram image using Pillow to embed into docx"""
    width, height = 1200, 750
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Background subtle grid
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill=(245, 247, 250), width=1)
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill=(245, 247, 250), width=1)

    # Colors
    header_color = (30, 41, 59)
    box_border = (71, 85, 105)
    box_bg = (248, 250, 252)

    entities = [
        # (title, x1, y1, x2, y2, [fields])
        ("USERS (ตารางผู้ใช้)", 50, 60, 320, 320, [
            "+ id (PK, BigInt)",
            "+ email (Unique, Varchar)",
            "+ username (Unique, Varchar)",
            "+ role (Admin / Worker / Customer)",
            "+ first_name / last_name",
            "+ phone_number",
            "+ avatar (Cloudinary Image)",
            "+ created_at (DateTime)"
        ]),
        ("WORKER_PROFILES (โปรไฟล์ช่าง)", 420, 60, 740, 340, [
            "+ id (PK, BigInt)",
            "+ user_id (FK, Unique, OneToOne)",
            "+ bio (Text)",
            "+ working_hours (Varchar)",
            "+ status (Pending/Approved/Rejected)",
            "+ is_available (Boolean)",
            "+ profile_image (Cloudinary Image)",
            "+ id_card_image (KYC Image)",
            "+ certificate_image (Cert Image)",
            "+ is_id_verified (Boolean)"
        ]),
        ("CATEGORIES (หมวดหมู่งาน)", 850, 60, 1140, 260, [
            "+ id (PK, BigInt)",
            "+ category_name (Varchar)",
            "+ icon (Varchar)",
            "+ description (Text)",
            "+ is_active (Boolean)"
        ]),
        ("PROVINCES (77 จังหวัด)", 850, 320, 1140, 460, [
            "+ id (PK, BigInt)",
            "+ province_name (Unique, Varchar)"
        ]),
        ("SERVICE_REQUESTS (คำขอจองงาน)", 50, 420, 370, 700, [
            "+ id (PK, BigInt)",
            "+ customer_id (FK -> Users)",
            "+ worker_id (FK -> WorkerProfile)",
            "+ category_id (FK -> Category)",
            "+ status (Requested/Accepted/Done)",
            "+ details (Text)",
            "+ address_note (Varchar)",
            "+ preferred_date / time_slot",
            "+ problem_image (Cloudinary Image)",
            "+ created_at / updated_at"
        ]),
        ("WORKER_SERVICES (ราคาและทักษะ)", 430, 420, 730, 560, [
            "+ id (PK, BigInt)",
            "+ worker_id (FK -> WorkerProfile)",
            "+ category_id (FK -> Category)",
            "+ starting_price (Decimal)",
            "+ price_unit (/งาน, /จุด, /ตร.ม.)"
        ]),
        ("REVIEWS (รีวิวและการประเมิน)", 800, 520, 1140, 700, [
            "+ id (PK, BigInt)",
            "+ request_id (FK, Unique -> ServiceReq)",
            "+ customer_id (FK -> Users)",
            "+ worker_id (FK -> WorkerProfile)",
            "+ rating (1 - 5 Stars)",
            "+ comment (Text)",
            "+ worker_reply (Text)",
            "+ created_at (DateTime)"
        ]),
    ]

    for title, x1, y1, x2, y2, fields in entities:
        # Box shadow & background
        draw.rounded_rectangle([x1 + 3, y1 + 3, x2 + 3, y2 + 3], radius=10, fill=(226, 232, 240))
        draw.rounded_rectangle([x1, y1, x2, y2], radius=10, fill=box_bg, outline=box_border, width=2)
        # Header bar
        draw.rounded_rectangle([x1, y1, x2, y1 + 32], radius=8, fill=header_color)
        draw.text((x1 + 14, y1 + 8), title, fill=(255, 255, 255))
        # Fields
        cur_y = y1 + 42
        for f in fields:
            draw.text((x1 + 14, cur_y), f, fill=(30, 41, 59))
            cur_y += 24

    # Connectors / Relationship lines
    # 1. Users -> Worker_Profiles (1:1)
    draw.line([(320, 150), (420, 150)], fill=(37, 99, 235), width=3)
    draw.text((345, 130), "1 : 1", fill=(37, 99, 235))

    # 2. Worker_Profiles -> Categories (Worker_Services N:M)
    draw.line([(740, 150), (850, 150)], fill=(16, 185, 129), width=3)
    draw.text((770, 130), "1 : N", fill=(16, 185, 129))

    # 3. Users -> Service_Requests (1:N)
    draw.line([(180, 320), (180, 420)], fill=(217, 119, 6), width=3)
    draw.text((190, 360), "1 : N", fill=(217, 119, 6))

    # 4. Worker_Profiles -> Service_Requests (1:N)
    draw.line([(420, 300), (370, 450)], fill=(217, 119, 6), width=3)
    draw.text((380, 350), "1 : N", fill=(217, 119, 6))

    # 5. Service_Requests -> Reviews (1:1)
    draw.line([(370, 600), (800, 600)], fill=(147, 51, 234), width=3)
    draw.text((560, 580), "1 : 1 (Completed Job)", fill=(147, 51, 234))

    # 6. Worker_Profiles -> Worker_Services
    draw.line([(580, 340), (580, 420)], fill=(16, 185, 129), width=3)
    draw.text((590, 370), "1 : N", fill=(16, 185, 129))

    img.save(output_path, format='PNG', quality=95)
    return output_path


class Command(BaseCommand):
    help = 'Generate formal Thai academic Word report (.docx) for Requirements and System Architecture'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("[-] Generating formal Word (.docx) report..."))
        
        base_dir = settings.BASE_DIR
        er_image_path = base_dir / 'er_diagram_generated.png'
        create_er_diagram_image(str(er_image_path))
        self.stdout.write(self.style.SUCCESS("[OK] Generated ER diagram image."))

        doc = docx.Document()

        # Set Standard Page Margins (Top: 1.25", Left: 1.25", Right: 1.0", Bottom: 1.0")
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(1.25)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.25)
            section.right_margin = Inches(1.0)

        # Style configurations
        normal_style = doc.styles['Normal']
        normal_style.font.name = 'TH Sarabun New'
        normal_style.font.size = Pt(16)
        normal_style.font.color.rgb = RGBColor(0, 0, 0)
        normal_style.paragraph_format.line_spacing = 1.15
        normal_style.paragraph_format.space_after = Pt(4)

        # Helper to add paragraphs
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

        # Helper for headings
        def add_h(text, level=1):
            if level == 1:
                return add_p(text, font_size=18, bold=True, space_before=12, space_after=6)
            elif level == 2:
                return add_p(text, font_size=16, bold=True, space_before=8, space_after=4)
            else:
                return add_p(text, font_size=16, bold=True, space_before=4, space_after=2)

        # ==========================================
        # 1. หน้าปก (COVER PAGE)
        # ==========================================
        add_p("", font_size=20, space_before=40)
        add_p("รายงาน", font_size=22, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_p("เรื่อง : การวิเคราะห์และออกแบบระบบประกาศและค้นหาช่างรับจ้างท้องถิ่น", font_size=20, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=10)
        add_p("กรณีศึกษา : ระบบช่างใกล้บ้าน (Local Skilled Worker Directory)", font_size=18, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=50)

        add_p("เสนอ", font_size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_p("ผู้ช่วยศาสตราจารย์ กณิชฑ์ ธีรสิทธางกูร", font_size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=50)

        add_p("จัดทำโดย", font_size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_p("นายภูพิรัฐ แซ่โค้ว   รหัสนักศึกษา 6812732119", font_size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_p("นายมนต์พระกาญจน์ คำเหลือ   รหัสนักศึกษา 6812732120", font_size=16, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=60)

        add_p("สาขาวิชา : วิทยาการคอมพิวเตอร์  คณะ : ศิลปศาสตร์และวิทยาศาสตร์", font_size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=20)
        add_p("รายงานฉบับนี้เป็นส่วนหนึ่งของวิชาการวิเคราะห์และออกแบบระบบ", font_size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_p("ภาคเรียนที่ 1 ปีการศึกษา 2569", font_size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_p("มหาวิทยาลัยราชภัฏศรีสะเกษ", font_size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

        doc.add_page_break()

        # ==========================================
        # 2. คำนำ (PREFACE - หน้า ก)
        # ==========================================
        add_p("ก", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_p("คำนำ", font_size=20, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18)

        add_p("        รายงานฉบับนี้จัดทำขึ้นเพื่อนำเสนอเอกสารข้อกำหนดความต้องการและการออกแบบสถาปัตยกรรมระบบ (Software Requirements Specification & System Architecture) ของโครงการ \"ระบบประกาศและค้นหาช่างรับจ้างท้องถิ่น (ช่างใกล้บ้าน)\" ซึ่งพัฒนาขึ้นเพื่อแก้ปัญหาการขาดศูนย์กลางค้นหาช่างฝีมือที่มีคุณภาพและตรวจสอบได้ในระดับท้องถิ่น ตลอดจนเพิ่มโอกาสในการสร้างรายได้แก่ช่างฝีมือในชุมชน")
        add_p("        เนื้อหาภายในเล่มประกอบด้วยการวิเคราะห์ความเป็นมาและวัตถุประสงค์ของระบบ, ข้อกำหนดความต้องการเชิงหน้าที่ (Functional Requirements) และไม่ใช่เชิงหน้าที่ (Non-Functional Requirements), การออกแบบสถาปัตยกรรมระบบแบบผสมผสาน (Hybrid Cloud Architecture) ระหว่าง Neon Serverless PostgreSQL และ MongoDB Atlas, การจัดทำแผนผังความสัมพันธ์ของข้อมูล (ER Diagram), พจนานุกรมข้อมูล (Data Dictionary) ตลอดจนการออกแบบระบบจัดเก็บสื่อแบบ Cloud Storage บน Cloudinary พร้อมกลไกป้องกันไฟล์ซ้ำซ้อนและระบบกำจัดไฟล์ขยะอัตโนมัติ")
        add_p("        ผู้จัดทำหวังเป็นอย่างยิ่งว่ารายงานฉบับนี้จะสะท้อนถึงการวิเคราะห์และออกแบบระบบตามมาตรฐานวิชาชีพซอฟต์แวร์ และเป็นประโยชน์ต่อผู้ที่สนใจศึกษาสถาปัตยกรรมเว็บแอปพลิเคชันสมัยใหม่ หากมีข้อผิดพลาดประการใด ผู้จัดทำขอน้อมรับเพื่อนำไปปรับปรุงแก้ไขในโอกาสต่อไป")

        add_p("", font_size=16, space_before=30)
        add_p("คณะผู้จัดทำ", font_size=16, bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_p("กันยายน 2569", font_size=16, align=WD_ALIGN_PARAGRAPH.RIGHT)

        doc.add_page_break()

        # ==========================================
        # 3. สารบัญ (TABLE OF CONTENTS - หน้า ข)
        # ==========================================
        add_p("ข", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_p("สารบัญ", font_size=20, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18)

        toc_table = doc.add_table(rows=1, cols=2)
        toc_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        toc_table.autofit = False
        toc_table.columns[0].width = Inches(5.0)
        toc_table.columns[1].width = Inches(1.0)

        hdr_cells = toc_table.rows[0].cells
        hdr_cells[0].text = "เรื่อง"
        hdr_cells[1].text = "หน้า"
        for c in hdr_cells:
            for p in c.paragraphs:
                p.runs[0].font.bold = True
                p.runs[0].font.size = Pt(16)
                p.runs[0].font.name = 'TH Sarabun New'

        toc_items = [
            ("คำนำ", "ก"),
            ("สารบัญ", "ข"),
            ("บทที่ 1 บทนำ", "1"),
            ("   1.1 ความเป็นมาและความสำคัญ", "1"),
            ("   1.2 วัตถุประสงค์ของระบบ", "1"),
            ("   1.3 ขอบเขตของโครงการ", "2"),
            ("   1.4 เทคโนโลยีที่ใช้ในการพัฒนาระบบ", "2"),
            ("บทที่ 2 ข้อกำหนดความต้องการของระบบ (System Requirements)", "3"),
            ("   2.1 บทบาทของผู้ใช้งานในระบบ (User Roles)", "3"),
            ("   2.2 ข้อกำหนดเชิงหน้าที่ (Functional Requirements)", "3"),
            ("   2.3 ข้อกำหนดที่ไม่ใช่เชิงหน้าที่ (Non-Functional Requirements)", "5"),
            ("บทที่ 3 การออกแบบสถาปัตยกรรมและฐานข้อมูล (Database Design)", "6"),
            ("   3.1 แผนภาพความสัมพันธ์ของข้อมูล (ER Diagram)", "6"),
            ("   3.2 พจนานุกรมข้อมูล (Data Dictionary - PostgreSQL)", "7"),
            ("   3.3 โครงสร้างข้อมูล NoSQL (MongoDB Document Schemas)", "9"),
            ("บทที่ 4 ระบบจัดเก็บสื่อและความปลอดภัย (Cloud Storage & Security)", "10"),
            ("   4.1 การเชื่อมต่อ Cloudinary Media Storage", "10"),
            ("   4.2 ระบบป้องกันการอัปโหลดไฟล์ซ้ำ (Content-Hash Deduplication)", "10"),
            ("   4.3 ระบบลบรูปภาพอัตโนมัติ (Automated Cleanup Signals)", "11"),
            ("บทที่ 5 สรุปผลและการพัฒนาต่อยอด", "12"),
            ("บรรณานุกรม / แหล่งอ้างอิง", "13"),
        ]

        for title, page_str in toc_items:
            row_cells = toc_table.add_row().cells
            row_cells[0].text = title
            row_cells[1].text = page_str
            for c in row_cells:
                set_cell_margins(c, top=40, bottom=40, left=60, right=60)
                for p in c.paragraphs:
                    p.paragraph_format.line_spacing = 1.15
                    for r in p.runs:
                        r.font.name = 'TH Sarabun New'
                        r.font.size = Pt(16)

        doc.add_page_break()

        # ==========================================
        # 4. บทที่ 1 บทนำ (PAGE 1)
        # ==========================================
        add_p("1", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_h("บทที่ 1 บทนำ", level=1)
        
        add_h("1.1 ความเป็นมาและความสำคัญ", level=2)
        add_p("        ในยุคปัจจุบัน ปัญหาการซ่อมแซมและบำรุงรักษาบ้านเรือน ที่พักอาศัย หรือสำนักงาน ไม่ว่าจะเป็นงานระบบไฟฟ้า ประปา เครื่องปรับอากาศ ปูนก่อสร้าง งานไม้ หรือโครงหลังคา ถือเป็นความต้องการพื้นฐานในชีวิตประจำวัน อย่างไรก็ตาม ผู้ว่าจ้างส่วนใหญ่มักประสบปัญหาการค้นหาช่างฝีมือในท้องถิ่น ขาดช่องทางติดต่อโดยตรง ขาดการตรวจสอบความน่าเชื่อถือ และไม่มีระบบติดตามสถานะงานที่ชัดเจน")
        add_p("        ขณะเดียวกัน ช่างฝีมืออิสระในชุมชนมักขาดเครื่องมือในการประชาสัมพันธ์ทักษะ ค่าบริการ และพื้นที่ให้บริการของตนเอง ทำให้เสียโอกาสในการรับงาน โครงการ \"ช่างใกล้บ้าน (Local Skilled Worker Directory)\" จึงได้รับการพัฒนาขึ้นเพื่อทำหน้าที่เป็นตัวกลางในการจับคู่ความต้องการระหว่างผู้ว่าจ้างและช่างฝีมือท้องถิ่นอย่างมีมาตรฐาน")

        add_h("1.2 วัตถุประสงค์ของระบบ", level=2)
        add_p("1. เพื่อพัฒนาระบบค้นหาและจับคู่ช่างฝีมือตามพื้นที่ให้บริการ (77 จังหวัด) และหมวดหมู่บริการ")
        add_p("2. เพื่อสร้างระบบตรวจสอบและยืนยันตัวตนของช่าง (KYC & Verified Badge) ด้วยบัตรประชาชนและใบประกอบวิชาชีพ")
        add_p("3. เพื่อสร้างระบบคำขอรับบริการ (Service Request Workflow) และระบบประเมินรีวิว 1-5 ดาว")
        add_p("4. เพื่อประยุกต์ใช้สถาปัตยกรรมคลาวด์แบบผสมผสาน (Hybrid Database) ระหว่าง Relational PostgreSQL, NoSQL MongoDB Atlas และ Cloudinary Media Storage")

        add_h("1.3 ขอบเขตของโครงการ", level=2)
        add_p("● ผู้ใช้งาน 3 บทบาท: ผู้ดูแลระบบ (Admin), ช่างรับจ้าง (Worker), และลูกค้า/ผู้ว่าจ้าง (Customer)")
        add_p("● การค้นหา: รองรับการค้นหาตามคำค้นหา (Keyword), หมวดหมู่งาน 10 หมวดหมู่ และจังหวัด 77 จังหวัด")
        add_p("● นโยบายความปลอดภัยฐานข้อมูล: ทำงานบน Cloud Database (Neon Serverless PostgreSQL และ MongoDB Atlas) 100% ไม่อนุญาตให้ใช้ SQLite ภายในเครื่อง")
        add_p("● ระบบสื่อ: รูปโปรไฟล์, บัตรประชาชน (KYC), ใบประกอบวิชาชีพ และรูปหน้างาน จัดเก็บบน Cloudinary")

        add_h("1.4 เทคโนโลยีที่ใช้ในการพัฒนาระบบ", level=2)
        add_p("● Backend Framework: Python 3.13 / Django 5.x Web Framework")
        add_p("● Relational Database: Neon Serverless PostgreSQL (Cloud-based)")
        add_p("● NoSQL Document Store: MongoDB Atlas (Search Logs, Portfolio Showcase, Real-time Chat)")
        add_p("● Media Cloud Storage: Cloudinary API Storage with Django Integration")
        add_p("● Frontend: Semantic HTML5, Modern CSS Glassmorphism, JavaScript, Chart.js")

        doc.add_page_break()

        # ==========================================
        # 5. บทที่ 2 ข้อกำหนดความต้องการ (PAGE 3)
        # ==========================================
        add_p("3", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_h("บทที่ 2 ข้อกำหนดความต้องการของระบบ (System Requirements)", level=1)

        add_h("2.1 บทบาทของผู้ใช้งานในระบบ (User Roles)", level=2)
        add_p("1. ผู้ดูแลระบบ (Admin): มีสิทธิ์ตรวจสอบและอนุมัติโปรไฟล์ช่าง, ตรวจสอบเอกสาร KYC, จัดการหมวดหมู่บริการ, ตรวจสอบรายงานปัญหา และดูภาพรวมสถิติผ่าน Admin Dashboard")
        add_p("2. ช่างรับจ้าง (Worker): มีสิทธิ์สร้างและแก้ไขโปรไฟล์, กำหนดทักษะและราคาเริ่มต้น, เลือกพื้นที่ให้บริการ, อัปโหลดเอกสาร KYC, จัดการคำขอจองงาน, ตอบกลับรีวิวลูกค้า และจัดการผลงาน ก่อน-หลัง (Before/After)")
        add_p("3. ผู้ว่าจ้าง/ลูกค้า (Customer): มีสิทธิ์ค้นหาช่าง, บันทึกช่างที่ถูกใจ (Bookmark), ส่งคำขอจองงานพร้อมแนบรูปหน้างาน, ติดตามสถานะงาน และเขียนรีวิวให้คะแนนหลังงานเสร็จสิ้น")

        add_h("2.2 ข้อกำหนดเชิงหน้าที่ (Functional Requirements)", level=2)
        add_p("● [FR-01] ระบบยืนยันตัวตนและความปลอดภัย: รองรับการเข้าสู่ระบบด้วย Email/Username, ระบบป้องกัน Brute-force Login Lockout, การจัดการสิทธิ์ Role-Based Access Control")
        add_p("● [FR-02] ระบบค้นหาและบันทึกประวัติ: ค้นหาตามคำค้นหา หมวดหมู่งาน และจังหวัด พร้อมบันทึก Search Log ลง MongoDB เพื่อนำไปวิเคราะห์คำค้นหายอดฮิตบนแดชบอร์ด")
        add_p("● [FR-03] ระบบคำขอรับบริการ (Booking Workflow): ลูกค้าส่งคำขอจอง -> ช่างตอบรับงาน (Accepted) -> กำลังดำเนินงาน (In Progress) -> งานเสร็จสมบูรณ์ (Completed) หรือยกเลิก (Cancelled)")
        add_p("● [FR-04] ระบบประเมินและรีวิว: ลูกค้าสามารถให้คะแนน 1-5 ดาว พร้อมข้อคิดเห็น และช่างสามารถตอบกลับข้อคิดเห็นได้ 1 ครั้ง")
        add_p("● [FR-05] ระบบผลงานตัวอย่าง (Portfolio Showcase): ช่างสามารถเพิ่มผลงานเปรียบเทียบภาพก่อนทำและหลังทำ (Before & After) จัดเก็บบน MongoDB Atlas")

        add_h("2.3 ข้อกำหนดที่ไม่ใช่เชิงหน้าที่ (Non-Functional Requirements)", level=2)
        add_p("● [NFR-01] ด้านความปลอดภัย (Security): รหัสผ่านเข้ารหัสด้วย PBKDF2/SHA256, รองรับ CSRF Token, XSS Protection, Session Cookie HttpOnly")
        add_p("● [NFR-02] ด้านสถาปัตยกรรม (Cloud Architecture): ฐานข้อมูลและสื่อทำงานบน Cloud 100% รองรับการ Deploy บน Serverless Platform (Vercel)")
        add_p("● [NFR-03] ด้านประสิทธิภาพ (Performance): โครงสร้างตารางมี Indexing, การเชื่อมโยงรูปภาพผ่าน CDN Cloudinary มีความเร็วในการโหลดสูง")

        doc.add_page_break()

        # ==========================================
        # 6. บทที่ 3 การออกแบบสถาปัตยกรรมและฐานข้อมูล (PAGE 6)
        # ==========================================
        add_p("6", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_h("บทที่ 3 การออกแบบสถาปัตยกรรมและฐานข้อมูล (Database Design)", level=1)

        add_h("3.1 แผนภาพความสัมพันธ์ของข้อมูล (Entity-Relationship Diagram: ER Diagram)", level=2)
        add_p("        แผนภาพ ER Diagram แสดงโครงสร้างและความสัมพันธ์ของเอนทิตีหลักในฐานข้อมูลเชิงสัมพันธ์ (Relational Database) ของระบบช่างใกล้บ้าน ดังภาพด้านล่าง:")

        if os.path.exists(str(er_image_path)):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_picture(str(er_image_path), width=Inches(6.2))
            add_p("ภาพที่ 3.1 แผนภาพความสัมพันธ์ของข้อมูล (Entity-Relationship Diagram)", font_size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)

        add_h("3.2 พจนานุกรมข้อมูล (Data Dictionary - PostgreSQL)", level=2)
        
        table_dict = doc.add_table(rows=1, cols=4)
        table_dict.alignment = WD_TABLE_ALIGNMENT.CENTER
        table_dict.columns[0].width = Inches(1.8)
        table_dict.columns[1].width = Inches(1.2)
        table_dict.columns[2].width = Inches(1.2)
        table_dict.columns[3].width = Inches(1.8)

        hdrs = table_dict.rows[0].cells
        hdrs[0].text = "ชื่อฟิลด์ (Field Name)"
        hdrs[1].text = "ประเภท (Type)"
        hdrs[2].text = "คีย์ (Key)"
        hdrs[3].text = "คำอธิบาย (Description)"
        for c in hdrs:
            set_cell_background(c, "E2E8F0")
            for p in c.paragraphs:
                p.runs[0].font.bold = True
                p.runs[0].font.name = 'TH Sarabun New'

        fields_data = [
            ("users.id", "BigInt", "PK", "รหัสประจำตัวผู้ใช้งาน"),
            ("users.email", "Varchar(254)", "Unique", "อีเมลสำหรับเข้าสู่ระบบ"),
            ("users.role", "Varchar(20)", "-", "บทบาท (ADMIN/WORKER/CUSTOMER)"),
            ("users.avatar", "Varchar(255)", "-", "URL รูปโปรไฟล์บน Cloudinary"),
            ("workers.id", "BigInt", "PK", "รหัสโปรไฟล์ช่าง"),
            ("workers.user_id", "BigInt", "FK, Unique", "เชื่อมโยงตาราง users (1:1)"),
            ("workers.status", "Varchar(20)", "-", "สถานะการอนุมัติโปรไฟล์"),
            ("workers.profile_image", "Varchar(255)", "-", "รูปโปรไฟล์ช่างบน Cloudinary"),
            ("workers.id_card_image", "Varchar(255)", "-", "รูปบัตรประชาชน KYC บน Cloudinary"),
            ("workers.certificate_image", "Varchar(255)", "-", "รูปใบประกอบวิชาชีพบน Cloudinary"),
            ("service_requests.id", "BigInt", "PK", "รหัสคำขอรับบริการ"),
            ("service_requests.status", "Varchar(20)", "-", "สถานะงาน (Requested->Completed)"),
            ("service_requests.problem_image", "Varchar(255)", "-", "รูปปัญหาหน้างานบน Cloudinary"),
            ("reviews.rating", "Integer", "-", "คะแนนความพึงพอใจ (1-5 ดาว)"),
        ]

        for f_name, f_type, f_key, f_desc in fields_data:
            r = table_dict.add_row().cells
            r[0].text = f_name
            r[1].text = f_type
            r[2].text = f_key
            r[3].text = f_desc
            for c in r:
                set_cell_margins(c, top=30, bottom=30, left=40, right=40)
                for p in c.paragraphs:
                    p.paragraph_format.line_spacing = 1.15
                    for run in p.runs:
                        run.font.name = 'TH Sarabun New'
                        run.font.size = Pt(14)

        add_h("3.3 โครงสร้างข้อมูล NoSQL (MongoDB Document Collections)", level=2)
        add_p("● Collection: worker_portfolios: จัดเก็บแกลเลอรีผลงานตัวอย่าง Before/After แยกตาม worker_id เพื่อความยืดหยุ่นสูง")
        add_p("● Collection: search_logs: จัดเก็บบันทึกประวัติคำค้นหา หมวดหมู่ จังหวัด และ IP สำหรับนำไปคำนวณกราฟสถิติ")
        add_p("● Collection: chat_messages: จัดเก็บข้อความแชทสนทนาระหว่างลูกค้าและช่าง พร้อมกำหนดดัชนี TTL (Time-To-Live 90 วัน)")

        doc.add_page_break()

        # ==========================================
        # 7. บทที่ 4 ระบบจัดเก็บสื่อและความปลอดภัย (PAGE 10)
        # ==========================================
        add_p("10", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_h("บทที่ 4 สถาปัตยกรรมระบบจัดเก็บสื่อและความปลอดภัย (Storage & Security)", level=1)

        add_h("4.1 การเชื่อมต่อ Cloudinary Media Storage", level=2)
        add_p("        ระบบได้เชื่อมต่อเข้ากับบริการ Cloudinary ผ่านแพ็กเกจ django-cloudinary-storage เพื่อทำหน้าที่เป็น Cloud Media Storage โดยสมบูรณ์ ทำให้ระบบไม่ต้องพึ่งพา Local Disk ภายในเครื่อง และสามารถทำงานบน Serverless Cloud Platform เช่น Vercel ได้อย่างมีประสิทธิภาพ")

        add_h("4.2 ระบบป้องกันการสร้างรูปซ้ำ (Content-Hash Deduplication)", level=2)
        add_p("        เพื่อป้องกันการอัปโหลดไฟล์รูปภาพซ้ำซ้อนจนสิ้นเปลืองพื้นที่จัดเก็บบน Cloudinary ระบบได้พัฒนาคลาส HashedUploadTo ใน core.cloudinary_utils ซึ่งจะคำนวณค่า SHA-256 Hash จากเนื้อหาของไฟล์รูปภาพจริง")
        add_p("        หากผู้ใช้อัปโหลดไฟล์รูปภาพเดิมซ้ำ แม้จะเปลี่ยนชื่อไฟล์ ระบบจะได้ค่า Hash เดิมและสร้างชื่อไฟล์แบบเดียวกัน ทำให้ Asset บน Cloudinary ชี้ไปยังไฟล์เดิมโดยอัตโนมัติ พร้อมทั้งแก้ปัญหาชื่อไฟล์ภาษาไทยได้อย่างเบ็ดเสร็จ")

        add_h("4.3 ระบบลบรูปภาพอัตโนมัติ (Automated Cleanup Signals)", level=2)
        add_p("        เพื่อป้องกันปัญหาไฟล์ขยะตกค้างบน Cloudinary ระบบได้สร้าง Django Signals ใน core.signals ดังนี้:")
        add_p("1. post_delete Signal: เมื่อมีการลบข้อมูล WorkerProfile, ServiceRequest หรือ User ในฐานข้อมูล ระบบจะเรียกคำสั่ง cloudinary.uploader.destroy() เพื่อลบไฟล์ที่เกี่ยวข้องออกจาก Cloudinary ทันที")
        add_p("2. pre_save Signal: เมื่อผู้ใช้อัปโหลดรูปภาพใหม่มาแทนที่รูปเดิม ระบบจะตรวจสอบหา Public ID ของรูปเดิมและส่งคำสั่งลบออกจาก Cloudinary โดยอัตโนมัติ")

        doc.add_page_break()

        # ==========================================
        # 8. บทที่ 5 สรุปผลและการพัฒนาต่อยอด (PAGE 12)
        # ==========================================
        add_p("12", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_h("บทที่ 5 สรุปผลและการพัฒนาต่อยอด", level=1)

        add_h("5.1 สรุปผลการพัฒนาระบบ", level=2)
        add_p("        ระบบ \"ช่างใกล้บ้าน (Local Skilled Worker Directory)\" ได้รับการพัฒนาขึ้นตามข้อกำหนดความต้องการและมาตรฐานสถาปัตยกรรมซอฟต์แวร์สมัยใหม่ โดยสามารถตอบโจทย์การจับคู่งานระหว่างผู้ว่าจ้างและช่างรับจ้างในท้องถิ่น มีระบบยืนยันตัวตน (KYC) ระบบติดตามสถานะงาน และระบบประเมินรีวิวที่โปร่งใส ฐานข้อมูล Relational บน Neon PostgreSQL และ NoSQL บน MongoDB Atlas ตลอดจน Cloudinary Media Storage ทำงานประสานกันได้อย่างสมบูรณ์")

        add_h("5.2 แนวทางการพัฒนาต่อยอดในอนาคต", level=2)
        add_p("1. ระบบชำระเงินออนไลน์ (Payment Gateway & Escrow): รองรับ PromptPay QR Code พร้อมระบบพักเงินจนกว่าลูกค้าจะยืนยันงานเสร็จสิ้น")
        add_p("2. ระบบพิกัดแผนที่ (Geolocation Routing): นำ Google Maps API มาช่วยคำนวณระยะทางจริงระหว่างบ้านลูกค้าและช่าง")
        add_p("3. ระบบแชทแบบ Real-time: พัฒนาระบบส่งข้อความผ่าน WebSocket เพื่อให้ติดต่อได้ทันที")

        doc.add_page_break()

        # ==========================================
        # 9. บรรณานุกรม (PAGE 13)
        # ==========================================
        add_p("13", font_size=14, align=WD_ALIGN_PARAGRAPH.RIGHT)
        add_h("บรรณานุกรม / แหล่งอ้างอิง", level=1)

        references = [
            "1. Django Software Foundation. (2026). Django Web Framework Documentation (Version 5.x). Retrieved from https://docs.djangoproject.com/",
            "2. Neon Inc. (2026). Serverless Postgres Architecture and Connection Pooling. Retrieved from https://neon.tech/docs/",
            "3. MongoDB Inc. (2026). MongoDB Atlas Multi-Cloud Database Documentation. Retrieved from https://www.mongodb.com/docs/atlas/",
            "4. Cloudinary Ltd. (2026). Cloudinary Django Integration & Storage Management. Retrieved from https://cloudinary.com/documentation/django_integration",
            "5. Chart.js Community. (2026). HTML5 Responsive Charting Library. Retrieved from https://www.chartjs.org/docs/",
            "6. กิตติ ภักดีวัฒนะกุล. (2565). การวิเคราะห์และออกแบบระบบ (Systems Analysis and Design). กรุงเทพฯ: เคทีพี พับลิชชิ่ง."
        ]

        for ref in references:
            add_p(ref, font_size=16, space_after=8)

        # Save DOCX file in project root
        output_docx_filename = 'รายงาน_การวิเคราะห์และออกแบบระบบช่างใกล้บ้าน.docx'
        output_docx_path = base_dir / output_docx_filename
        doc.save(str(output_docx_path))
        self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Generated Word document at: {output_docx_path}"))
