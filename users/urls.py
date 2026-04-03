from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view() ,name='register'),
    path("verify-email/<str:token>/", views.verify_email, name="verify-email"),
    path("verify-pending/", views.verification_pending, name="verification-pending"),
    path("resend-verification/", views.resend_verification, name="resend-verification"),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('password-change/', views.UserPasswordChangeView.as_view(), name='password_change'),

    path('profile/favorites/', views.FavouriteListView.as_view(), name='favorite_list'),
    path('fav/<uuid:public_id>/', views.FavoriteToggleView.as_view(), name='favorite_add'),
    path('like/', views.LikeToggleView.as_view(), name='like'),
]