from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from workers.models import WorkerProfile

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='อีเมล หรือ ชื่อผู้ใช้ (Email / Username)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'อีเมล หรือ ชื่อผู้ใช้ (เช่น username)', 'autofocus': True})
    )
    password = forms.CharField(
        label='รหัสผ่าน (Password)',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'})
    )


class RegisterForm(forms.ModelForm):
    first_name = forms.CharField(
        label='ชื่อจริง',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อจริง'})
    )
    last_name = forms.CharField(
        label='นามสกุล',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'นามสกุล'})
    )
    email = forms.EmailField(
        label='อีเมล',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'})
    )
    phone_number = forms.CharField(
        label='เบอร์โทรศัพท์',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0812345678'})
    )
    password = forms.CharField(
        label='รหัสผ่าน',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'กำหนดรหัสผ่านอย่างน้อย 6 ตัวอักษร'})
    )
    confirm_password = forms.CharField(
        label='ยืนยันรหัสผ่าน',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'กรอกรหัสผ่านซ้ำอีกครั้ง'})
    )
    role = forms.ChoiceField(
        label='ประเภทผู้ใช้งาน',
        choices=[('CUSTOMER', 'ลูกค้า / ผู้ค้นหาช่าง (Customer)'), ('WORKER', 'ช่างรับจ้าง (Skilled Worker)')],
        widget=forms.RadioSelect(attrs={'class': 'role-radio-select'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'role']

    def clean_email(self):
        email = self.cleaned_data.get('email').strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('อีเมลนี้ถูกใช้งานในระบบแล้ว')
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', 'รหัสผ่านทั้งสองช่องไม่ตรงกัน')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            if user.role == 'WORKER':
                WorkerProfile.objects.get_or_create(user=user, defaults={'status': 'PENDING'})
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

