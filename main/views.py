from rest_framework import permissions, viewsets, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .models import MasterClass, Category, Booking, Review, Favorite, Notification, Image, Session
from .serializers import (
    MasterClassSerializer, CategorySerializer, BookingSerializer,
    ReviewSerializer, FavoriteSerializer, UserSerializer, RegisterSerializer
)
from .permissions import IsOrganizer, IsAdmin, IsOwnerOrReadOnly, IsParticipant, IsBookingOwner
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import RegisterForm, LoginForm
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator


from django.http import HttpRequest, HttpResponse, JsonResponse

from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from .models import MasterClass, Category, User, Booking
from .filters import MasterClassFilter

User = get_user_model()


# ============================================================
# ПАНЕЛЬ АДМИНИСТРАТОРА
# ============================================================

def is_admin(user: User) -> bool:
    """Проверяет, является ли пользователь администратором."""
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)


@login_required
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    """Главная панель администратора."""
    if not is_admin(request.user):
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')

    context = {
        'pending_masterclasses': MasterClass.objects.filter(status='pending').count(),
        'pending_reviews': Review.objects.filter(status='pending').count(),
        'total_users': User.objects.count(),
        'total_categories': Category.objects.count(),
    }
    return render(request, 'main/admin_dashboard.html', context)


@login_required
def admin_masterclasses(request: HttpRequest) -> HttpResponse:
    """Список мастер-классов для модерации."""
    if not is_admin(request.user):
        return redirect('home')

    status_filter = request.GET.get('status', 'all')

    if status_filter == 'all':
        masterclasses = MasterClass.objects.all().order_by('-created_at')
    else:
        masterclasses = MasterClass.objects.filter(status=status_filter).order_by('-created_at')

    # Пагинация
    paginator = Paginator(masterclasses, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'main/admin_masterclasses.html', {
        'masterclasses': masterclasses,
        'page_obj': page_obj,
        'current_status': status_filter,
    })


@login_required
def admin_approve_masterclass(request: HttpRequest, masterclass_id: int) -> HttpResponse:
    """Одобрение мастер-класса."""
    if not is_admin(request.user):
        return redirect('home')

    masterclass = get_object_or_404(MasterClass, id=masterclass_id)
    masterclass.status = 'approved'
    masterclass.save()

    messages.success(request, f'Мастер-класс "{masterclass.title}" одобрен')
    return redirect('admin_masterclasses')


@login_required
def admin_reject_masterclass(request: HttpRequest, masterclass_id: int) -> HttpResponse:
    """Отклонение мастер-класса."""
    if not is_admin(request.user):
        return redirect('home')

    masterclass = get_object_or_404(MasterClass, id=masterclass_id)
    masterclass.status = 'rejected'
    masterclass.save()

    messages.success(request, f'Мастер-класс "{masterclass.title}" отклонён')
    return redirect('admin_masterclasses')


@login_required
def admin_reviews(request: HttpRequest) -> HttpResponse:
    """Список отзывов для модерации."""
    if not is_admin(request.user):
        return redirect('home')

    status_filter = request.GET.get('status', 'all')

    if status_filter == 'all':
        reviews = Review.objects.all().order_by('-created_at')
    else:
        reviews = Review.objects.filter(status=status_filter).order_by('-created_at')

    # Пагинация
    paginator = Paginator(reviews, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'main/admin_reviews.html', {
        'reviews': reviews,
        'page_obj': page_obj,
        'current_status': status_filter,
    })


@login_required
def admin_approve_review(request: HttpRequest, review_id: int) -> HttpResponse:
    """Одобрение отзыва."""
    if not is_admin(request.user):
        return redirect('home')

    review = get_object_or_404(Review, id=review_id)
    review.status = 'approved'
    review.save()

    messages.success(request, 'Отзыв одобрен')
    return redirect('admin_reviews')


@login_required
def admin_delete_review(request: HttpRequest, review_id: int) -> HttpResponse:
    """Удаление отзыва (для администратора)."""
    if not is_admin(request.user):
        return redirect('home')

    review = get_object_or_404(Review, id=review_id)
    review.delete()

    messages.success(request, 'Отзыв удалён')
    return redirect('admin_reviews')


@login_required
def admin_users(request: HttpRequest) -> HttpResponse:
    """Список пользователей для управления с поиском и фильтрацией."""
    if not is_admin(request.user):
        return redirect('home')

    users = User.objects.all().order_by('-date_joined')

    # Поиск по имени, фамилии, email
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query)
        )

    # Фильтр по роли
    role_filter = request.GET.get('role', 'all')
    if role_filter != 'all':
        users = users.filter(role=role_filter)

    # Пагинация
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'main/admin_users.html', {
        'users': users,
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
    })


@login_required
def admin_block_user(request: HttpRequest, user_id: int) -> HttpResponse:
    """Блокировка пользователя."""
    if not is_admin(request.user):
        return redirect('home')

    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.error(request, 'Вы не можете заблокировать самого себя')
        return redirect('admin_users')

    user.is_blocked = True
    user.is_active = False
    user.save()

    messages.success(request, f'Пользователь {user.username} заблокирован')
    return redirect('admin_users')


@login_required
def admin_unblock_user(request: HttpRequest, user_id: int) -> HttpResponse:
    """Разблокировка пользователя."""
    if not is_admin(request.user):
        return redirect('home')

    user = get_object_or_404(User, id=user_id)
    user.is_blocked = False
    user.is_active = True
    user.save()

    messages.success(request, f'Пользователь {user.username} разблокирован')
    return redirect('admin_users')


@login_required
def admin_make_organizer(request: HttpRequest, user_id: int) -> HttpResponse:
    """Назначение пользователя организатором."""
    if not is_admin(request.user):
        return redirect('home')

    user = get_object_or_404(User, id=user_id)
    user.role = 'organizer'
    user.save()

    messages.success(request, f'Пользователь {user.username} теперь организатор')
    return redirect('admin_users')


@login_required
def admin_categories(request: HttpRequest) -> HttpResponse:
    """Управление категориями."""
    if not is_admin(request.user):
        return redirect('home')

    if request.method == 'POST':
        name = request.POST.get('name')
        slug = request.POST.get('slug')
        if name and slug:
            Category.objects.create(name=name, slug=slug)
            messages.success(request, f'Категория "{name}" создана')
        return redirect('admin_categories')

    categories = Category.objects.all().order_by('name')
    return render(request, 'main/admin_categories.html', {'categories': categories})


@login_required
def admin_edit_category(request: HttpRequest, category_id: int) -> HttpResponse:
    """Редактирование категории."""
    if not is_admin(request.user):
        return redirect('home')

    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.slug = request.POST.get('slug')
        category.save()
        messages.success(request, 'Категория обновлена')
        return redirect('admin_categories')

    return render(request, 'main/admin_edit_category.html', {'category': category})


@login_required
def admin_delete_category(request: HttpRequest, category_id: int) -> HttpResponse:
    """Удаление категории."""
    if not is_admin(request.user):
        return redirect('home')

    category = get_object_or_404(Category, id=category_id)
    category.delete()
    messages.success(request, 'Категория удалена')
    return redirect('admin_categories')


@login_required
def admin_profile_view(request: HttpRequest) -> HttpResponse:
    """Профиль администратора."""
    if not is_admin(request.user):
        return redirect('home')

    return render(request, 'main/admin_profile.html', {'user': request.user})


@login_required
def admin_bookings_history(request: HttpRequest) -> HttpResponse:
    """Отображает историю всех бронирований для администратора.
    Args:
        request: HTTP-запрос от администратора
    Returns:
        HttpResponse: Страница со списком всех бронирований и статистикой"""
    # Проверка прав доступа
    if not is_admin(request.user):
        return redirect('home')

    # Получаем все бронирования с оптимизацией запросов
    bookings = Booking.objects.all().select_related(
        'participant',
        'masterclass',
        'session'
    ).order_by('-created_at')

    # Пагинация
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Выручка (без пагинации)
    total_revenue = sum(b.total_price for b in bookings if b.payment_status == 'paid')

    context: dict = {
        'bookings': bookings,
        'page_obj': page_obj,
        'total_bookings': bookings.count(),
        'total_revenue': total_revenue,
    }

    return render(request, 'main/admin_bookings_history.html', context)
# ============================================================
# VIEWSETS ДЛЯ МАСТЕР-КЛАССОВ
# ============================================================

class MasterClassViewSet(viewsets.ModelViewSet):
    queryset = MasterClass.objects.all()
    serializer_class = MasterClassSerializer
    filterset_class = MasterClassFilter

    def get_permissions(self) -> list:
        """Назначает права доступа в зависимости от действия."""
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

    def get_serializer_context(self) -> dict:
        """Передаёт request в сериализатор для поля is_favorite."""
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context

    def get_queryset(self):
        """Фильтрует queryset по параметрам запроса и роли пользователя."""
        queryset = super().get_queryset()
        city = self.request.query_params.get('city', None)
        if city:
            queryset = queryset.filter(city__icontains=city)
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__slug=category)
        if self.request.user.is_authenticated:
            if not self.request.user.is_admin and not self.request.user.is_organizer:
                queryset = queryset.filter(status='approved')
        else:
            queryset = queryset.filter(status='approved')
        return queryset

    def perform_create(self, serializer) -> None:
        """При создании устанавливает организатора как текущего пользователя."""
        serializer.save(organizer=self.request.user)


# ============================================================
# VIEWSETS ДЛЯ КАТЕГОРИЙ
# ============================================================

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self) -> list:
        """Администратор может изменять категории, остальные только читать."""
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

    def get_permissions(self) -> list:
        """Участник создаёт бронирования, владелец или админ просматривает."""
        if self.action == 'create':
            # Создавать бронирование могут только участники
            permission_classes = [IsParticipant]
        else:
            # Просматривать может владелец или админ
            permission_classes = [IsBookingOwner]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Админ видит все бронирования, участник только свои."""
        user = self.request.user
        if user.is_admin:
            return Booking.objects.all()
        return Booking.objects.filter(participant=user)

    def perform_create(self, serializer) -> None:
        """Создаёт бронирование и обновляет количество участников."""
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
        """Админ видит все отзывы, остальные только одобренные."""
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
        """Возвращает только избранное текущего пользователя."""
        return Favorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer) -> None:
        """При создании устанавливает пользователя как текущего."""
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
        """Обрабатывает POST-запрос на регистрацию."""
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
        """Обрабатывает POST-запрос на вход."""
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
        """Обрабатывает POST-запрос на выход."""
        logout(request)
        return Response({"message": "Выход выполнен успешно"})


def register_view(request: HttpRequest) -> HttpResponse:
    """Отображает и обрабатывает форму регистрации пользователя.
    Args:request: HTTP-запрос
    Returns:HttpResponse: Страница регистрации или перенаправление"""
    if request.user.is_authenticated:
        if request.user.role == 'organizer':
            return redirect('organizer_dashboard')
        else:
            return redirect('participant_dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if user.role == 'organizer':
                return redirect('organizer_dashboard')
            else:
                return redirect('participant_dashboard')
    else:
        form = RegisterForm()

    return render(request, 'main/register.html', {'form': form})


def login_view(request: HttpRequest) -> HttpResponse:
    """Отображает и обрабатывает форму входа пользователя.
    Args:request: HTTP-запрос
    Returns:HttpResponse: Страница входа или перенаправление"""
    if request.user.is_authenticated:
        # Если уже залогинен, перенаправляем по роли
        if request.user.role == 'organizer':
            return redirect('organizer_dashboard')
        elif request.user.role == 'admin' or request.user.is_superuser:
            return redirect('admin_profile')
        else:
            return redirect('participant_dashboard')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            # Перенаправление по роли
            if user.role == 'organizer':
                return redirect('organizer_dashboard')
            elif user.role == 'admin' or user.is_superuser:
                return redirect('admin_profile')
            else:
                return redirect('participant_dashboard')
        else:
            error = 'Неверное имя пользователя или пароль'

    return render(request, 'main/login.html', {'error': error})


def logout_view(request: HttpRequest) -> HttpResponse:
    """Выполняет выход пользователя и перенаправляет на страницу входа."""
    logout(request)
    return redirect('/login/')


@login_required
def participant_dashboard(request: HttpRequest) -> HttpResponse:
    """Страница участника с его активными бронированиями."""

    # Показываем только активные бронирования (не отменённые)
    bookings = Booking.objects.filter(
        participant=request.user
    ).exclude(
        status='cancelled'
    ).order_by('-created_at')

    print(f"=== УЧАСТНИК: {request.user.username} ===")
    print(f"Всего активных бронирований: {bookings.count()}")

    context = {
        'user': request.user,
        'bookings': bookings,
    }
    return render(request, 'main/participant_dashboard.html', context)


@login_required
def session_participants_view(request: HttpRequest, session_id: int) -> HttpResponse:
    """Страница организатора со списком участников сеанса."""
    session = get_object_or_404(Session, id=session_id)
    masterclass = session.masterclass

    # Проверка прав
    if request.user != masterclass.organizer and not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')

    # Получаем все бронирования на этот сеанс
    bookings = Booking.objects.filter(session=session, status='confirmed')

    context = {
        'session': session,
        'masterclass': masterclass,
        'bookings': bookings,
        'participants_count': bookings.count(),
    }
    return render(request, 'main/session_participants.html', context)

@login_required
def organizer_dashboard(request: HttpRequest) -> HttpResponse:
    """Страница организатора с его мастер-классами."""
    my_masterclasses = MasterClass.objects.filter(
        organizer=request.user
    ).select_related('category').prefetch_related('sessions').order_by('-created_at')

    # Для каждого мастер-класса добавляем первый сеанс
    for mc in my_masterclasses:
        mc.first_session = mc.sessions.filter(status='active').order_by('start_datetime').first()

    context = {
        'user': request.user,
        'my_masterclasses': my_masterclasses,
    }
    return render(request, 'main/organizer_dashboard.html', context)

# ============================================================
# НОВЫЕ VIEW-ФУНКЦИИ ДЛЯ НОВОГО ДИЗАЙНА (ДОБАВИТЬ СЮДА)
# ============================================================


def home_view(request: HttpRequest) -> HttpResponse:
    """Главная страница с лучшими и популярными мастер-классами."""

    # Лучшие по отзывам
    top_masterclasses = MasterClass.objects.filter(
        status='approved'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    ).filter(
        reviews_count__gt=0
    ).order_by('-avg_rating')[:2]

    # Популярные по количеству участников (через сеансы)
    popular_masterclasses = MasterClass.objects.filter(
        status='approved'
    ).annotate(
        total_participants=Sum('sessions__current_participants')
    ).order_by('-total_participants')[:3]

    # Статистика
    total_masterclasses = MasterClass.objects.filter(status='approved').count()
    total_participants = Booking.objects.filter(status='confirmed').count()
    total_organizers = User.objects.filter(role='organizer').count()
    total_cities = MasterClass.objects.filter(status='approved').values('city').distinct().count()

    categories = Category.objects.all()

    context = {
        'top_masterclasses': top_masterclasses,
        'popular_masterclasses': popular_masterclasses,
        'categories': categories,
        'total_masterclasses': total_masterclasses,
        'total_participants': total_participants,
        'total_organizers': total_organizers,
        'total_cities': total_cities,
    }
    return render(request, 'main/home.html', context)

from django.db.models import Avg, Count, Sum, Min, Q, F

def catalog_view(request: HttpRequest) -> HttpResponse:
    """Каталог мастер-классов с фильтрацией, поиском и пагинацией."""
    # Базовый запрос — только одобренные мастер-классы
    masterclasses = MasterClass.objects.filter(
        status='approved'
    ).select_related('category', 'organizer').prefetch_related(
        'sessions', 'images'
    )

    # 1. ПОИСК по названию и описанию
    search_query = request.GET.get('search', '').strip()
    if search_query:
        masterclasses = masterclasses.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # 2. ФИЛЬТР по городу
    city_filter = request.GET.get('city', '')
    if city_filter:
        masterclasses = masterclasses.filter(city__icontains=city_filter)

    # 3. ФИЛЬТР по формату
    format_filter = request.GET.get('format', '')
    if format_filter:
        masterclasses = masterclasses.filter(format=format_filter)

    # 4. ФИЛЬТР по категории
    category_filter = request.GET.get('category', '')
    if category_filter and category_filter.isdigit():
        masterclasses = masterclasses.filter(category_id=int(category_filter))

    # Аннотируем только минимальную дату для сортировки
    masterclasses = masterclasses.annotate(
        nearest_start=Min('sessions__start_datetime')
    )

    # СОРТИРОВКА
    sort_by = request.GET.get('sort', 'date')
    if sort_by == 'price_asc':
        masterclasses = masterclasses.order_by('price')
    elif sort_by == 'price_desc':
        masterclasses = masterclasses.order_by('-price')
    elif sort_by == 'date_desc':
        masterclasses = masterclasses.order_by('-nearest_start')
    else:
        masterclasses = masterclasses.order_by('nearest_start')

    # ПАГИНАЦИЯ
    paginator = Paginator(masterclasses, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Для каждого мастер-класса на странице получаем ближайший сеанс
    for mc in page_obj:
        mc.nearest_session = mc.sessions.filter(
            status='active',
            start_datetime__gt=timezone.now()
        ).order_by('start_datetime').first()

    # Данные для фильтров
    cities = MasterClass.objects.filter(status='approved').values_list('city', flat=True).distinct().order_by('city')
    categories = Category.objects.all()

    # Сохраняем текущие параметры фильтрации для пагинации
    current_params = request.GET.copy()
    if 'page' in current_params:
        current_params.pop('page')

    context = {
        'page_obj': page_obj,
        'cities': cities,
        'categories': categories,
        'search_query': search_query,
        'city_filter': city_filter,
        'format_filter': format_filter,
        'category_filter': category_filter,
        'sort_by': sort_by,
        'current_params': current_params.urlencode(),
    }

    return render(request, 'main/catalog.html', context)


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    """Профиль пользователя (универсальный)."""
    return render(request, 'main/profile.html', {'user': request.user})

@login_required
def favorites_list_view(request: HttpRequest) -> HttpResponse:
    """Страница избранного текущего пользователя."""
    favorites = Favorite.objects.filter(user=request.user)
    return render(request, 'main/favorites.html', {'favorites': favorites})


from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .models import MasterClass, Booking, Favorite, Category

@login_required
def create_masterclass_view(request: HttpRequest) -> HttpResponse:
    """Создание мастер-класса с сеансами (только организатор и админ)."""
    if request.user.role != 'organizer' and not request.user.is_admin:
        return redirect('home')

    categories = Category.objects.all()

    if request.method == 'POST':
        # Получаем данные из формы
        title = request.POST.get('title')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        city = request.POST.get('city')
        address = request.POST.get('address')
        format_type = request.POST.get('format')
        price = request.POST.get('price')

        # Создаём мастер-класс (без дат, они теперь в сеансах)
        masterclass = MasterClass.objects.create(
            title=title,
            description=description,
            category_id=category_id,
            organizer=request.user,
            city=city,
            address=address,
            format=format_type,
            price=price,
            status='pending'
        )

        # Создаём сеансы из динамических полей
        start_datetimes = request.POST.getlist('start_datetime')
        end_datetimes = request.POST.getlist('end_datetime')
        max_participants_list = request.POST.getlist('max_participants')
        new_meeting_links = request.POST.getlist('new_meeting_link')

        for i in range(len(start_datetimes)):
            if start_datetimes[i] and end_datetimes[i]:
                Session.objects.create(
                    masterclass=masterclass,
                    start_datetime=datetime.strptime(start_datetimes[i], '%Y-%m-%dT%H:%M'),
                    end_datetime=datetime.strptime(end_datetimes[i], '%Y-%m-%dT%H:%M'),
                    max_participants=int(max_participants_list[i]),
                    meeting_link = new_meeting_links[i] if i < len(new_meeting_links) else ''
                )

        # Обработка загруженных изображений
        images = request.FILES.getlist('images')
        for i, img in enumerate(images):
            Image.objects.create(
                masterclass=masterclass,
                image=img,
                is_main=(i == 0)
            )

        messages.success(request, 'Мастер-класс успешно создан!')
        return redirect('masterclass_detail', masterclass_id=masterclass.id)

    return render(request, 'main/create_masterclass.html', {'categories': categories})

def masterclass_detail_view(request: HttpRequest, masterclass_id: int) -> HttpResponse:
    """Детальная страница мастер-класса с отзывами и сеансами."""
    masterclass = get_object_or_404(
        MasterClass.objects.select_related('category', 'organizer').prefetch_related(
            'sessions', 'images', 'reviews__author'
        ),
        id=masterclass_id
    )
    sessions = masterclass.sessions.filter(
        status='active',
        start_datetime__gt=timezone.now()
    ).order_by('start_datetime')

    # Переменные по умолчанию для неавторизованных пользователей
    is_favorite = False
    can_edit = False
    can_review = False
    participants_list = []
    reviews_count = 0
    avg_rating = None

    # Если пользователь авторизован
    if request.user.is_authenticated:
        # Проверка в избранном
        is_favorite = Favorite.objects.filter(user=request.user, masterclass=masterclass).exists()

        # Проверка прав на редактирование/удаление
        can_edit = (request.user == masterclass.organizer) or request.user.is_admin

        # Список участников (для организатора)
        if can_edit:
            bookings = Booking.objects.filter(masterclass=masterclass, status='confirmed')
            participants_list = [booking.participant for booking in bookings]

        # Можно ли оставить отзыв
        user_booking = Booking.objects.filter(
            participant=request.user,
            masterclass=masterclass,
            status='completed'
        ).first()
        can_review = user_booking and not Review.objects.filter(author=request.user, masterclass=masterclass).exists()

    # Отзывы на этот мастер-класс (только одобренные)
    reviews = Review.objects.filter(masterclass=masterclass, status='approved')
    reviews_count = reviews.count()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    if avg_rating:
        avg_rating = round(avg_rating, 1)

    context = {
        'masterclass': masterclass,
        'is_favorite': is_favorite,
        'reviews': reviews,
        'reviews_count': reviews_count,
        'avg_rating': avg_rating,
        'can_edit': can_edit,
        'participants_list': participants_list,
        'can_review': can_review,
        'sessions': sessions,  # Сеансы
    }

    return render(request, 'main/masterclass_detail.html', context)


@login_required
def edit_masterclass_view(request: HttpRequest, masterclass_id: int) -> HttpResponse:
    """Редактирование мастер-класса и его сеансов."""
    masterclass = get_object_or_404(MasterClass, id=masterclass_id)

    if request.user != masterclass.organizer and not request.user.is_admin:
        return redirect('masterclass_detail', masterclass_id=masterclass.id)

    categories = Category.objects.all()
    sessions = masterclass.sessions.filter(status='active').order_by('start_datetime')

    if request.method == 'POST':
        # Обновляем основную информацию
        masterclass.title = request.POST.get('title')
        masterclass.description = request.POST.get('description')
        masterclass.category_id = request.POST.get('category')
        masterclass.city = request.POST.get('city')
        masterclass.address = request.POST.get('address')
        masterclass.format = request.POST.get('format')
        masterclass.price = request.POST.get('price')
        masterclass.save()

        # Обновляем существующие сеансы
        session_ids = request.POST.getlist('session_id')
        start_datetimes = request.POST.getlist('start_datetime')
        end_datetimes = request.POST.getlist('end_datetime')
        max_participants_list = request.POST.getlist('max_participants')

        for i in range(len(session_ids)):
            if session_ids[i] and start_datetimes[i] and end_datetimes[i]:
                session = Session.objects.get(id=session_ids[i], masterclass=masterclass)
                session.start_datetime = datetime.strptime(start_datetimes[i], '%Y-%m-%dT%H:%M')
                session.end_datetime = datetime.strptime(end_datetimes[i], '%Y-%m-%dT%H:%M')
                session.max_participants = int(max_participants_list[i])
                session.meeting_link = request.POST.getlist('meeting_link')[i] if request.POST.getlist(
                    'meeting_link') else ''
                session.save()

        # Добавляем новые сеансы
        new_start_datetimes = request.POST.getlist('new_start_datetime')
        new_end_datetimes = request.POST.getlist('new_end_datetime')
        new_max_participants_list = request.POST.getlist('new_max_participants')

        for i in range(len(new_start_datetimes)):
            if new_start_datetimes[i] and new_end_datetimes[i]:
                Session.objects.create(
                    masterclass=masterclass,
                    start_datetime=datetime.strptime(new_start_datetimes[i], '%Y-%m-%dT%H:%M'),
                    end_datetime=datetime.strptime(new_end_datetimes[i], '%Y-%m-%dT%H:%M'),
                    max_participants=int(new_max_participants_list[i])
                )

        messages.success(request, 'Мастер-класс обновлён!')
        return redirect('masterclass_detail', masterclass_id=masterclass.id)

    context = {
        'masterclass': masterclass,
        'categories': categories,
        'sessions': sessions,
    }
    return render(request, 'main/edit_masterclass.html', context)



@login_required
def add_favorite_view(request: HttpRequest, masterclass_id: int) -> JsonResponse:
    """Добавление мастер-класса в избранное (асинхронно)."""
    if request.method == 'POST':
        masterclass = get_object_or_404(MasterClass, id=masterclass_id)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            masterclass=masterclass
        )
        return JsonResponse({'status': 'added', 'favorite': created})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def remove_favorite_view(request: HttpRequest, masterclass_id: int) -> JsonResponse:
    """Удаление мастер-класса из избранного."""
    if request.method == 'POST':
        Favorite.objects.filter(
            user=request.user,
            masterclass_id=masterclass_id
        ).delete()
        return redirect('favorites_list')
    return redirect('favorites_list')


@login_required
def add_booking_view(request: HttpRequest, masterclass_id: int) -> HttpResponse:
    """Бронирование мастер-класса."""
    masterclass = get_object_or_404(MasterClass, id=masterclass_id)

    # Проверка: есть ли свободные места
    if masterclass.current_participants >= masterclass.max_participants:
        messages.error(request, 'Свободные места закончились')
        return redirect('masterclass_detail', masterclass_id=masterclass.id)

    # Проверка: есть ли АКТИВНОЕ бронирование (не отменённое)
    existing_booking = Booking.objects.filter(
        participant=request.user,
        masterclass=masterclass,
        status__in=['pending', 'confirmed']  # Только активные
    ).exists()

    if existing_booking:
        messages.error(request, 'Вы уже записаны на этот мастер-класс')
        return redirect('masterclass_detail', masterclass_id=masterclass.id)

    # Создаём бронирование
    booking = Booking.objects.create(
        participant=request.user,
        masterclass=masterclass,
        status='confirmed',
        payment_status='paid',
        participants_count=1,
        total_price=masterclass.price
    )

    # Увеличиваем количество участников
    masterclass.current_participants += 1
    masterclass.save()

    messages.success(request, f'Вы успешно записались на мастер-класс "{masterclass.title}"!')
    return redirect('masterclass_detail', masterclass_id=masterclass.id)


@login_required
def booking_session_view(request: HttpRequest, session_id: int) -> HttpResponse:
    """Страница бронирования конкретного сеанса."""
    session = get_object_or_404(
        Session,
        id=session_id,
        status='active',
        start_datetime__gt=timezone.now()
    )
    masterclass = session.masterclass

    if request.user == masterclass.organizer:
        messages.error(request, 'Вы не можете записаться на свой мастер-класс')
        return redirect('masterclass_detail', masterclass_id=masterclass.id)

    if request.method == 'POST':
        participants_count = int(request.POST.get('participants_count', 1))

        if participants_count > session.free_places:
            messages.error(request, 'Выбрано больше мест, чем доступно')
            return redirect('booking_session', session_id=session.id)

        # Сохраняем данные в сессию для страницы оплаты
        request.session['booking_data'] = {
            'session_id': session.id,
            'participants_count': participants_count,
            'participant_name': request.POST.get('participant_name', ''),
            'participant_email': request.POST.get('participant_email', ''),
            'participant_phone': request.POST.get('participant_phone', ''),
            'comment': request.POST.get('comment', ''),
        }
        return redirect('payment_page', masterclass_id=masterclass.id)

    return render(request, 'main/booking_session.html', {
        'session': session,
        'masterclass': masterclass,
        'max_participants': session.free_places
    })


@login_required
def booking_detail_view(request: HttpRequest, booking_id: int) -> HttpResponse:
    """Детальная страница бронирования."""
    booking = get_object_or_404(Booking, id=booking_id, participant=request.user)
    session = booking.session
    masterclass = booking.masterclass

    context = {
        'booking': booking,
        'session': session,
        'masterclass': masterclass,
    }
    return render(request, 'main/booking_detail.html', context)

def custom_logout_view(request: HttpRequest) -> HttpResponse:
    """Выход из системы с перенаправлением на главную."""
    logout(request)
    return redirect('home')



def delete_masterclass_view(request: HttpRequest, masterclass_id: int) -> HttpResponse:
    """Удаление мастер-класса (только владелец или администратор)."""
    masterclass = get_object_or_404(MasterClass, id=masterclass_id)

    # Проверка прав
    if request.user != masterclass.organizer and not request.user.is_admin:
        return redirect('masterclass_detail', masterclass_id=masterclass.id)

    if request.method == 'POST':
        masterclass.delete()
        messages.success(request, 'Мастер-класс успешно удалён!')
        return redirect('catalog')

    return render(request, 'main/confirm_delete.html', {'masterclass': masterclass})


@login_required
def add_review_view(request: HttpRequest, masterclass_id: int) -> HttpResponse:
    """Добавление отзыва на мастер-класс (обработка POST)."""
    masterclass = get_object_or_404(MasterClass, id=masterclass_id)

    if request.method == 'POST':
        rating = int(request.POST.get('rating', 5))
        text = request.POST.get('text', '')

        user_booking = Booking.objects.filter(
            participant=request.user,
            masterclass=masterclass,
            status='pending'
        ).first()

        if user_booking and not Review.objects.filter(author=request.user, masterclass=masterclass).exists():
            Review.objects.create(
                author=request.user,
                masterclass=masterclass,
                booking=user_booking,
                rating=rating,
                text=text,
                status='approved'
            )

    return redirect('masterclass_detail', masterclass_id=masterclass.id)



def profile_simple_view(request: HttpRequest) -> HttpResponse:
    """Тестовая страница профиля (упрощённая версия)."""
    return render(request, 'main/profile_simple.html', {'user': request.user})


from .forms import UserEditForm, OrganizerEditForm
from django.contrib import messages


from django.http import JsonResponse
from .forms import UserEditForm


@login_required
def edit_profile_ajax(request: HttpRequest) -> JsonResponse:
    """AJAX-обработчик редактирования профиля пользователя.
    Args:request: HTTP-запрос с данными формы
    Returns:JsonResponse: Результат операции (успех/ошибка и обновлённые данные)"""
    if request.method == 'POST':
        if request.user.role == 'organizer':
            form = OrganizerEditForm(request.POST, request.FILES, instance=request.user)
        else:
            form = UserEditForm(request.POST, request.FILES, instance=request.user)

        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
                'phone': request.user.phone,
                'organization_name': request.user.organization_name if request.user.role == 'organizer' else None,
                'avatar_url': request.user.avatar.url if request.user.avatar else None,
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Пожалуйста, проверьте введённые данные'
            })
    return JsonResponse({'success': False, 'error': 'Метод не разрешён'})




@login_required
def payment_page_view(request: HttpRequest, masterclass_id: int) -> HttpResponse:
    """Страница оплаты мастер-класса.
    Args:request: HTTP-запрос
        masterclass_id: ID мастер-класса
    Returns:HttpResponse: Страница оплаты или перенаправление"""
    masterclass = get_object_or_404(MasterClass, id=masterclass_id)

    # Получаем данные из сессии
    booking_data = request.session.get('booking_data', {})

    if not booking_data:
        return redirect('catalog')

    session = get_object_or_404(Session, id=booking_data.get('session_id'))
    participants_count = booking_data.get('participants_count', 1)
    total_price = masterclass.price * participants_count

    if request.method == 'POST':
        # Создаём бронирование
        Booking.objects.create(
            participant=request.user,
            masterclass=masterclass,
            session=session,
            status='confirmed',
            payment_status='paid',
            participants_count=participants_count,
            total_price=total_price
        )

        # Обновляем количество участников в сеансе
        session.current_participants += participants_count
        session.save()

        # Очищаем сессию
        request.session.pop('booking_data', None)

        messages.success(request, f'Вы успешно записались на "{masterclass.title}"!')
        return redirect('participant_dashboard')

    context = {
        'masterclass': masterclass,
        'session': session,
        'participants_count': participants_count,
        'total_price': total_price,
        'participant_name': booking_data.get('participant_name', ''),
        'participant_email': booking_data.get('participant_email', ''),
        'participant_phone': booking_data.get('participant_phone', ''),
        'comment': booking_data.get('comment', ''),
    }
    return render(request, 'main/payment_page.html', context)

@login_required
def cancel_booking_view(request: HttpRequest, booking_id: int) -> HttpResponse:
    """Отмена бронирования пользователем.
    Args:request: HTTP-запрос
        booking_id: ID бронирования
    Returns:HttpResponse: Перенаправление или страница подтверждения"""
    print("=== cancel_booking_view ВЫЗВАНА ===")
    print(f"Booking ID: {booking_id}")
    print(f"Method: {request.method}")

    booking = get_object_or_404(Booking, id=booking_id, participant=request.user)
    print(f"Booking found: {booking.id}, masterclass: {booking.masterclass.title}")

    masterclass = booking.masterclass

    # Проверка: можно ли отменить (за 24 часа до начала)
    time_until_start = masterclass.start_datetime - timezone.now()
    can_cancel = time_until_start > timedelta(hours=24)
    print(f"Can cancel: {can_cancel}, hours left: {time_until_start.total_seconds() / 3600}")

    if request.method == 'POST':
        print("=== ОБРАБОТКА POST ===")

        if not can_cancel:
            print("Отмена запрещена: менее 24 часов")
            messages.error(request, 'Отмена невозможна: до начала мастер-класса осталось менее 24 часов')
            return redirect('participant_dashboard')

        if booking.status == 'cancelled':
            print("Бронирование уже отменено")
            messages.error(request, 'Эта запись уже отменена')
            return redirect('participant_dashboard')

        try:
            with transaction.atomic():
                print("Отменяем бронирование...")
                booking.status = 'cancelled'
                booking.payment_status = 'refunded'
                booking.save()
                print(f"Booking saved, new status: {booking.status}")

                print(f"Current participants before: {masterclass.current_participants}")
                masterclass.refresh_from_db()
                print(f"Current participants after refresh: {masterclass.current_participants}")

                masterclass.current_participants -= booking.participants_count
                print(f"After subtract: {masterclass.current_participants}")

                if masterclass.current_participants < 0:
                    masterclass.current_participants = 0
                    print("Set to 0 because negative")

                masterclass.save(update_fields=['current_participants'])
                print(f"Masterclass saved, new participants: {masterclass.current_participants}")

                messages.success(request,
                                 f'Запись на мастер-класс "{masterclass.title}" отменена. Деньги будут возвращены в течение 3-5 рабочих дней.')
                print("SUCCESS")
        except Exception as e:
            print(f"ERROR: {e}")
            messages.error(request, f'Ошибка при отмене: {str(e)}')

        return redirect('participant_dashboard')

    print("=== GET REQUEST ===")
    context = {
        'booking': booking,
        'can_cancel': can_cancel,
        'hours_left': int(time_until_start.total_seconds() / 3600) if not can_cancel else 0,
    }
    return render(request, 'main/cancel_booking.html', context)


from django.http import JsonResponse


def edit_review_view(request: HttpRequest, review_id: int) -> HttpResponse:
    """Редактирование отзыва пользователя.
    Args:request: HTTP-запрос
        review_id: ID отзыва
    Returns:HttpResponse: Страница редактирования или перенаправление"""
    review = get_object_or_404(Review, id=review_id, author=request.user)
    masterclass = review.masterclass

    if request.method == 'POST':
        rating = int(request.POST.get('rating', 5))
        text = request.POST.get('text', '')
        review.rating = rating
        review.text = text
        review.save()
        messages.success(request, 'Отзыв обновлён')
        return redirect('masterclass_detail', masterclass_id=masterclass.id)

    return render(request, 'main/edit_review.html', {
        'review': review,
        'masterclass': masterclass
    })


def delete_review_view(request: HttpRequest, review_id: int) -> HttpResponse:
    """Удаление отзыва пользователя.
    Args:request: HTTP-запрос
        review_id: ID отзыва
    Returns:HttpResponse: Перенаправление на страницу мастер-класса"""
    review = get_object_or_404(Review, id=review_id, author=request.user)
    masterclass_id = review.masterclass.id
    review.delete()
    messages.success(request, 'Отзыв удалён')
    return redirect('masterclass_detail', masterclass_id=masterclass_id)