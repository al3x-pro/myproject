from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view() ,name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('password_change/', views.UserPasswordChangeView.as_view(), name='password_change'),

    path('profile/favorites/', views.FavouriteListView.as_view(), name='favorite_list'),
    path('fav/<uuid:public_id>/', views.FavoriteToggleView.as_view(), name='favorite_add'),
    path('like/', views.LikeToggleView.as_view(), name='like'),
]