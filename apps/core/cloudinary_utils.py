import hashlib
import os
import logging
from django.utils.deconstruct import deconstructible
from django.conf import settings

logger = logging.getLogger(__name__)


@deconstructible
class HashedUploadTo:
    """
    สร้างชื่อไฟล์ตาม SHA-256 Hash ของเนื้อหาไฟล์รูปภาพ
    - ป้องกันการสร้างรูปซ้ำ (Deduplication): หากอัปโหลดรูปภาพเดิม จะได้ hash เดิม
    - ป้องกันปัญหาชื่อไฟล์ภาษาไทย หรือชื่อไฟล์ชนกันระหว่างผู้ใช้
    """
    def __init__(self, subfolder):
        self.subfolder = subfolder.strip('/')

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower()
        if not ext or ext not in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg']:
            ext = '.jpg'

        hasher = hashlib.sha256()
        content_hashed = False

        # พยายามอ่านเนื้อหาไฟล์เพื่อคำนวณ Content Hash
        for field in instance._meta.fields:
            if field.get_internal_type() in ('FileField', 'ImageField'):
                file_field = getattr(instance, field.name, None)
                if file_field and hasattr(file_field, 'file') and file_field.file:
                    try:
                        pos = file_field.tell() if hasattr(file_field, 'tell') else 0
                        file_field.seek(0)
                        content = file_field.read()
                        file_field.seek(pos)
                        if content:
                            hasher.update(content)
                            content_hashed = True
                            break
                    except Exception:
                        pass

        if not content_hashed:
            # Fallback หากไม่สามารถอ่าน raw stream ได้
            fallback_seed = f"{instance.__class__.__name__}_{getattr(instance, 'pk', 'new')}_{filename}"
            hasher.update(fallback_seed.encode('utf-8'))

        file_hash = hasher.hexdigest()[:24]
        return f"{self.subfolder}/{file_hash}{ext}"


def hashed_upload_path(subfolder):
    return HashedUploadTo(subfolder)


def delete_cloudinary_asset(file_path_or_field):
    """
    ลบรูปภาพออกจาก Cloudinary โดยอัตโนมัติเมื่อมีการลบข้อมูลหรือเปลี่ยนรูปในระบบ
    """
    if not file_path_or_field:
        return False

    try:
        if hasattr(file_path_or_field, 'name'):
            file_name = file_path_or_field.name
        else:
            file_name = str(file_path_or_field)

        if not file_name:
            return False

        # ตรวจสอบว่ามีการตั้งค่า Cloudinary หรือไม่
        if not getattr(settings, 'CLOUDINARY_STORAGE', {}).get('CLOUD_NAME'):
            return False

        import cloudinary.uploader

        # ถอด path และ extension เพื่อหา public_id
        # Cloudinary public_id คือ path โดยไม่มี file extension
        public_id, _ = os.path.splitext(file_name)

        # ลบ asset ออกจาก Cloudinary
        response = cloudinary.uploader.destroy(public_id, invalidate=True)
        logger.info(f"Cloudinary destroy for '{public_id}': {response}")
        return True
    except Exception as e:
        logger.warning(f"Failed to delete Cloudinary asset for {file_path_or_field}: {e}")
        return False
