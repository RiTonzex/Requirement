from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.contrib import messages
from .forms import LoginForm, RegisterForm, UserProfileForm
from .utils import check_login_rate_limit, record_failed_login, reset_failed_login
from django.conf import settings

User = get_user_model()


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        username_input = request.POST.get('username', '').strip()

        # Check Rate Limit before processing
        is_locked, remaining_seconds, attempts = check_login_rate_limit(request, username_input)
        if is_locked:
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            time_msg = f"{minutes} นาที {seconds} วินาที" if minutes > 0 else f"{seconds} วินาที"
            messages.error(
                request,
                f"⚠️ ระบบความปลอดภัย: บัญชีหรือ IP ของคุณถูกระงับการเข้าสู่ระบบชั่วคราวเนื่องจากกรอกรหัสผ่านผิดเกิน {settings.LOGIN_RATE_LIMIT_ATTEMPTS} ครั้ง กรุณารออีก {time_msg}"
            )
            form = LoginForm(request)
            return render(request, 'accounts/login.html', {'form': form, 'is_locked': True, 'remaining_seconds': remaining_seconds})

        # หากมีผู้พยายามล็อกอินด้วยบัญชีแอดมินในหน้าปกติ ให้ปฏิเสธและตอบว่าไม่พบบัญชีเสมอ
        admin_match = User.objects.filter(Q(username__iexact=username_input) | Q(email__iexact=username_input), role='ADMIN').exists()

        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()

            # [ADMIN SEPARATION]: ห้ามแอดมินล็อกอินผ่านหน้าผู้ใช้ทั่วไป
            if user.is_admin_user:
                record_failed_login(request, username_input)
                messages.error(request, "ไม่พบบัญชีผู้ใช้งานนี้ในระบบ")
                return render(request, 'accounts/login.html', {'form': form})

            login(request, user)
            reset_failed_login(request, username_input)
            messages.success(request, f"ยินดีต้อนรับคุณ {user.full_name} เข้าสู่ระบบสำเร็จ")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('accounts:dashboard_redirect')
        else:
            if admin_match:
                record_failed_login(request, username_input)
                messages.error(request, "ไม่พบบัญชีผู้ใช้งานนี้ในระบบ")
                return render(request, 'accounts/login.html', {'form': form})

            is_locked_now, remaining_sec, new_attempts = record_failed_login(request, username_input)
            if is_locked_now:
                minutes = remaining_sec // 60
                messages.error(
                    request,
                    f"⚠️ ระบบความปลอดภัย: กรอกรหัสผ่านผิดเกินกำหนด ({settings.LOGIN_RATE_LIMIT_ATTEMPTS} ครั้ง) ระบบทำการระงับการเข้าสู่ระบบชั่วคราวเป็นเวลา {minutes} นาที"
                )
            else:
                remaining_attempts = settings.LOGIN_RATE_LIMIT_ATTEMPTS - new_attempts
                messages.error(
                    request,
                    f"อีเมลหรือรหัสผ่านไม่ถูกต้อง (เหลือโอกาสลองอีก {remaining_attempts} ครั้ง ก่อนระบบระงับชั่วคราว)"
                )
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def admin_login_view(request):
    """
    หน้าเข้าสู่ระบบเฉพาะสำหรับผู้ดูแลระบบ (Admin Portal)
    - อนุญาตเฉพาะบัญชีที่มีสิทธิ์เป็น ADMIN หรือ is_staff / is_superuser เท่านั้น
    - ผู้ใช้ทั่วไปหรือช่างจะไม่สามารถเข้าสู่ระบบผ่านหน้านี้ได้
    """
    if request.user.is_authenticated:
        if request.user.is_admin_user:
            return redirect('dashboard:admin_dashboard')
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        username_input = request.POST.get('username', '').strip()

        # Check Rate Limit before processing
        is_locked, remaining_seconds, attempts = check_login_rate_limit(request, username_input)
        if is_locked:
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            time_msg = f"{minutes} นาที {seconds} วินาที" if minutes > 0 else f"{seconds} วินาที"
            messages.error(
                request,
                f"⚠️ ระบบความปลอดภัย: บัญชีหรือ IP ถูกระงับการเข้าสู่ระบบชั่วคราวเนื่องจากกรอกรหัสผ่านผิดเกิน {settings.LOGIN_RATE_LIMIT_ATTEMPTS} ครั้ง กรุณารออีก {time_msg}"
            )
            form = LoginForm(request)
            return render(request, 'accounts/admin_login.html', {'form': form, 'is_locked': True, 'remaining_seconds': remaining_seconds})

        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_admin_user:
                record_failed_login(request, username_input)
                messages.error(request, "❌ ไม่พบบัญชีผู้ดูแลระบบ (หน้านี้อนุญาตเฉพาะผู้ดูแลระบบที่มีสิทธิ์เท่านั้น)")
                return render(request, 'accounts/admin_login.html', {'form': form})

            login(request, user)
            reset_failed_login(request, username_input)
            messages.success(request, f"ยินดีต้อนรับผู้ดูแลระบบ {user.full_name} เข้าสู่ศูนย์ควบคุมระบบ")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard:admin_dashboard')
        else:
            is_locked_now, remaining_sec, new_attempts = record_failed_login(request, username_input)
            if is_locked_now:
                minutes = remaining_sec // 60
                messages.error(
                    request,
                    f"⚠️ ระบบความปลอดภัย: กรอกรหัสผ่านผิดเกินกำหนด ({settings.LOGIN_RATE_LIMIT_ATTEMPTS} ครั้ง) ระบบทำการระงับชั่วคราวเป็นเวลา {minutes} นาที"
                )
            else:
                remaining_attempts = settings.LOGIN_RATE_LIMIT_ATTEMPTS - new_attempts
                messages.error(
                    request,
                    f"ชื่อผู้ใช้หรือรหัสผ่านผู้ดูแลระบบไม่ถูกต้อง (เหลือโอกาสลองอีก {remaining_attempts} ครั้ง)"
                )
    else:
        form = LoginForm()

    return render(request, 'accounts/admin_login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    role_param = request.GET.get('role', 'CUSTOMER').upper()
    initial_role = 'WORKER' if role_param == 'WORKER' else 'CUSTOMER'

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='accounts.backends.EmailOrUsernameBackend')
            if user.role == 'WORKER':
                messages.success(request, "สมัครสมาชิกช่างรับจ้างสำเร็จ! กรุณากรอกข้อมูลทักษะและพื้นที่บริการเพิ่มเติม")
                return redirect('workers:edit_profile')
            messages.success(request, "สมัครสมาชิกสำเร็จ! ยินดีต้อนรับสู่ระบบค้นหาช่างใกล้บ้าน")
            return redirect('dashboard:customer_dashboard')
        else:
            messages.error(request, "เกิดข้อผิดพลาด กรุณาตรวจสอบข้อมูลที่กรอก")
    else:
        form = RegisterForm(initial={'role': initial_role})

    return render(request, 'accounts/register.html', {'form': form, 'initial_role': initial_role})


def logout_view(request):
    logout(request)
    messages.info(request, "คุณได้ออกจากระบบเรียบร้อยแล้ว")
    return redirect('core:home')


@login_required
def dashboard_redirect(request):
    if request.user.is_admin_user:
        return redirect('dashboard:admin_dashboard')
    elif request.user.is_worker:
        return redirect('dashboard:worker_dashboard')
    else:
        return redirect('dashboard:customer_dashboard')


@login_required
def profile_edit_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "บันทึกข้อมูลส่วนตัวเรียบร้อยแล้ว")
            return redirect('accounts:profile_edit')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'accounts/profile_edit.html', {'form': form})

