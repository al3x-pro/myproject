from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view() ,name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),

    path('profile/favourites/', views.favourite_list, name='favourite_list'),
    path('fav/<int:id>/', views.favourite_add, name='favourite_add'),

    path('like/', views.like, name='like'),

    path('password_change/', views.UserPasswordChangeView.as_view(), name='password_change'),
]