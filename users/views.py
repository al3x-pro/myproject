from django.shortcuts import render
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm, UserProfileForm, UserPasswordChangeForm
from django.contrib.auth import get_user_model
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin


class RegisterView(CreateView):
    model = get_user_model()
    template_name = 'registration/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')


class ProfileView(LoginRequiredMixin, UpdateView):
    model = get_user_model()
    template_name = 'users/profile.html'
    form_class = UserProfileForm
    success_url = reverse_lazy('users:profile')
    
    def get_object(self, queryset=None):
        return self.request.user


class UserPasswordChangeView(PasswordChangeView):
    template_name = 'registration/password_change_form.html'
    form_class = UserPasswordChangeForm
    success_url = reverse_lazy('password_change_done')
