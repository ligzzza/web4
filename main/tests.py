from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import MasterClass, Category, Booking, Session, Review, Favorite
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


class AuthTest(TestCase):
    """Тесты регистрации и авторизации"""

    def test_user_registration(self):
        """Тест 1: Регистрация нового пользователя (через модель)"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='test123456',
            role='participant'
        )
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('test123456'))

class MasterClassTest(TestCase):
    """Тесты мастер-классов"""

    def setUp(self):
        self.organizer = User.objects.create_user(
            username='organizer',
            email='org@test.com',
            password='org123',
            role='organizer'
        )
        self.category = Category.objects.create(
            name='Кулинария',
            slug='kulinariya'
        )
        self.masterclass = MasterClass.objects.create(
            title='Пицца',
            description='Готовим пиццу',
            category=self.category,
            organizer=self.organizer,
            city='Москва',
            address='ул. Тверская, 10',
            format='offline',
            price=1500,
            status='approved'
        )

    def test_masterclass_creation(self):
        """Тест 2: Создание мастер-класса"""
        self.assertEqual(MasterClass.objects.count(), 1)
        self.assertEqual(self.masterclass.title, 'Пицца')

    def test_masterclass_str(self):
        """Тест 3: Метод __str__ мастер-класса"""
        self.assertEqual(str(self.masterclass), 'Пицца - Москва')


class SessionTest(TestCase):
    """Тесты сеансов"""

    def setUp(self):
        self.organizer = User.objects.create_user(
            username='organizer',
            email='org@test.com',
            password='org123',
            role='organizer'
        )
        self.category = Category.objects.create(name='Творчество', slug='tvorchestvo')
        self.masterclass = MasterClass.objects.create(
            title='Рисование',
            description='Учимся рисовать',
            category=self.category,
            organizer=self.organizer,
            city='Москва',
            address='ул. Арбат, 15',
            format='offline',
            price=1000,
            status='approved'
        )
        self.session = Session.objects.create(
            masterclass=self.masterclass,
            start_datetime=timezone.now() + timedelta(days=5),
            end_datetime=timezone.now() + timedelta(days=5, hours=2),
            max_participants=10,
            current_participants=0,
            status='active'
        )

    def test_session_creation(self):
        """Тест 4: Создание сеанса"""
        self.assertEqual(Session.objects.count(), 1)
        self.assertEqual(self.session.max_participants, 10)

    def test_free_places_property(self):
        """Тест 5: Проверка свойства free_places"""
        self.assertEqual(self.session.free_places, 10)
        self.assertTrue(self.session.has_free_places)


class BookingTest(TestCase):
    """Тесты бронирования"""

    def setUp(self):
        self.participant = User.objects.create_user(
            username='participant',
            email='part@test.com',
            password='part123',
            role='participant'
        )
        self.organizer = User.objects.create_user(
            username='organizer',
            email='org@test.com',
            password='org123',
            role='organizer'
        )
        self.category = Category.objects.create(name='Кулинария', slug='kulinariya')
        self.masterclass = MasterClass.objects.create(
            title='Пицца',
            description='Готовим пиццу',
            category=self.category,
            organizer=self.organizer,
            city='Москва',
            address='ул. Тверская, 10',
            format='offline',
            price=1500,
            status='approved'
        )
        self.session = Session.objects.create(
            masterclass=self.masterclass,
            start_datetime=timezone.now() + timedelta(days=5),
            end_datetime=timezone.now() + timedelta(days=5, hours=2),
            max_participants=10,
            current_participants=0,
            status='active'
        )
        self.booking = Booking.objects.create(
            participant=self.participant,
            masterclass=self.masterclass,
            session=self.session,
            status='confirmed',
            payment_status='paid',
            participants_count=2,
            total_price=3000
        )

    def test_booking_creation(self):
        """Тест 6: Создание бронирования"""
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(self.booking.total_price, 3000)

    def test_total_price_calculation(self):
        """Тест 7: Расчёт итоговой цены"""
        self.assertEqual(self.booking.total_price, 3000)


class FavoriteTest(TestCase):
    """Тесты избранного"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='user123',
            role='participant'
        )
        self.organizer = User.objects.create_user(
            username='organizer',
            email='org@test.com',
            password='org123',
            role='organizer'
        )
        self.category = Category.objects.create(name='Творчество', slug='tvorchestvo')
        self.masterclass = MasterClass.objects.create(
            title='Рисование',
            description='Учимся рисовать',
            category=self.category,
            organizer=self.organizer,
            city='Москва',
            address='ул. Арбат, 15',
            format='offline',
            price=1000,
            status='approved'
        )
        self.favorite = Favorite.objects.create(
            user=self.user,
            masterclass=self.masterclass
        )

    def test_favorite_creation(self):
        """Тест 8: Добавление в избранное"""
        self.assertEqual(Favorite.objects.count(), 1)


class ReviewTest(TestCase):
    """Тесты отзывов"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='user123',
            role='participant'
        )
        self.organizer = User.objects.create_user(
            username='organizer',
            email='org@test.com',
            password='org123',
            role='organizer'
        )
        self.category = Category.objects.create(name='Кулинария', slug='kulinariya')
        self.masterclass = MasterClass.objects.create(
            title='Пицца',
            description='Готовим пиццу',
            category=self.category,
            organizer=self.organizer,
            city='Москва',
            address='ул. Тверская, 10',
            format='offline',
            price=1500,
            status='approved'
        )
        # Сеанс с прошедшей датой (для отзыва) — даты должны идти в правильном порядке
        self.session = Session.objects.create(
            masterclass=self.masterclass,
            start_datetime=timezone.now() - timedelta(days=5),
            end_datetime=timezone.now() - timedelta(days=5) + timedelta(hours=2),  # +2 часа от start
            max_participants=10,
            current_participants=1,
            status='completed'
        )
        self.booking = Booking.objects.create(
            participant=self.user,
            masterclass=self.masterclass,
            session=self.session,
            status='completed',
            payment_status='paid',
            participants_count=1,
            total_price=1500
        )
        self.review = Review.objects.create(
            author=self.user,
            masterclass=self.masterclass,
            booking=self.booking,
            rating=5,
            text='Отлично!',
            status='approved'
        )

    def test_review_creation(self):
        """Тест 9: Создание отзыва"""
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(self.review.rating, 5)


class CategoryTest(TestCase):
    """Тесты категорий"""

    def setUp(self):
        self.category = Category.objects.create(
            name='Спорт',
            slug='sport',
            description='Спортивные мастер-классы'
        )

    def test_category_creation(self):
        """Тест 10: Создание категории"""
        self.assertEqual(Category.objects.count(), 1)
        self.assertEqual(str(self.category), 'Спорт')