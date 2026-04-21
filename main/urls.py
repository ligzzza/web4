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
    path('', views.home_view, name='home'),
    path('catalog/', views.catalog_view, name='catalog'),
    path('profile/', views.profile_view, name='profile'),
    path('create/', views.create_masterclass_view, name='create_masterclass'),
    path('masterclass/<int:masterclass_id>/', views.masterclass_detail_view, name='masterclass_detail'),
    path('masterclass/<int:masterclass_id>/edit/', views.edit_masterclass_view, name='edit_masterclass'),
    path('masterclass/<int:masterclass_id>/delete/', views.delete_masterclass_view, name='delete_masterclass'),
    path('masterclass/<int:masterclass_id>/review/', views.add_review_view, name='add_review'),
    path('favorites/', views.favorites_list_view, name='favorites_list'),
    path('favorite/<int:masterclass_id>/add/', views.add_favorite_view, name='add_favorite'),
    path('favorite/<int:masterclass_id>/remove/', views.remove_favorite_view, name='remove_favorite'),
    path('booking/<int:masterclass_id>/add/', views.add_booking_view, name='add_booking'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('participant/dashboard/', views.participant_dashboard, name='participant_dashboard'),
    path('organizer/dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
    path('payment/<int:masterclass_id>/', views.payment_page_view, name='payment_page'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking_view, name='cancel_booking'),
    path('session/<int:session_id>/book/', views.booking_session_view, name='booking_session'),
    path('booking-detail/<int:booking_id>/', views.booking_detail_view, name='booking_detail'),
    path('booking/<int:booking_id>/', views.booking_detail_view, name='booking_detail'),

    # Отзывы - редактирование и удаление
    path('review/<int:review_id>/edit/', views.edit_review_view, name='edit_review'),
    path('review/<int:review_id>/delete/', views.delete_review_view, name='delete_review'),
]