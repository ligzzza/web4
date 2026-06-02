from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

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

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Web страницы
    path('', views.home_view, name='home'),
    path('catalog/', views.catalog_view, name='catalog'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit-ajax/', views.edit_profile_ajax, name='edit_profile_ajax'),
    path('create/', views.create_masterclass_view, name='create_masterclass'),
    path('masterclass/<int:masterclass_id>/', views.masterclass_detail_view, name='masterclass_detail'),
    path('masterclass/<int:masterclass_id>/edit/', views.edit_masterclass_view, name='edit_masterclass'),
    path('masterclass/<int:masterclass_id>/delete/', views.delete_masterclass_view, name='delete_masterclass'),
    path('masterclass/<int:masterclass_id>/review/', views.add_review_view, name='add_review'),
    path('masterclass/<int:masterclass_id>/sessions/', views.masterclass_sessions_view, name='masterclass_sessions'),
    path('favorites/', views.favorites_list_view, name='favorites_list'),
    path('favorite/<int:masterclass_id>/add/', views.add_favorite_view, name='add_favorite'),
    path('favorite/<int:masterclass_id>/remove/', views.remove_favorite_view, name='remove_favorite'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('participant/dashboard/', views.participant_dashboard, name='participant_dashboard'),
    path('organizer/dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
    path('payment/<int:masterclass_id>/', views.payment_page_view, name='payment_page'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking_view, name='cancel_booking'),
    path('session/<int:session_id>/book/', views.booking_session_view, name='booking_session'),
    path('session/<int:session_id>/participants/', views.session_participants_view, name='session_participants'),
    path('booking-detail/<int:booking_id>/', views.booking_detail_view, name='booking_detail'),
    path('booking/<int:booking_id>/', views.booking_detail_view, name='booking_detail'),

    # Отзывы - редактирование и удаление
    path('review/<int:review_id>/edit/', views.edit_review_view, name='edit_review'),
    path('review/<int:review_id>/delete/', views.delete_review_view, name='delete_review'),

    # Администратор
    path('control/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('control/masterclasses/', views.admin_masterclasses, name='admin_masterclasses'),
    path('control/masterclass/<int:masterclass_id>/approve/', views.admin_approve_masterclass,
         name='admin_approve_masterclass'),
    path('control/masterclass/<int:masterclass_id>/reject/', views.admin_reject_masterclass,
         name='admin_reject_masterclass'),
    path('control/reviews/', views.admin_reviews, name='admin_reviews'),
    path('control/review/<int:review_id>/approve/', views.admin_approve_review, name='admin_approve_review'),
    path('control/review/<int:review_id>/delete/', views.admin_delete_review, name='admin_delete_review'),
    path('control/users/', views.admin_users, name='admin_users'),
    path('control/user/<int:user_id>/block/', views.admin_block_user, name='admin_block_user'),
    path('control/user/<int:user_id>/unblock/', views.admin_unblock_user, name='admin_unblock_user'),
    path('control/user/<int:user_id>/make-organizer/', views.admin_make_organizer, name='admin_make_organizer'),
    path('control/categories/', views.admin_categories, name='admin_categories'),
    path('control/category/<int:category_id>/edit/', views.admin_edit_category, name='admin_edit_category'),
    path('control/category/<int:category_id>/delete/', views.admin_delete_category, name='admin_delete_category'),
    path('control/bookings/', views.admin_bookings_history, name='admin_bookings_history'),
    path('control/profile/', views.admin_profile_view, name='admin_profile'),
# Добавить в urlpatterns (после существующих путей)
    path('about/', views.about_page, name='about'),
    path('faq/', views.faq_page, name='faq'),
    path('how-to-book/', views.how_to_book_page, name='how_to_book'),
    path('cancellation-rules/', views.cancellation_rules_page, name='cancellation_rules'),
    path('refund-policy/', views.refund_policy_page, name='refund_policy'),
    path('privacy/', views.privacy_page, name='privacy'),
    path('terms/', views.terms_page, name='terms'),
    path('image/<int:image_id>/delete/', views.delete_masterclass_image, name='delete_masterclass_image'),
    path('organizer/<int:user_id>/masterclasses/', views.organizer_masterclasses, name='organizer_masterclasses'),
]