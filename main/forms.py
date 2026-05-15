
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django import forms
from .models import User, Image

User = get_user_model()

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, validators=[validate_password])
    password2 = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, initial='participant')
    organization_name = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'role', 'organization_name']

    def clean_password2(self) -> str:
        """Проверяет, совпадают ли введённые пароли.
        Returns:str: Второй пароль, если проверка пройдена
        Raises:ValidationError: Если пароли не совпадают"""
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise forms.ValidationError('Пароли не совпадают')
        return password2

    def save(self, commit: bool = True) -> User:
        """Сохраняет пользователя с хешированным паролем.
        Args:commit: Сохранять ли объект в БД (по умолчанию True)
        Returns:User: Сохранённый объект пользователя"""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """Форма для входа пользователя."""
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

from .models import Image

class ImageForm(forms.ModelForm):
    """Форма для загрузки изображений мастер-класса."""
    class Meta:
        model = Image
        fields = ['image', 'is_main']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class UserEditForm(forms.ModelForm):
    """Форма редактирования профиля для участника."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Телефон'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

class OrganizerEditForm(forms.ModelForm):
    """Форма редактирования профиля для организатора (доп. поле "Название студии")."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'organization_name', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Телефон'}),
            'organization_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название студии'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }