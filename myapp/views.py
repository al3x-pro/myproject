from django.http import JsonResponse
from django.shortcuts import render
from .models import Entry, Comment
from .forms import EntryForm, CommentForm, EntrySearchForm
from django.views.generic import ListView, DetailView, CreateView, UpdateView \
    , DeleteView, View, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from django.core.cache import cache
from django.core import serializers
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchVector, SearchQuery
from django.contrib import messages
import logging


# Maximum number of recently viewed entries to keep in session
MAX_RECENT_ENTRIES = 10
# Maximum number of results returned by the live AJAX search
AJAX_RESULTS_LIMIT = 3

logger = logging.getLogger("daybook")


class EntryListView(LoginRequiredMixin, ListView):
    """
    Displays a paginated, filterable list of journal entries.
    Supports sorting by recency (new/old), popularity, and category filters.
    Category counts and aggregate totals are cached to reduce database load.
    URL query params:
        sort (str): 'new' (default) | 'old' | 'popular' | <Category value>
    """
    model = Entry
    template_name = "base/base.html"
    context_object_name = "entries"
    ordering = ["-created_at"]
    paginate_by = 5
 
    def get_queryset(self):
        """
        Returns a filtered and sorted queryset based on the 'sort' query parameter.
        Filtering by category uses Entry.Category enum values.
        Filtering by 'popular' requires both likes and comments to be non-zero.
        """
        queryset = super().get_queryset()
        sort = self.request.GET.get("sort", "new")
 
        if sort == "old":
            queryset = queryset.order_by("created_at")
        elif sort == "new":
            queryset = queryset.order_by("-created_at")
        elif sort == "popular":
            queryset = queryset.filter(
                total_comments__gt=0,
                total_likes__gt=0,
            ).order_by("-total_likes", "-total_comments")
        elif sort in Entry.Category.values:
            queryset = queryset.filter(category=sort)
        else:
            queryset = queryset.order_by("-created_at")
 
        return queryset
 
    def get_context_data(self, **kwargs):
        """
        Extends context with:
          - 'categories': list of dicts with label, value, and entry count per category
          - 'totals': aggregate counts of published entries, authors, and comments
          - 'current_sort': echoes the active sort param back to the template for UI state
        Both 'categories' and 'totals' are cached to avoid repeated aggregation queries.
        Cache TTLs: categories = 15 min, totals = 5 min.
        """
        context = super().get_context_data(**kwargs)
        context["current_sort"] = self.request.GET.get("sort", "new")

        context["categories"] = cache.get_or_set(
            "categories_list",
            lambda: [
                {
                    "label": Entry.Category(row["category"]).label,
                    "count": row["count"],
                    "name": Entry.Category(row["category"]).value,
                }
                for row in Entry.objects.values("category").annotate(count=Count("id"))
            ],
            timeout=60 * 15,
        )
 
        context["totals"] = cache.get_or_set(
            "entry_totals",
            lambda: Entry.objects.filter(is_published=True).aggregate(
                total_users=Count("author", distinct=True),
                total_comments=Count("comments", distinct=True),
                total_entries=Count("id", distinct=True),
            ),
            timeout=60 * 5,
        )
 
        return context


class EntryDetailView(DetailView):
    """
    Displays a single journal entry by its public_id slug.

    Tracks recently viewed entries in the user's session (capped at
    MAX_RECENT_ENTRIES). Provides all comments, a comment form, and
    the authenticated user's favourite status for the entry.

    URL kwargs:
        public_id (str): the entry's public_id field used as the slug.
    """

    model = Entry
    context_object_name = "entry"
    template_name = "myapp/entry_detail.html"
    slug_field = "public_id"        # Look up Entry by this model field
    slug_url_kwarg = "public_id"    # Matched from the URL pattern


    def get_queryset(self):
        return super().get_queryset().prefetch_related("favorites")

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and maintains a capped, ordered list of recently
        viewed entry IDs in the session (most recent last).

        Session key: 'recent_entries' — list of int entry IDs, max MAX_RECENT_ENTRIES.
        """
        response = super().get(request, *args, **kwargs)
        entry_id = self.object.id
        logger.info(f"Requesting post id={kwargs.get('public_id')}")

        recent = request.session.get("recent_entries", [])

        # Move entry to end (most recent) regardless of prior position
        if entry_id in recent:
            recent.remove(entry_id)
        recent.append(entry_id)

        request.session["recent_entries"] = recent[-MAX_RECENT_ENTRIES:]
        request.session.modified = True

        return response

    def get_context_data(self, **kwargs):
        """
        Extends context with:
          - 'allcomments': threaded comments for this entry, with authors preloaded
          - 'comment_form': blank CommentForm for posting a new comment
          - 'fav': True if the current authenticated user has favourited this entry
        """
        context = super().get_context_data(**kwargs)

        # Fetch comments with author data in one query; order for threaded display
        context["allcomments"] = (
            Comment.objects.filter(entry=self.object)
            .select_related("author")
            .order_by("parent_id", "created_at")  
        )

        context["fav"] = (
            self.request.user.is_authenticated
            and self.object.favorites.filter(id=self.request.user.id).exists()
        )

        # Blank form for authenticated users to submit a new comment
        context["comment_form"] = CommentForm()

        return context


class CommentAjaxView(View):
    """
    Handle AJAX requests for adding and deleting comments
    """
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        # Ensure this is an AJAX request
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'This endpoint only accepts AJAX requests'
            }, status=400)
        
        # Check if this is a delete action
        if request.POST.get('action') == 'delete':
            return self.delete_comment(request)
        else:
            return self.add_comment(request)
    
    def delete_comment(self, request):
        """Handle comment deletion"""
        comment_id = request.POST.get('nodeid')
        
        try:
            comment = Comment.objects.get(id=comment_id)
            
            # Verify the user owns this comment
            if comment.author != request.user:
                return JsonResponse({
                'error': 'You do not have permission to delete this comment'
                }, status=403)
            
            comment.delete()
            return JsonResponse({'remove': comment_id})
            
        except Comment.DoesNotExist:
            return JsonResponse({
                'error': 'Comment not found'
            }, status=404)
    
    def add_comment(self, request):
        """Handle new comment submission"""
        # Get the data from POST
        text = request.POST.get('text')
        entry_id = request.POST.get('entry')
        parent_id = request.POST.get('parent')
        
        # Validate required fields
        if not text or not entry_id:
            return JsonResponse({
                'error': 'Missing required fields',
                'details': 'Content and entry ID are required'
            }, status=400)
        
        try:
            # Get the entry
            entry = Entry.objects.get(id=entry_id)
            
            # Create the comment
            comment = Comment(
                text=text,
                author=request.user,
                entry=entry
            )
            
            # If there's a parent, set it
            if parent_id and parent_id != '':
                try:
                    parent_comment = Comment.objects.get(id=parent_id)
                    comment.parent = parent_comment
                except Comment.DoesNotExist:
                    return JsonResponse({
                        'error': 'Parent comment not found'
                    }, status=404)
            
            comment.save()
            
            return JsonResponse({
                'result': text,
                'user': request.user.username,
                'id': comment.id
            })
            
        except Entry.DoesNotExist:
            return JsonResponse({
                'error': 'Entry not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'error': 'An error occurred while saving the comment',
                'details': str(e)
            }, status=500)


class EntryCreateView(LoginRequiredMixin, CreateView):
    """
    Allows authenticated users to create a new journal entry.

    Automatically assigns the current user as the entry's author on save.
    Redirects to the newly created entry's detail page on success.

    Access: login required — unauthenticated users are redirected to LOGIN_URL.
    """

    model = Entry
    form_class = EntryForm
    template_name = "myapp/entry_form.html"   
    extra_context = {"title": "Create New Entry"}

    def form_valid(self, form):
        """
        Assigns the authenticated user as the author before saving.
        """
        form.instance.author = self.request.user
        form.instance.is_published = True
        logger.info(f"Creating post title={form.cleaned_data['title']}")
        messages.success(self.request, "Entry created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        """
        Redirects to the detail page of the newly created entry.
        """
        return self.object.get_absolute_url()
    

class EntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Allows the author of an entry to update it.

    Access control:
      - LoginRequiredMixin: redirects unauthenticated users to LOGIN_URL.
      - UserPassesTestMixin: returns 403 if the logged-in user is not the author.

    Uses public_id as the URL slug to avoid exposing internal PKs.
    Redirects to the entry's detail page on success.

    URL kwargs:
        public_id (str): the entry's public_id field used as the slug.
    """

    model = Entry
    form_class = EntryForm
    template_name = "myapp/entry_form.html"      
    extra_context = {"title": "Update Entry"}
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_object(self, queryset=None):
        """
        Fetches the entry once and caches it on the instance.
        """
        if not hasattr(self, "_object"):
            self._object = super().get_object(queryset)
        return self._object

    def test_func(self):
        """
        Grants access only if the current user is the entry's author.

        Returns True to allow, False to return a 403 Forbidden response.
        Uses the cached get_object() to avoid an extra DB query.
        """
        return self.get_object().author == self.request.user

    def form_valid(self, form):
        """
        Ensures the author field cannot be overwritten on update.
        """
        form.instance.author = self.request.user
        logger.info(f"Updating post id={self.object.id}")
        messages.success(self.request, "Entry updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        """
        Redirects to the detail page of the updated entry.
        """
        return self.object.get_absolute_url()
    

class EntryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Allows the author of an entry to permanently delete it.

    Access control:
      - LoginRequiredMixin: redirects unauthenticated users to LOGIN_URL.
      - UserPassesTestMixin: returns 403 if the logged-in user is not the author.

    Uses public_id as the URL slug to avoid exposing internal PKs.
    Redirects to the entry list on success.

    URL kwargs:
        public_id (str): the entry's public_id field used as the slug.
    """

    model = Entry
    template_name = "myapp/entry_confirm_delete.html"  
    success_url = reverse_lazy("myapp:entry-list")
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_object(self, queryset=None):
        """
        Fetches the entry once and caches it on the instance.
        """
        if not hasattr(self, "_object"):
            self._object = super().get_object(queryset)
        return self._object

    def test_func(self):
        """
        Grants access only if the current user is the entry's author.

        Returns True to allow, False to return a 403 Forbidden response.
        Uses the cached get_object() to avoid an extra DB query.
        """
        return self.get_object().author == self.request.user

    def form_valid(self, form):
        """
        Hook called on confirmed DELETE (POST to the confirm page).
        """
        logger.warning(f"Deleting post id={self.obj.id}")
        messages.success(
            self.request,
            f'Entry "{self.object.title}" was deleted successfully.'
        )
        return super().form_valid(form)

        
class EntrySearchView(TemplateView):
    """
    Handles both AJAX live search and full-page search for entries.

    Two modes:
      1. AJAX (POST, action='post'):
         Accepts 'ss' (search string), returns up to AJAX_RESULTS_LIMIT
         matching entry titles serialized as JSON. Used for live search UI.

      2. Full-page search (GET, param 'q'):
         Renders search.html with all matching entries and the bound form.
         Uses PostgreSQL full-text search across title and text fields.

    URL: myapp/search/
    """

    template_name = "myapp/search.html"

    def get_context_data(self, **kwargs):
        """
        Returns the default context with an unbound form, empty query
        and results — used for the initial empty search page render.
        """
        context = super().get_context_data(**kwargs)
        context["form"] = EntrySearchForm()
        context["q"] = ""
        context["results"] = []
        return context

    def get(self, request, *args, **kwargs):
        """
        Handles full-page search via GET param 'q'.

        If 'q' is present and the form is valid, queries entries using
        PostgreSQL full-text search across title and text fields.
        Falls back to the empty search page if 'q' is absent or invalid.
        """
        context = self.get_context_data()

        if "q" in request.GET:
            form = EntrySearchForm(request.GET)

            if form.is_valid():
                q = form.cleaned_data["q"]

                # select_related avoids N+1 queries when template accesses author
                results = (
                    Entry.objects.select_related("author")
                    .annotate(search=SearchVector("title", "text"))
                    .filter(search=SearchQuery(q))
                )
                context.update({"form": form, "q": q, "results": results})
            else:
                # Invalid form — return page with bound form so errors are visible
                context["form"] = form

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles AJAX live search via POST with action='post'.

        Expects:
            action (str): must be 'post' to trigger AJAX mode.
            ss (str): the search string typed by the user.

        Returns:
            JsonResponse: {'search_string': <serialized JSON>}
        """
        if request.POST.get("action") != "post":
            return JsonResponse({"error": "Invalid action."}, status=400)

        search_string = str(request.POST.get("ss", "")).strip()

        if not search_string:
            return JsonResponse({"search_string": "[]"}, safe=False)

        results = (
            Entry.objects.annotate(search=SearchVector("title", "text"))
            .filter(search=SearchQuery(search_string))
            [:AJAX_RESULTS_LIMIT]
        )
        data = serializers.serialize("json", list(results), fields=("title", "public_id"))
        return JsonResponse({"search_string": data}, safe=False)