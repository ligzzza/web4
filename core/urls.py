from django.contrib import admin
from django.urls import path, include
from main.views import UserListView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('main.urls')),  # все API из приложения main
    path('api/users/', UserListView.as_view(), name='user-list'),  # список пользователей
    path('api-auth/', include('rest_framework.urls')),  # для авторизации в DRF
]