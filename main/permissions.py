from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """Доступ только для администратора"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsOrganizer(permissions.BasePermission):
    """Доступ только для организатора"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'organizer'


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Редактировать может только владелец"""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.organizer == request.user


class IsParticipant(permissions.BasePermission):
    """Доступ только для участников"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'participant'


class IsBookingOwner(permissions.BasePermission):
    """Бронирование может просматривать только владелец"""
    def has_object_permission(self, request, view, obj):
        return obj.participant == request.user or request.user.role == 'admin'