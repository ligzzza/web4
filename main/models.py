from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError


# 1. ПОЛЬЗОВАТЕЛЬ
class User(AbstractUser):
    """Модель пользователя с ролями Участник/Организатор/Администратор"""

    ROLE_CHOICES = [
        ('participant', 'Участник'),
        ('organizer', 'Организатор'),
        ('admin', 'Администратор'),
    ]

    email = models.EmailField(unique=True, verbose_name="Email (логин)")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='participant', verbose_name="Роль")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Аватар")
    is_active = models.BooleanField(default=True, verbose_name="Активен (не заблокирован)")
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")
    last_login = models.DateTimeField(blank=True, null=True, verbose_name="Последний вход")

    # Дополнительные поля для организатора
    organization_name = models.CharField(max_length=200, blank=True, verbose_name="Название студии/организации")
    organization_description = models.TextField(blank=True, verbose_name="Описание студии")
    is_blocked = models.BooleanField(default=False, verbose_name="Заблокирован")

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        swappable = 'AUTH_USER_MODEL'  # Указывает, что это кастомная модель

    def __str__(self)-> str:
        """Возвращает строковое представление пользователя."""
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin(self) -> bool:
        """Проверяет, является ли пользователь администратором."""
        return self.role == 'admin' or self.is_superuser

    @property
    def is_organizer(self) -> bool:
        """Проверяет, является ли пользователь организатором."""
        return self.role == 'organizer'

    @property
    def is_participant(self) -> bool:
        """Проверяет, является ли пользователь участником."""
        return self.role == 'participant'

    def add_default_permissions(self):
        """Добавляет Django-права в зависимости от роли пользователя"""
        from django.contrib.auth.models import Permission

        # Базовые права для всех авторизованных пользователей
        base_permissions = Permission.objects.filter(
            codename__in=[
                'view_masterclass',
                'view_category',
            ]
        )
        self.user_permissions.add(*base_permissions)

        # Права для участника
        if self.role == 'participant':
            participant_permissions = Permission.objects.filter(
                codename__in=[
                    'add_booking',
                    'view_booking',
                    'change_booking',
                    'add_review',
                    'view_review',
                    'change_review',
                    'add_favorite',
                    'view_favorite',
                ]
            )
            self.user_permissions.add(*participant_permissions)

        # Права для организатора (всё, что у участника + свои)
        elif self.role == 'organizer':
            organizer_permissions = Permission.objects.filter(
                codename__in=[
                    'add_booking',
                    'view_booking',
                    'change_booking',
                    'add_review',
                    'view_review',
                    'change_review',
                    'add_favorite',
                    'view_favorite',
                    'add_masterclass',
                    'change_masterclass',
                    'delete_masterclass',
                    'view_masterclass',
                ]
            )
            self.user_permissions.add(*organizer_permissions)

# 2. КАТЕГОРИЯ
class Category(models.Model):
    """Категория мастер-классов (Кулинария, Творчество и т.д.)"""

    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL-имя")
    description = models.TextField(blank=True, verbose_name="Описание")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Изображение")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']

    def __str__(self) -> str:
        """Возвращает название категории."""
        return self.name

# 3. МАСТЕР-КЛАСС
class MasterClass(models.Model):
    """Мастер-класс (мероприятие)"""

    FORMAT_CHOICES = [
        ('online', 'Онлайн'),
        ('offline', 'Офлайн'),
    ]

    STATUS_CHOICES = [
        ('pending', 'На модерации'),
        ('approved', 'Одобрен'),
        ('rejected', 'Отклонен'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='masterclasses',
                                 verbose_name="Категория")
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='masterclasses',
                                  limit_choices_to={'role': 'organizer'}, verbose_name="Организатор")

    city = models.CharField(max_length=100, verbose_name="Город")
    address = models.CharField(max_length=255, blank=True, verbose_name="Адрес")
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='offline', verbose_name="Формат")

    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)],
                                verbose_name="Цена (руб)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    moderation_comment = models.TextField(blank=True, verbose_name="Комментарий модератора")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Мастер-класс"
        verbose_name_plural = "Мастер-классы"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
        ]
    def clean(self) -> None:
        """Валидация: уникальность названия у одного организатора."""
        # Проверка: у одного организатора не может быть двух мастер-классов с одинаковым названием
        if MasterClass.objects.filter(
            organizer=self.organizer,
            title__iexact=self.title
        ).exclude(pk=self.pk).exists():
            raise ValidationError({'title': 'У вас уже есть мастер-класс с таким названием'})

    def save(self, *args, **kwargs) -> None:
        """Сохраняет мастер-класс с предварительной валидацией."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Возвращает строковое представление мастер-класса."""
        return f"{self.title} - {self.city}"

# 4. ИЗОБРАЖЕНИЕ
class Image(models.Model):
    """Изображения для мастер-класса"""

    masterclass = models.ForeignKey(MasterClass, on_delete=models.CASCADE, related_name='images',
                                    verbose_name="Мастер-класс")
    image = models.ImageField(upload_to='masterclasses/', verbose_name="Изображение")
    is_main = models.BooleanField(default=False, verbose_name="Главное фото")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Изображение"
        verbose_name_plural = "Изображения"

    def __str__(self) -> str:
        """Возвращает строковое представление изображения."""
        return f"Фото для {self.masterclass.title}"

# СЕССИИ
class Session(models.Model):
    """Сеанс мастер-класса (конкретная дата и время)"""

    masterclass = models.ForeignKey(
        'MasterClass',
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name="Мастер-класс"
    )
    start_datetime = models.DateTimeField(verbose_name="Дата и время начала")
    end_datetime = models.DateTimeField(verbose_name="Дата и время окончания")
    max_participants = models.PositiveIntegerField(default=10, verbose_name="Максимум участников")
    current_participants = models.PositiveIntegerField(default=0, verbose_name="Текущее количество записавшихся")
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Активен'),
            ('cancelled', 'Отменён'),
            ('completed', 'Завершён'),
        ],
        default='active',
        verbose_name="Статус"
    )
    meeting_link = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Ссылка на онлайн-трансляцию (Zoom, Яндекс.Телемост и т.д.)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Сеанс"
        verbose_name_plural = "Сеансы"
        ordering = ['start_datetime']

    def clean(self) -> None:
        def clean(self) -> None:
            """Валидация: дата окончания позже даты начала."""
            if self.end_datetime <= self.start_datetime:
                raise ValidationError({'end_datetime': 'Дата окончания должна быть позже даты начала'})

            # === НОВАЯ ПРОВЕРКА: пересечение с другими сеансами этого МК ===
            overlapping = Session.objects.filter(
                masterclass=self.masterclass,
                start_datetime__lt=self.end_datetime,
                end_datetime__gt=self.start_datetime
            ).exclude(pk=self.pk)

            if overlapping.exists():
                raise ValidationError(
                    'Этот сеанс пересекается с другим сеансом этого мастер-класса. '
                    'Пожалуйста, выберите другое время.'
                )

    def save(self, *args, **kwargs) -> None:
        """Сохраняет сеанс с предварительной валидацией."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Возвращает строковое представление сеанса."""
        return f"{self.masterclass.title} - {self.start_datetime.strftime('%d.%m.%Y %H:%M')}"

    @property
    def free_places(self) -> int:
        """Возвращает количество свободных мест."""
        return self.max_participants - self.current_participants

    @property
    def has_free_places(self) -> bool:
        """Проверяет, есть ли свободные места."""
        return self.current_participants < self.max_participants

# 5. БРОНИРОВАНИЕ
class Booking(models.Model):
    """Бронирование места на мастер-класс"""

    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('confirmed', 'Подтверждено'),
        ('cancelled', 'Отменено'),
        ('completed', 'Завершено'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачено'),
        ('refunded', 'Возврат'),
    ]

    participant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings',
                                    limit_choices_to={'role': 'participant'}, verbose_name="Участник")
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name="Сеанс"
    )
    masterclass = models.ForeignKey(MasterClass, on_delete=models.CASCADE, related_name='bookings',
                                    verbose_name="Мастер-класс")
    booking_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата бронирования")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending',
                                      verbose_name="Статус оплаты")
    participants_count = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)],
                                                     verbose_name="Количество мест")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена на момент бронирования")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    comment = models.TextField(blank=True, verbose_name="Комментарий к бронированию")

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ['-created_at']
        #unique_together = ['participant', 'masterclass']  # Запрет повторной записи на одно мероприятие

    def __str__(self) -> str:
        """Возвращает строковое представление бронирования."""
        return f"{self.participant.get_full_name()} → {self.masterclass.title}"

    def save(self, *args, **kwargs) -> None:
        """Сохраняет бронирование, автоматически рассчитывая итоговую цену."""
        if not self.total_price:
            self.total_price = self.masterclass.price * self.participants_count
        super().save(*args, **kwargs)

# 6. ОТЗЫВ
class Review(models.Model):
    """Отзыв на мастер-класс"""

    STATUS_CHOICES = [
        ('pending', 'На модерации'),
        ('approved', 'Одобрен'),
        ('rejected', 'Отклонен'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews', verbose_name="Автор")
    masterclass = models.ForeignKey(MasterClass, on_delete=models.CASCADE, related_name='reviews',
                                    verbose_name="Мастер-класс")
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review',
                                   verbose_name="Бронирование")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)],
                                              verbose_name="Оценка (1-5)")
    text = models.TextField(verbose_name="Текст отзыва")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at']

    def __str__(self) -> str:
        """Возвращает строковое представление отзыва."""
        return f"Отзыв от {self.author.get_full_name()} на {self.masterclass.title} (оценка: {self.rating})"


# 7. ИЗБРАННОЕ
class Favorite(models.Model):
    """Избранные мастер-классы пользователя"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name="Пользователь")
    masterclass = models.ForeignKey(MasterClass, on_delete=models.CASCADE, related_name='favorited_by',
                                    verbose_name="Мастер-класс")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        unique_together = ['user', 'masterclass']  # Нельзя добавить одно и то же дважды

    def __str__(self) -> str:
        """Возвращает строковое представление избранного."""
        return f"{self.user.get_full_name()} → {self.masterclass.title}"