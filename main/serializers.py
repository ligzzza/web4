from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ExampleModel


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователей"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class ExampleModelSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ExampleModel"""
    owner_username = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = ExampleModel
        fields = [
            'id',
            'name',
            'description',
            'is_active',
            'owner',
            'owner_username',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']