from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'masterclasses', views.MasterClassViewSet)
router.register(r'categories', views.CategoryViewSet)
router.register(r'bookings', views.BookingViewSet)
router.register(r'reviews', views.ReviewViewSet)
router.register(r'favorites', views.FavoriteViewSet)

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    path('api/users/', views.UserListView.as_view(), name='user-list'),
    path('api/register/', views.RegisterView.as_view(), name='api_register'),
    path('api/login/', views.LoginView.as_view(), name='api_login'),
    path('api/logout/', views.LogoutView.as_view(), name='api_logout'),

    # Web страницы
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('participant/dashboard/', views.participant_dashboard, name='participant_dashboard'),
    path('organizer/dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
]