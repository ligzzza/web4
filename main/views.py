from rest_framework import viewsets, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from .models import ExampleModel
from .serializers import ExampleModelSerializer, UserSerializer


class ExampleModelViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с ExampleModel (полный CRUD)"""
    queryset = ExampleModel.objects.all()
    serializer_class = ExampleModelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        """При создании автоматически устанавливаем текущего пользователя как владельца"""
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        """Фильтрация queryset по необходимости"""
        queryset = super().get_queryset()
        # Можно добавить фильтрацию по параметрам запроса
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Кастомное действие для переключения статуса is_active"""
        example = self.get_object()
        example.is_active = not example.is_active
        example.save()
        return Response({
            'status': 'success',
            'is_active': example.is_active,
            'message': f'Статус изменен на {"активно" if example.is_active else "неактивно"}'
        })


class UserListView(generics.ListAPIView):
    """Список пользователей"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]