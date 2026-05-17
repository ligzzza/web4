from django.contrib import admin
from .models import User, Category, MasterClass, Image, Booking, Review, Favorite, Notification, Session
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['masterclass', 'start_datetime', 'end_datetime', 'max_participants', 'current_participants', 'status', 'meeting_link']
    list_filter = ['status', 'masterclass']
    search_fields = ['masterclass__title']
    fields = ['masterclass', 'start_datetime', 'end_datetime', 'max_participants', 'status', 'meeting_link']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_blocked')
    list_filter = ('role', 'is_active', 'is_blocked')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'email', 'phone', 'avatar')}),
        ('Права доступа', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Для организатора', {'fields': ('organization_name', 'organization_description')}),
        ('Блокировка', {'fields': ('is_blocked',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )

    def save_model(self, request, obj, form, change):
        """Хеширует пароль при сохранении"""
        if 'password' in form.changed_data:
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(MasterClass)
class MasterClassAdmin(admin.ModelAdmin):
    list_display = ['title', 'organizer', 'city', 'format', 'price', 'status', 'created_at']
    list_filter = ['status', 'city', 'format', 'category']
    search_fields = ['title', 'description']

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['masterclass', 'is_main', 'uploaded_at']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['participant', 'masterclass', 'status', 'payment_status', 'total_price']
    list_filter = ['status', 'payment_status']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['author', 'masterclass', 'rating', 'status', 'created_at']
    list_filter = ['rating', 'status']

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'masterclass', 'created_at']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'title', 'is_read', 'created_at']
    list_filter = ['type', 'is_read']