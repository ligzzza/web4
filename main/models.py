from django.db import models
from django.contrib.auth.models import User


class BaseModel(models.Model):
    """Абстрактная базовая модель с общими полями"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ExampleModel(BaseModel):
    """Пример модели для вашего приложения"""
    name = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='examples',
        verbose_name="Владелец"
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Пример'
        verbose_name_plural = 'Примеры'