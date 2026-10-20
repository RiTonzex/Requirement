import io
import math
from PIL import Image, ImageDraw, ImageFont
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from workers.models import WorkerProfile
from bookings.models import ServiceRequest

User = get_user_model()


def create_gradient_image(width, height, top_color, bottom_color):
    """สร้างพื้นหลัง Gradient สวยงาม"""
    base = Image.new('RGB', (width, height), top_color)
    top_r, top_g, top_b = top_color
    bot_r, bot_g, bot_b = bottom_color

    draw = ImageDraw.Draw(base)
    for y in range(height):
        ratio = y / float(height)
        r = int(top_r + (bot_r - top_r) * ratio)
        g = int(top_g + (bot_g - top_g) * ratio)
        b = int(top_b + (bot_b - top_b) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return base


def create_worker_avatar(name_th, role_th, color_theme, badge_text="ช่างมืออาชีพ"):
    """สร้างภาพโปรไฟล์ช่างตัวอย่างระดับ HD (600x600)"""
    width, height = 600, 600
    top_c, bot_c = color_theme
    img = create_gradient_image(width, height, top_c, bot_c)
    draw = ImageDraw.Draw(img)

    # วาดวงกลมพื้นหลังตกแต่ง
    draw.ellipse([30, 30, width - 30, height - 30], outline=(255, 255, 255, 60), width=4)
    draw.ellipse([150, 100, 450, 400], fill=(255, 255, 255, 220))

    # วาดรูปหน้าคน/ช่าง (Head + Torso Silhouette)
    # Head
    draw.ellipse([230, 140, 370, 280], fill=top_c)
    # หมวกเซฟตี้ / Hardhat
    draw.polygon([(200, 170), (400, 170), (370, 120), (230, 120)], fill=(245, 158, 11))
    draw.rectangle([190, 165, 410, 178], fill=(217, 119, 6))

    # Torso
    draw.pieslice([170, 280, 430, 520], 180, 360, fill=top_c)

    # Card ด้านล่างพร้อมชื่อและตำแหน่ง
    draw.rounded_rectangle([60, 430, 540, 540], radius=20, fill=(255, 255, 255))
    
    # วาดข้อความ (Fallback Font)
    draw.text((300, 460), f"ช่าง{name_th}", fill=(15, 23, 42), anchor="mm")
    draw.text((300, 495), f"{role_th} | {badge_text}", fill=(79, 70, 229), anchor="mm")

    # บันทึกลง BytesIO
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=92)
    return ContentFile(buf.getvalue())


def create_user_avatar(name_th, role_title, bg_color):
    """สร้างภาพ Avatar ผู้ใช้ทั่วไป (400x400)"""
    width, height = 400, 400
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # วงกลมรอบ
    draw.ellipse([20, 20, 380, 380], outline=(255, 255, 255), width=6)
    
    # ตัวอักษรย่อตรงกลาง
    initial = name_th[0] if name_th else "U"
    draw.ellipse([100, 80, 300, 280], fill=(255, 255, 255, 230))
    draw.ellipse([140, 110, 260, 230], fill=bg_color)
    draw.pieslice([80, 240, 320, 440], 180, 360, fill=bg_color)

    # ชื่อและบทบาท
    draw.rounded_rectangle([40, 310, 360, 370], radius=16, fill=(255, 255, 255))
    draw.text((200, 330), name_th, fill=(15, 23, 42), anchor="mm")
    draw.text((200, 352), role_title, fill=(99, 102, 241), anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    return ContentFile(buf.getvalue())


def create_document_mockup(doc_type="ID_CARD", title="บัตรประชาชน"):
    """สร้างภาพเอกสารจำลอง KYC / ใบประกอบวิชาชีพ (700x450)"""
    width, height = 700, 450
    bg = (248, 250, 252) if doc_type == "ID_CARD" else (255, 251, 235)
    border_color = (2, 132, 199) if doc_type == "ID_CARD" else (217, 119, 6)

    img = Image.new('RGB', (width, height), bg)
    draw = ImageDraw.Draw(img)

    # กรอบเอกสาร
    draw.rounded_rectangle([20, 20, 680, 430], radius=24, outline=border_color, width=5)
    
    # Header แถบสี
    draw.rounded_rectangle([20, 20, 680, 90], radius=20, fill=border_color)
    draw.text((350, 55), f"OFFICIAL VERIFIED DOCUMENT: {title}", fill=(255, 255, 255), anchor="mm")

    # รูปถ่ายติดบัตร
    draw.rectangle([60, 130, 220, 330], fill=(226, 232, 240), outline=(148, 163, 184), width=2)
    draw.ellipse([100, 160, 180, 240], fill=(100, 116, 139))
    draw.pieslice([70, 250, 210, 370], 180, 360, fill=(100, 116, 139))

    # เส้นข้อความจำลอง
    draw.rectangle([260, 140, 620, 170], fill=(203, 213, 225))
    draw.rectangle([260, 190, 560, 215], fill=(226, 232, 240))
    draw.rectangle([260, 235, 520, 260], fill=(226, 232, 240))
    draw.rectangle([260, 280, 480, 305], fill=(226, 232, 240))

    # ตราประทับ Official Stamp
    draw.ellipse([500, 300, 640, 410], outline=(22, 163, 74), width=4)
    draw.text((570, 355), "VERIFIED KYC", fill=(22, 163, 74), anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    return ContentFile(buf.getvalue())


def create_problem_mockup(title_th, cat_name, color_theme):
    """สร้างภาพหน้างาน / ปัญหาการซ่อม (800x500)"""
    width, height = 800, 500
    top_c, bot_c = color_theme
    img = create_gradient_image(width, height, top_c, bot_c)
    draw = ImageDraw.Draw(img)

    # กล่องภาพหน้างาน
    draw.rounded_rectangle([40, 40, 760, 460], radius=24, outline=(255, 255, 255, 180), width=4)

    # สัญลักษณ์หน้างาน
    draw.rounded_rectangle([250, 100, 550, 300], radius=16, fill=(255, 255, 255, 220))
    draw.rectangle([340, 160, 460, 240], fill=top_c)
    draw.polygon([(400, 120), (330, 180), (470, 180)], fill=(239, 68, 68))

    # ป้ายกำกับ
    draw.rounded_rectangle([100, 340, 700, 420], radius=16, fill=(255, 255, 255))
    draw.text((400, 365), f"ภาพถ่ายหน้างาน: {title_th}", fill=(15, 23, 42), anchor="mm")
    draw.text((400, 395), f"หมวดหมู่งาน: {cat_name}", fill=(79, 70, 229), anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=90)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = 'Generate and upload realistic demo images for all workers, users, KYC, certificates, and bookings to Cloudinary'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("[*] Generating and uploading sample images to Cloudinary..."))

        # 1. User Avatars
        admin = User.objects.filter(role='ADMIN').first()
        if admin:
            self.stdout.write(f" -> Uploading avatar for Admin ({admin.full_name})...")
            avatar_file = create_user_avatar(admin.first_name, "ผู้ดูแลระบบ (Admin)", (30, 41, 59))
            admin.avatar.save('admin_avatar.jpg', avatar_file, save=True)

        customers = User.objects.filter(role='CUSTOMER')
        for i, cust in enumerate(customers):
            self.stdout.write(f" -> Uploading avatar for Customer ({cust.full_name})...")
            c_colors = [(14, 165, 233), (168, 85, 247), (236, 72, 153)]
            avatar_file = create_user_avatar(cust.first_name, "ลูกค้า (Customer)", c_colors[i % len(c_colors)])
            cust.avatar.save(f'cust_{cust.id}_avatar.jpg', avatar_file, save=True)

        # 2. Worker Profiles, KYC, and Certificates
        workers = WorkerProfile.objects.select_related('user').all()
        themes = [
            ((15, 23, 42), (30, 58, 138)),    # Electrician
            ((12, 74, 110), (14, 116, 144)),  # AC
            ((67, 20, 7), (154, 52, 18)),     # Plumber
            ((24, 24, 27), (82, 82, 91)),     # Construction
            ((66, 32, 6), (146, 64, 14)),     # Wood
            ((76, 29, 149), (124, 58, 237)),  # Roof
        ]

        roles = [
            "ช่างระบบไฟฟ้ามืออาชีพ",
            "ช่างแอร์และระบบความเย็น",
            "ช่างประปาและสุขาภิบาล",
            "ช่างก่อสร้างและต่อเติม",
            "ช่างไม้และเฟอร์นิเจอร์",
            "ช่างซ่อมหลังคาและกันซึม"
        ]

        for i, wp in enumerate(workers):
            theme = themes[i % len(themes)]
            role_desc = roles[i % len(roles)]
            self.stdout.write(f" -> Uploading profile & KYC for Worker #{wp.id} ({wp.user.full_name})...")

            # Profile Image
            prof_file = create_worker_avatar(wp.user.first_name, role_desc, theme, "ผ่านการคัดกรอง")
            wp.profile_image.save(f'worker_{wp.id}_profile.jpg', prof_file, save=False)

            # KYC ID Card
            id_file = create_document_mockup("ID_CARD", f"บัตรประชาชน - {wp.user.full_name}")
            wp.id_card_image.save(f'worker_{wp.id}_idcard.jpg', id_file, save=False)

            # Certificate
            cert_file = create_document_mockup("CERTIFICATE", f"ใบประกอบวิชาชีพช่าง - {role_desc}")
            wp.certificate_image.save(f'worker_{wp.id}_certificate.jpg', cert_file, save=False)

            wp.is_id_verified = True
            wp.save()

        # 3. Service Requests Problem Images
        bookings = ServiceRequest.objects.select_related('category', 'worker__user').all()
        for i, bk in enumerate(bookings):
            self.stdout.write(f" -> Uploading problem image for Booking #{bk.id} ({bk.category.category_name})...")
            prob_file = create_problem_mockup(bk.details[:30], bk.category.category_name, themes[i % len(themes)])
            bk.problem_image.save(f'booking_{bk.id}_problem.jpg', prob_file, save=True)

        self.stdout.write(self.style.SUCCESS("[SUCCESS] All sample images successfully generated and uploaded to Cloudinary!"))
