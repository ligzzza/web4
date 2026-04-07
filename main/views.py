from rest_framework import permissions, viewsets, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from .models import MasterClass, Category, Booking, Review, Favorite, Notification
from .serializers import (
    MasterClassSerializer, CategorySerializer, BookingSerializer,
    ReviewSerializer, FavoriteSerializer, UserSerializer, RegisterSerializer
)
from .permissions import IsOrganizer, IsAdmin, IsOwnerOrReadOnly, IsParticipant, IsBookingOwner
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm

User = get_user_model()


# ============================================================
# VIEWSETS ДЛЯ МАСТЕР-КЛАССОВ
# ============================================================

class MasterClassViewSet(viewsets.ModelViewSet):
    queryset = MasterClass.objects.all()
    serializer_class = MasterClassSerializer

    def get_permissions(self):
        """Назначаем разные права для разных действий"""
        if self.action == 'create':
            # Создавать могут только организаторы
            permission_classes = [IsOrganizer]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Редактировать и удалять может владелец или админ
            permission_classes = [IsOwnerOrReadOnly | IsAdmin]
        else:
            # Читать могут все (авторизованные или нет)
            permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = super().get_queryset()
        city = self.request.query_params.get('city', None)
        if city:
            queryset = queryset.filter(city__icontains=city)
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__slug=category)
        if not self.request.user.is_admin and not self.request.user.is_organizer:
            queryset = queryset.filter(status='approved')
        return queryset

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)


# ============================================================
# VIEWSETS ДЛЯ КАТЕГОРИЙ
# ============================================================

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Изменять категории может только администратор
            permission_classes = [IsAdmin]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]

# ============================================================
# VIEWSETS ДЛЯ БРОНИРОВАНИЙ
# ============================================================

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def get_permissions(self):
        if self.action == 'create':
            # Создавать бронирование могут только участники
            permission_classes = [IsParticipant]
        else:
            # Просматривать может владелец или админ
            permission_classes = [IsBookingOwner]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Booking.objects.all()
        return Booking.objects.filter(participant=user)

    def perform_create(self, serializer):
        masterclass = serializer.validated_data['masterclass']
        # Проверка свободных мест
        if masterclass.current_participants >= masterclass.max_participants:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": "Свободные места закончились"})
        serializer.save(participant=self.request.user, total_price=masterclass.price)
        # Обновляем количество участников
        masterclass.current_participants += 1
        masterclass.save()


# ============================================================
# VIEWSETS ДЛЯ ОТЗЫВОВ
# ============================================================

class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с отзывами"""
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Только одобренные отзывы для всех, все отзывы для админа"""
        if self.request.user.is_admin:
            return Review.objects.all()
        return Review.objects.filter(status='approved')


# ============================================================
# VIEWSETS ДЛЯ ИЗБРАННОГО
# ============================================================

class FavoriteViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с избранным"""
    queryset = Favorite.objects.all()
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Пользователь видит только своё избранное"""
        return Favorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """При создании устанавливаем текущего пользователя"""
        serializer.save(user=self.request.user)


# ============================================================
# ПРОСТЫЕ GENERIC VIEWS
# ============================================================

class UserListView(generics.ListAPIView):
    """Список пользователей (только для админа)"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class RegisterView(generics.CreateAPIView):
    """Регистрация нового пользователя"""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserSerializer(user).data,
            "message": "Регистрация успешна"
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Авторизация пользователя"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return Response({
                "user": UserSerializer(user).data,
                "message": "Вход выполнен успешно"
            })
        else:
            return Response({
                "error": "Неверное имя пользователя или пароль"
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """Выход из системы"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"message": "Выход выполнен успешно"})


def register_view(request):
    #if request.user.is_authenticated:
    #   return redirect('/')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Перенаправление в зависимости от роли
            if user.role == 'organizer':
                return redirect('/organizer/dashboard/')
            else:
                return redirect('/participant/dashboard/')
    else:
        form = RegisterForm()

    return render(request, 'main/register.html', {'form': form})


def login_view(request):
    #if request.user.is_authenticated:
    #    return redirect('/')

    error = None
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                # Перенаправление в зависимости от роли
                if user.role == 'organizer':
                    return redirect('/organizer/dashboard/')
                else:
                    return redirect('/participant/dashboard/')
            else:
                error = 'Неверное имя пользователя или пароль'
    else:
        form = LoginForm()

    return render(request, 'main/login.html', {'form': form, 'error': error})


def logout_view(request):
    logout(request)
    return redirect('/login/')


@login_required
def participant_dashboard(request):
    """Страница для участника"""
    return render(request, 'main/participant_dashboard.html', {'user': request.user})


@login_required
def organizer_dashboard(request):
    """Страница для организатора"""
    return render(request, 'main/organizer_dashboard.html', {'user': request.user})