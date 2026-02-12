from django.http import JsonResponse
from django.shortcuts import render
from .models import Entry, Category, Comment
from .forms import EntryForm, CommentForm, EntrySearchForm
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, F
from django.core.cache import cache
from django.core import serializers
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchVector, SearchQuery


class EntryListView(LoginRequiredMixin, ListView):
    """
    Entries List
    """
    model = Entry
    template_name = 'base/base.html'
    context_object_name = 'entries'
    ordering = ['-created_at']
    paginate_by = 10

    def get_queryset(self):
        query = super().get_queryset()
        
        # Simple filtering by category
        filter_list = self.request.GET.get('category')
        if filter_list and filter_list != 'all':
            query = query.filter(category__slug=filter_list)

        return query
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['categories'] = Category.objects.annotate(entry_count=Count('entries'))
        context['comments_count'] = Comment.objects.count()
        context['users_count'] = Entry.objects.get_author_count()

        return context


class EntryDetailView(DetailView):
    """
    Entry Detail
    """
    model = Entry
    context_object_name = 'entry'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)

        # Increment view count atomically
        Entry.objects.filter(pk=obj.pk).update(views=F('views') + 1)
        obj.refresh_from_db(fields=['views'])

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all comments for this post, ordered by tree structure
        context['allcomments'] = Comment.objects.filter(
            entry=self.object
        ).select_related('author')

        fav = False
        user = self.request.user

        if user.is_authenticated:
            fav = self.object.favourites.filter(id=user.id).exists()

        context['comment_form'] = CommentForm()
        context['fav'] = fav
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
    Entry Creation
    """
    model = Entry
    form_class = EntryForm
    extra_context = {'title': 'Create New Entry'}

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return self.object.get_absolute_url()
    

class EntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Entry Updation
    """
    model = Entry
    form_class = EntryForm
    extra_context = {'title': 'Update Entry'}

    def test_func(self):
        entry = self.get_object()
        return entry.author == self.request.user
    
    def get_success_url(self):
        return self.object.get_absolute_url()
    

class EntryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Entry Delition
    """
    model = Entry
    success_url = reverse_lazy('myapp:entry-list')

    def test_func(self):
        entry = self.get_object()
        return entry.author == self.request.user


class SearchView(View):
    """
    Search Entries
    """
    def get(self):
        ...

    def post(self):
        ...

        
def entry_search(request):
    form = EntrySearchForm()
    q = ''
    results = []

    if request.POST.get('action') == 'post':
        search_string = str(request.POST.get('ss', ''))
    
        if search_string:  # Checks for both None and empty string
            results = Entry.objects.annotate(
                search=SearchVector('title', 'text')
            ).filter(search=search_string)[:3]
            
            data = serializers.serialize('json', list(results), fields=('title',))
            return JsonResponse({'search_string': data}, safe=False)
        else:
            return JsonResponse({'search_string': '[]'}, safe=False)

    if 'q' in request.GET:
        form = EntrySearchForm(request.GET)
        if form.is_valid():
            q = form.cleaned_data['q']

            results = Entry.objects.annotate(search=SearchVector(
                'title', 'text'),).filter(search=SearchQuery(q))

    return render(request, 'myapp/search.html', {'form': form,
                                                 'q':q,
                                                 'results': results,})