from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import View
from .models import MasterClass, Booking


class IsAdmin(permissions.BasePermission):
    """Доступ только для администратора."""
    def has_permission(self, request: Request, view: View) -> bool:
        """
        Проверяет, является ли пользователь администратором.
        Args:
            request: HTTP-запрос
            view: Представление, к которому обращаются
        Returns:
            bool: True если администратор, иначе False
        """
        return request.user.is_authenticated and request.user.role == 'admin'


class IsOrganizer(permissions.BasePermission):
    """Доступ только для организатора."""
    def has_permission(self, request: Request, view: View) -> bool:
        """
        Проверяет, является ли пользователь организатором.
        Args:
            request: HTTP-запрос
            view: Представление, к которому обращаются
        Returns:
            bool: True если организатор, иначе False
        """
        return request.user.is_authenticated and request.user.role == 'organizer'


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Редактировать может только владелец мастер-класса."""
    def has_object_permission(self, request: Request, view: View, obj: MasterClass) -> bool:
        """
        Проверяет, имеет ли пользователь право на изменение объекта.
        Args:
            request: HTTP-запрос
            view: Представление, к которому обращаются
            obj: Объект мастер-класса
        Returns:
            bool: True если метод безопасный или пользователь владелец
        """
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.organizer == request.user


class IsParticipant(permissions.BasePermission):
    """Доступ только для участников."""
    def has_permission(self, request: Request, view: View) -> bool:
        """
        Проверяет, является ли пользователь участником.
        Args:
            request: HTTP-запрос
            view: Представление, к которому обращаются
        Returns:
            bool: True если участник, иначе False
        """
        return request.user.is_authenticated and request.user.role == 'participant'


class IsBookingOwner(permissions.BasePermission):
    """Бронирование может просматривать только владелец или администратор."""
    def has_object_permission(self, request: Request, view: View, obj: Booking) -> bool:
        """
        Проверяет, имеет ли пользователь право на просмотр бронирования.
        Args:
            request: HTTP-запрос
            view: Представление, к которому обращаются
            obj: Объект бронирования
        Returns:
            bool: True если пользователь владелец бронирования или администратор
        """
        return obj.participant == request.user or request.user.role == 'admin'