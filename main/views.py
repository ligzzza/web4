from rest_framework import permissions, viewsets, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from .models import MasterClass, Category, Booking, Review, Favorite, Notification, Image, Session
from .serializers import (
    MasterClassSerializer, CategorySerializer, BookingSerializer,
    ReviewSerializer, FavoriteSerializer, UserSerializer, RegisterSerializer
)
from .permissions import IsOrganizer, IsAdmin, IsOwnerOrReadOnly, IsParticipant, IsBookingOwner
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm
from datetime import datetime

from django.contrib.auth.decorators import login_required  # 👈 ЭТО ВАЖНО!
from django.shortcuts import get_object_or_404  # 👈 ЭТО ВАЖНО!
from django.contrib import messages  # 👈 ЭТО ВАЖНО!
from django.core.paginator import Paginator
from django.db.models import Q, Min
from django.db.models import Avg, Count


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


def login_view(request):
    if request.user.is_authenticated:
        # Если уже залогинен, перенаправляем на профиль
        if request.user.role == 'organizer':
            return redirect('organizer_dashboard')
        else:
            return redirect('participant_dashboard')

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
                    return redirect('organizer_dashboard')
                else:
                    return redirect('participant_dashboard')
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
    """Страница участника с его бронированиями"""

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
def organizer_dashboard(request):
    """Страница организатора с его мастер-классами"""
    my_masterclasses = MasterClass.objects.filter(organizer=request.user).order_by('-created_at')

    # Для каждого мастер-класса добавляем первый сеанс
    for mc in my_masterclasses:
        mc.first_session = mc.sessions.filter(status='active').order_by('start_datetime').first()

    context = {
        'user': request.user,
        'my_masterclasses': my_masterclasses,
    }
    return render(request, 'main/organizer_dashboard.html', context)


# WEB VIEWS (НОВЫЙ КОД - ДОБАВИТЬ В КОНЕЦ ФАЙЛА)
# ============================================================

def register_view(request):
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if user.role == 'organizer':
                return redirect('/organizer/dashboard/')
            else:
                return redirect('/participant/dashboard/')
    else:
        form = RegisterForm()

    return render(request, 'main/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('/')

    error = None
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
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


# ============================================================
# НОВЫЕ VIEW-ФУНКЦИИ ДЛЯ НОВОГО ДИЗАЙНА (ДОБАВИТЬ СЮДА)
# ============================================================


def home_view(request):
    """Главная страница"""
    from .models import MasterClass, Category, User, Booking
    from django.db.models import Avg, Count, Sum

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

def catalog_view(request):
    """Каталог мастер-классов с фильтрацией, поиском и пагинацией"""

    # Базовый запрос — только одобренные мастер-классы
    masterclasses = MasterClass.objects.filter(status='approved')

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
        mc.nearest_session = mc.sessions.filter(status='active').order_by('start_datetime').first()

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
def profile_view(request):
    """Профиль пользователя (универсальный)"""
    return render(request, 'main/profile.html', {'user': request.user})

@login_required
def favorites_list_view(request):
    """Список избранного"""
    favorites = Favorite.objects.filter(user=request.user)
    return render(request, 'main/favorites.html', {'favorites': favorites})




from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .models import MasterClass, Booking, Favorite, Category




@login_required
def create_masterclass_view(request):
    """Создание мастер-класса с сеансами (только организатор и админ)"""
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

        for i in range(len(start_datetimes)):
            if start_datetimes[i] and end_datetimes[i]:
                Session.objects.create(
                    masterclass=masterclass,
                    start_datetime=datetime.strptime(start_datetimes[i], '%Y-%m-%dT%H:%M'),
                    end_datetime=datetime.strptime(end_datetimes[i], '%Y-%m-%dT%H:%M'),
                    max_participants=int(max_participants_list[i])
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

def masterclass_detail_view(request, masterclass_id):
    """Детальная страница мастер-класса с отзывами"""
    masterclass = get_object_or_404(MasterClass, id=masterclass_id)
    sessions = masterclass.sessions.filter(status='active')

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
def edit_masterclass_view(request, masterclass_id):
    """Редактирование мастер-класса и его сеансов"""
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


from django.http import JsonResponse

@login_required
def add_favorite_view(request, masterclass_id):
    """Добавление в избранное (асинхронно)"""
    if request.method == 'POST':
        masterclass = get_object_or_404(MasterClass, id=masterclass_id)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            masterclass=masterclass
        )
        return JsonResponse({'status': 'added', 'favorite': created})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def remove_favorite_view(request, masterclass_id):
    """Удаление из избранного"""
    if request.method == 'POST':
        Favorite.objects.filter(
            user=request.user,
            masterclass_id=masterclass_id
        ).delete()
        return redirect('favorites_list')
    return redirect('favorites_list')


@login_required
def add_booking_view(request, masterclass_id):
    """Бронирование мастер-класса"""
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
def booking_session_view(request, session_id):
    session = get_object_or_404(Session, id=session_id, status='active')
    masterclass = session.masterclass

    if request.method == 'POST':
        if not session.has_free_places:
            messages.error(request, 'Свободные места закончились')
            return redirect('masterclass_detail', masterclass_id=masterclass.id)

        Booking.objects.create(
            participant=request.user,
            masterclass=masterclass,
            session=session,
            status='confirmed',
            payment_status='paid',
            participants_count=1,
            total_price=masterclass.price
        )
        session.current_participants += 1
        session.save()

        messages.success(request, f'Вы записались на "{masterclass.title}"')
        return redirect('masterclass_detail', masterclass_id=masterclass.id)

    return render(request, 'main/booking_session.html', {'session': session, 'masterclass': masterclass})


@login_required
def booking_detail_view(request, booking_id):
    """Детальная страница бронирования"""
    booking = get_object_or_404(Booking, id=booking_id, participant=request.user)
    session = booking.session
    masterclass = booking.masterclass

    context = {
        'booking': booking,
        'session': session,
        'masterclass': masterclass,
    }
    return render(request, 'main/booking_detail.html', context)

def custom_logout_view(request):
    """Выход из системы"""
    logout(request)
    return redirect('home')



def delete_masterclass_view(request, masterclass_id):
    """Удаление мастер-класса (только владелец или админ)"""
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
def add_review_view(request, masterclass_id):
    masterclass = get_object_or_404(MasterClass, id=masterclass_id)

    if request.method == 'POST':
        rating = int(request.POST.get('rating', 5))
        text = request.POST.get('text', '')

        user_booking = Booking.objects.filter(
            participant=request.user,
            masterclass=masterclass,
            status='completed'
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


@login_required
def favorites_list_view(request):
    """Страница избранного"""
    favorites = Favorite.objects.filter(user=request.user)
    return render(request, 'main/favorites.html', {'favorites': favorites})


def profile_simple_view(request):
    """Простой профиль для теста"""
    return render(request, 'main/profile_simple.html', {'user': request.user})


from .forms import UserEditForm, OrganizerEditForm
from django.contrib import messages


from django.http import JsonResponse
from .forms import UserEditForm


@login_required
def edit_profile_ajax(request):
    """AJAX редактирование профиля"""
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
def payment_page_view(request, masterclass_id):
    """Страница оплаты мастер-класса"""
    masterclass = get_object_or_404(MasterClass, id=masterclass_id)

    # Получаем данные из сессии
    booking_data = request.session.get('booking_data', {})

    if not booking_data or booking_data.get('masterclass_id') != masterclass.id:
        return redirect('booking_page', masterclass_id=masterclass.id)

    participants_count = booking_data.get('participants_count', 1)
    total_price = masterclass.price * participants_count

    if request.method == 'POST':
        # Создаём бронирование
        booking = Booking.objects.create(
            participant=request.user,
            masterclass=masterclass,
            status='confirmed',
            payment_status='paid',
            participants_count=participants_count,
            total_price=total_price
        )

        # Увеличиваем количество участников
        masterclass.current_participants += participants_count
        masterclass.save()

        # Очищаем сессию
        request.session.pop('booking_data', None)

        messages.success(request, f'Вы успешно записались на мастер-класс "{masterclass.title}"!')
        return redirect('masterclass_detail', masterclass_id=masterclass.id)

    context = {
        'masterclass': masterclass,
        'participants_count': participants_count,
        'total_price': total_price,
        'participant_name': booking_data.get('participant_name', ''),
        'participant_phone': booking_data.get('participant_phone', ''),
        'participant_email': booking_data.get('participant_email', ''),
        'comment': booking_data.get('comment', ''),
    }
    return render(request, 'main/payment_page.html', context)


from datetime import timedelta
from django.utils import timezone
from django.contrib import messages
from django.db import transaction


@login_required
def cancel_booking_view(request, booking_id):
    """Отмена бронирования"""
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


def edit_review_view(request, review_id):
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


def delete_review_view(request, review_id):
    review = get_object_or_404(Review, id=review_id, author=request.user)
    masterclass_id = review.masterclass.id
    review.delete()
    messages.success(request, 'Отзыв удалён')
    return redirect('masterclass_detail', masterclass_id=masterclass_id)