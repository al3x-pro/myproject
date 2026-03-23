from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm, UserPasswordChangeForm, UserProfileForm
from django.contrib.auth import get_user_model, login
from myapp.models import Entry
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views import View


class RegisterView(UserPassesTestMixin, CreateView):
    """
    Handles new user registration.

    Displays and processes the CustomUserCreationForm. On success,
    automatically logs the user in and redirects to the entry list.

    Access: redirects already-authenticated users away from the page
    to prevent duplicate account creation (via UserPassesTestMixin).
    """

    model = get_user_model()
    template_name = "registration/register.html"
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("myapp:entry-list")  

    def test_func(self):
        """
        Blocks already-authenticated users from accessing the register page.
        """
        return not self.request.user.is_authenticated

    def handle_no_permission(self):
        """
        Redirects authenticated users away from the registration page.
        """
        return redirect(self.success_url)

    def form_valid(self, form):
        """
        Saves the new user and logs them in immediately.
        """
        response = super().form_valid(form)
        login(
            self.request,
            self.object,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        return response


class ProfileView(LoginRequiredMixin, UpdateView):
    """
    Allows authenticated users to view and update their own profile.

    Always operates on the currently logged-in user — no pk or slug
    is needed in the URL, and no user can edit another's profile.

    Access: login required — unauthenticated users are redirected to LOGIN_URL.
    Redirects back to the profile page on successful update.
    """

    model = get_user_model()
    template_name = "users/profile.html"
    form_class = UserProfileForm
    success_url = reverse_lazy("users:profile")

    def get_object(self, queryset=None):
        """
        Returns the currently authenticated user as the object to update.
        This approach also means no pk/slug is exposed in the URL, so
        users cannot tamper with the URL to edit another account.
        """
        return self.request.user

    def form_valid(self, form):
        """
        Saves the updated profile and shows a success message.
        """
        messages.success(self.request, "Your profile was updated successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Re-renders the form with validation errors and an error message.
        """
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """
    Allows authenticated users to change their password.

    Extends Django's built-in PasswordChangeView with a custom form
    and template. Redirects to the password change done page on success.

    Access: login required — unauthenticated users are redirected to LOGIN_URL.
    """

    template_name = "registration/password_change_form.html"
    form_class = UserPasswordChangeForm
    success_url = reverse_lazy("users:password_change_done")

    def form_valid(self, form):
        """
        Saves the new password and shows a success message.

        Note: Django's PasswordChangeView calls update_session_auth_hash()
        internally via super(), so the user stays logged in after the change.
        """
        messages.success(self.request, "Your password was changed successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Re-renders the form with validation errors and an error message.
        """
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class FavoriteToggleView(LoginRequiredMixin, View):
    """
    Toggles the favourite status of an entry for the current user.

    If the user has already favourited the entry, it is removed.
    If not, it is added. Redirects back to the referring page in both cases.

    Access: login required — unauthenticated users are redirected to LOGIN_URL.

    URL kwargs:
        public_id (str): the public_id of the entry to favourite/unfavourite.
    """

    def post(self, request, *args, **kwargs):
        """
        Handles the favourite toggle on POST.
        """
        entry = get_object_or_404(Entry, public_id=kwargs["public_id"])

        if entry.favorites.filter(id=request.user.id).exists():
            entry.favorites.remove(request.user)
            messages.success(request, f'"{entry.title}" removed from your favourites.')
        else:
            entry.favorites.add(request.user)
            messages.success(request, f'"{entry.title}" added to your favourites.')

        # Fall back to entry detail if the referrer header is absent
        fallback_url = entry.get_absolute_url()
        redirect_url = request.META.get("HTTP_REFERER", fallback_url)
        return HttpResponseRedirect(redirect_url)


class FavouriteListView(LoginRequiredMixin, TemplateView):
    """
    Displays the current user's favourited entries and recently viewed entries.

    Two querysets are provided to the template:
      - 'favourites': all entries the user has marked as favourite.
      - 'visited': recently viewed entries stored in the session, preserved
        in the order they were visited (most recent last).

    Access: login required — unauthenticated users are redirected to LOGIN_URL.
    """

    template_name = "users/favorites.html"

    def get_context_data(self, **kwargs):
        """
        Builds context with favourited and recently visited entries.
        """
        context = super().get_context_data(**kwargs)

        # All entries the user has favourited, with author preloaded
        context["favorites"] = (
            Entry.objects.filter(favorites=self.request.user)
            .select_related("author")
        )

        # Restore session visit order — filter() does not guarantee id__in order
        recent_ids = self.request.session.get("recent_entries", [])
        recent_qs = (
            Entry.objects.filter(id__in=recent_ids)
            .select_related("author")
        )

        # Re-sort the queryset to match the session order (most recent last)
        recent_map = {entry.id: entry for entry in recent_qs}
        context["visited"] = [
            recent_map[entry_id]
            for entry_id in recent_ids
            if entry_id in recent_map      # Guard against stale session IDs
        ]

        return context


class LikeToggleView(LoginRequiredMixin, View):
    """
    Toggles the like status of an entry for the current user via AJAX.

    Accepts a POST request with the entry ID, adds or removes the like,
    and returns the updated like count as JSON.

    Access: login required — unauthenticated requests receive a 401 response
    rather than a redirect, since this is an AJAX endpoint.

    Expected POST params:
        action (str): must be 'post' to process the request.
        likeid (int): the primary key of the entry to like/unlike.

    Returns:
        JsonResponse: {
            'liked': bool,      — True if like was added, False if removed
            'like_count': int   — updated total like count
        }
    """

    def post(self, request, *args, **kwargs):
        """
        Handles the like toggle.
        """
        if request.POST.get("action") != "post":
            return JsonResponse({"error": "Invalid action."}, status=400)

        # Validate likeid before casting
        raw_id = request.POST.get("likeid")
        if not raw_id or not raw_id.strip().isdigit():
            return JsonResponse({"error": "Invalid entry ID."}, status=400)

        entry = get_object_or_404(Entry, id=int(raw_id))

        if entry.likes.filter(id=request.user.id).exists():
            entry.likes.remove(request.user)
            liked = False
        else:
            entry.likes.add(request.user)
            liked = True

        return JsonResponse({
            "liked": liked,
            "like_count": entry.likes.count(),
        })

    def handle_no_permission(self):
        """
        Returns a 401 JSON response for unauthenticated AJAX requests.
        """
        return JsonResponse({"error": "Authentication required."}, status=401)