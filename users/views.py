from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm, UserProfileForm, UserPasswordChangeForm
from django.contrib.auth import get_user_model
from myapp.models import Entry
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required


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


@login_required
def favourite_add(request, id):
    entry = get_object_or_404(Entry, id=id)
    if entry.favourites.filter(id=request.user.id).exists():
        entry.favourites.remove(request.user)
    else:
        entry.favourites.add(request.user)
    return HttpResponseRedirect(request.META['HTTP_REFERER'])

@login_required
def favourite_list(request):
    new = Entry.objects.filter(favourites=request.user)
    return render(request, 'users/favourites.html', {'new': new})

@login_required
def like(request):
    if request.POST.get('action') == 'post':
        result = ''
        id = int(request.POST.get('likeid'))
        entry = get_object_or_404(Entry, id=id)
        if entry.likes.filter(id=request.user.id).exists():
            entry.likes.remove(request.user)
            entry.like_count -= 1
            result = entry.like_count
            entry.save()
        else:
            entry.likes.add(request.user)
            entry.like_count += 1
            result = entry.like_count
            entry.save()

        return JsonResponse({'result': result,})