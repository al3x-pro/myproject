from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view() ,name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),

    path('profile/favorites/', views.favourite_list, name='favorite_list'),
    path('fav/<uuid:public_id>/', views.favorite_add, name='favorite_add'),

    path('like/', views.like, name='like'),

    path('password_change/', views.UserPasswordChangeView.as_view(), name='password_change'),
]