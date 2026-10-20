import logging
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from workers.models import WorkerProfile
from bookings.models import ServiceRequest
from core.cloudinary_utils import delete_cloudinary_asset

logger = logging.getLogger(__name__)
User = get_user_model()


# ==========================================
# 1. AUTO DELETE ON POST_DELETE
# ==========================================

@receiver(post_delete, sender=WorkerProfile)
def delete_worker_profile_images_on_delete(sender, instance, **kwargs):
    """ลบรูปโปรไฟล์, บัตรประชาชน และใบประกอบวิชาชีพจาก Cloudinary เมื่อลบ WorkerProfile"""
    if instance.profile_image:
        delete_cloudinary_asset(instance.profile_image)
    if instance.id_card_image:
        delete_cloudinary_asset(instance.id_card_image)
    if instance.certificate_image:
        delete_cloudinary_asset(instance.certificate_image)


@receiver(post_delete, sender=ServiceRequest)
def delete_service_request_image_on_delete(sender, instance, **kwargs):
    """ลบรูปถ่ายปัญหาหน้างานจาก Cloudinary เมื่อลบคำขอรับบริการ"""
    if instance.problem_image:
        delete_cloudinary_asset(instance.problem_image)


@receiver(post_delete, sender=User)
def delete_user_avatar_on_delete(sender, instance, **kwargs):
    """ลบรูป Avatar ของผู้ใช้เมื่อบัญชีถูกลบ"""
    if hasattr(instance, 'avatar') and instance.avatar:
        delete_cloudinary_asset(instance.avatar)


# ==========================================
# 2. AUTO CLEANUP OLD IMAGE ON UPDATE (PRE_SAVE)
# ==========================================

@receiver(pre_save, sender=WorkerProfile)
def auto_delete_old_worker_images_on_update(sender, instance, **kwargs):
    """ลบรูปเก่าออกจาก Cloudinary เมื่อมีการอัปโหลดรูปใหม่มาแทนที่"""
    if not instance.pk:
        return

    try:
        old_instance = WorkerProfile.objects.filter(pk=instance.pk).first()
        if not old_instance:
            return

        # ตรวจสอบรูปโปรไฟล์
        if old_instance.profile_image and old_instance.profile_image != instance.profile_image:
            delete_cloudinary_asset(old_instance.profile_image)

        # ตรวจสอบรูปบัตรประชาชน
        if old_instance.id_card_image and old_instance.id_card_image != instance.id_card_image:
            delete_cloudinary_asset(old_instance.id_card_image)

        # ตรวจสอบรูปใบประกอบวิชาชีพ
        if old_instance.certificate_image and old_instance.certificate_image != instance.certificate_image:
            delete_cloudinary_asset(old_instance.certificate_image)
    except Exception as e:
        logger.warning(f"Error in pre_save worker image cleanup: {e}")


@receiver(pre_save, sender=ServiceRequest)
def auto_delete_old_booking_image_on_update(sender, instance, **kwargs):
    """ลบรูปปัญหาหน้างานเก่าออกจาก Cloudinary เมื่อมีการเปลี่ยนรูปใหม่"""
    if not instance.pk:
        return

    try:
        old_instance = ServiceRequest.objects.filter(pk=instance.pk).first()
        if not old_instance:
            return

        if old_instance.problem_image and old_instance.problem_image != instance.problem_image:
            delete_cloudinary_asset(old_instance.problem_image)
    except Exception as e:
        logger.warning(f"Error in pre_save booking image cleanup: {e}")


@receiver(pre_save, sender=User)
def auto_delete_old_user_avatar_on_update(sender, instance, **kwargs):
    """ลบ Avatar เก่าออกจาก Cloudinary เมื่อผู้ใช้อัปโหลดรูปใหม่"""
    if not instance.pk:
        return

    try:
        old_instance = User.objects.filter(pk=instance.pk).first()
        if not old_instance:
            return

        if hasattr(old_instance, 'avatar') and hasattr(instance, 'avatar'):
            if old_instance.avatar and old_instance.avatar != instance.avatar:
                delete_cloudinary_asset(old_instance.avatar)
    except Exception as e:
        logger.warning(f"Error in pre_save user avatar cleanup: {e}")
