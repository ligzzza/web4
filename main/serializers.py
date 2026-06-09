from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import MasterClass, Category, Booking, Review, Favorite, Session
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователей"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'role', 'avatar']

class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категорий"""

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image']

class SessionSerializer(serializers.ModelSerializer):
    """Сериализатор для сеансов"""

    class Meta:
        model = Session
        fields = ['id', 'start_datetime', 'end_datetime', 'max_participants', 'current_participants', 'status',
                  'meeting_link']

class MasterClassSerializer(serializers.ModelSerializer):
    """Сериализатор для мастер-классов"""
    organizer_name = serializers.ReadOnlyField(source='organizer.username')
    category_name = serializers.ReadOnlyField(source='category.name')
    is_favorite = serializers.SerializerMethodField()
    sessions = SessionSerializer(many=True, read_only=True)

    class Meta:
        model = MasterClass
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'organizer', 'organizer_name', 'city', 'address', 'format',
            'price', 'status', 'created_at', 'updated_at',
            'is_favorite', 'sessions'
        ]
        read_only_fields = ['organizer', 'created_at', 'updated_at']

    def get_is_favorite(self, obj: MasterClass) -> bool:
        """Проверяет, добавил ли текущий пользователь мастер-класс в избранное.
        Args:obj: Объект мастер-класса
        Returns:bool: True если в избранном, False если нет"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user, masterclass=obj).exists()
        return False

class BookingSerializer(serializers.ModelSerializer):
    """Сериализатор для бронирований"""
    participant_name = serializers.ReadOnlyField(source='participant.username')
    masterclass_title = serializers.ReadOnlyField(source='masterclass.title')
    session_info = SessionSerializer(source='session', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'participant', 'participant_name', 'masterclass', 'masterclass_title',
            'session', 'session_info', 'status', 'payment_status',
            'participants_count', 'total_price', 'created_at'
        ]
        read_only_fields = ['participant', 'total_price', 'created_at']

class ReviewSerializer(serializers.ModelSerializer):
    """Сериализатор для отзывов"""
    author_name = serializers.ReadOnlyField(source='author.username')
    author_full_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'author', 'author_name', 'author_full_name', 'masterclass',
                  'booking', 'rating', 'text', 'status', 'created_at']
        read_only_fields = ['author', 'created_at']

    def get_author_full_name(self, obj: Review) -> str:
        """Возвращает полное имя автора отзыва.
        Args:obj: Объект отзыва
        Returns:str: Полное имя автора"""
        return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.username

class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного"""
    masterclass_info = MasterClassSerializer(source='masterclass', read_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'user', 'masterclass', 'masterclass_info', 'created_at']
        read_only_fields = ['user', 'created_at']

class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 'last_name', 'phone', 'role']

    def validate(self, attrs: dict) -> dict:
        """Проверяет, совпадают ли пароли.
        Args:attrs: Словарь с данными формы
        Returns:dict: Проверенные данные
        Raises:ValidationError: Если пароли не совпадают"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data: dict) -> User:
        """Создаёт нового пользователя.
        Args:validated_data: Проверенные данные пользователя
        Returns:User: Созданный объект пользователя"""
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user